#!/usr/bin/env python3
"""CLI-only collection, trigger planning and idempotent Feishu delivery. Python 3.11+."""
import argparse
import concurrent.futures
import hashlib
import json
import os
from pathlib import Path
import subprocess
from datetime import datetime, timedelta, timezone
from zoneinfo import ZoneInfo


def read(path):
    return json.loads(Path(path).read_text())


def write(path, value):
    path = Path(path); path.parent.mkdir(parents=True, exist_ok=True)
    temp = path.with_suffix(path.suffix + '.tmp')
    temp.write_text(json.dumps(value, ensure_ascii=False, indent=2))
    os.replace(temp, path)


def instant(s):
    d = datetime.fromisoformat(s.replace('Z', '+00:00'))
    if d.tzinfo is None:
        raise ValueError('Timestamps must include timezone')
    return d


def call(argv):
    r = subprocess.run(argv, capture_output=True, text=True, timeout=180)
    if r.returncode:
        raise RuntimeError(f'CLI failed ({r.returncode}); inspect command locally without exposing credentials')
    x = json.loads(r.stdout)
    if not x.get('ok'):
        raise RuntimeError('CLI did not return ok=true; stop and inspect authentication/schema')
    return x


def config(path):
    c = read(path)
    assert c['schema_version'] == 1
    assert isinstance(c['cli'], list) and c['cli'] and all(isinstance(x, str) for x in c['cli'])
    assert c['projects'] and len({p['key'] for p in c['projects']}) == len(c['projects'])
    for p in c['projects']:
        for k in ('key', 'name', 'workspace_id', 'campaign_id', 'timezone'):
            assert p.get(k), f'Missing {k}'
        ZoneInfo(p['timezone'])
    s = c['schedule']
    assert s['poll_minutes'] > 0 and s['catchup_minutes'] >= s['poll_minutes']
    assert all(isinstance(n, int) and n > 0 for n in s['checkpoint_minutes'])
    for t in s['daily_times']:
        datetime.strptime(t, '%H:%M')
    assert s['interval_minutes'] is None or s['interval_minutes'] > 0
    if c.get('destination'):
        d = c['destination']; assert d['type'] in ('user', 'chat') and d['as'] in ('bot', 'user') and d['id']
    return c


def collect(c, project):
    videos = []; seen = set(); page = 1; expected = None
    start = (datetime.now(ZoneInfo(project['timezone'])) - timedelta(days=c['history_days'])).replace(hour=0, minute=0, second=0, microsecond=0)
    while True:
        x = call(c['cli'] + ['hireaicreator', 'video', '+list', '--workspace-id', project['workspace_id'], '--scheduled-from', start.isoformat(), '--page-size', '100', '--page', str(page)])['data']
        if expected is None: expected = x['total']
        if x['total'] != expected: raise RuntimeError('Pagination changed during collection; rerun snapshot')
        for v in x['items']:
            if v['id'] in seen: raise RuntimeError('Repeated video across pages')
            seen.add(v['id'])
            if v.get('workspace_id') == project['workspace_id'] and v.get('campaign_id') == project['campaign_id']:
                videos.append(v)
        if not x['has_more']: break
        if not x['items']: raise RuntimeError('Empty non-final page')
        page += 1
    if len(seen) != expected: raise RuntimeError('Incomplete pagination')
    ids = sorted({v['published_content_id'] for v in videos if v.get('published_content_id')})
    def fetch(cid):
        prefix = c['cli'] + ['campaign-monitor']
        suffix = ['--workspace-id', project['workspace_id'], '--id', cid]
        post = call(prefix + ['+post-get'] + suffix)['data']
        history = call(prefix + ['+post-performance-get'] + suffix + ['--limit', '1'])['data']['items']
        return cid, post, history[0] if history else None
    with concurrent.futures.ThreadPoolExecutor(max_workers=c.get('concurrency', 4)) as pool:
        rows = list(pool.map(fetch, ids))
    return {'project':project, 'observed_at':datetime.now(timezone.utc).isoformat(), 'videos':videos,
            'performance':{cid:p for cid,_,p in rows if p is not None}, 'posts':{cid:p for cid,p,_ in rows},
            'collection':{'history_from':start.isoformat(), 'future_end':None, 'workspace_rows':len(seen), 'pages':page}}


def destination_key(c):
    return hashlib.sha256(json.dumps(c['destination'],sort_keys=True).encode()).hexdigest()[:12]


def due(c, snap, state, now):
    p = snap['project']; z = ZoneInfo(p['timezone']); local = now.astimezone(z)
    schedule = c['schedule']; candidates = []
    # All outstanding thresholds within the catch-up window are merged into one project card.
    for cid, post in snap['posts'].items():
        published = post.get('published_at')
        if not published: continue
        for offset in schedule['checkpoint_minutes']:
            at = instant(published) + timedelta(minutes=offset)
            candidates.append((f'post:{cid}:{published}:{offset}',at))
    for days in (0,1):
        date = local.date() - timedelta(days=days)
        for time in schedule['daily_times']:
            hour,minute = map(int,time.split(':'))
            at = datetime(date.year,date.month,date.day,hour,minute,tzinfo=z)
            candidates.append((f'daily:{date}:{time}',at))
    interval = schedule['interval_minutes']
    if interval:
        epoch = int(now.timestamp()) // (interval*60) * interval*60
        candidates.append((f'interval:{epoch}',datetime.fromtimestamp(epoch,timezone.utc)))
    prefix = p['key'] + ':' + destination_key(c) + ':'
    return [{'key':prefix+key,'due_at':at.isoformat(),'late_seconds':int((now-at).total_seconds())}
            for key,at in candidates if timedelta(0) <= now-at <= timedelta(minutes=schedule['catchup_minutes'])
            and prefix+key not in state.get('completed',{})]


def deliver(c, snap, card, state_path, triggers):
    if not c.get('enabled'): raise ValueError('Configuration is paused; enable only after onboarding test')
    dest = c['destination']; state_path = Path(state_path)
    project_key = snap['project']['key']
    if not any(p == snap['project'] for p in c['projects']): raise ValueError('Snapshot project does not match configuration')
    expected_prefix = project_key + ':' + destination_key(c) + ':'
    if any(not t['key'].startswith(expected_prefix) for t in triggers): raise ValueError('Trigger belongs to another project or destination')
    if len(json.dumps(card, ensure_ascii=False, separators=(',', ':')).encode()) > 30000: raise ValueError('Card exceeds size limit')
    lock = state_path.with_suffix('.lock'); lock.parent.mkdir(parents=True,exist_ok=True)
    # Prevent overlapping scheduler runs from sending different batches concurrently.
    import fcntl
    with lock.open('w') as handle:
        fcntl.flock(handle,fcntl.LOCK_EX)
        state = read(state_path) if state_path.exists() else {}
        pending = state.get('pending')
        triggers = [t for t in triggers if t['key'] not in state.get('completed',{})]
        if not pending and not triggers: return {'status':'quiet'}
        if pending and (pending['destination'] != dest or pending.get('project_key') != project_key):
            raise RuntimeError('Resolve pending receipt before changing destination')
        if not pending:
            keys = sorted(t['key'] for t in triggers)
            token = hashlib.sha256('|'.join(keys).encode()).hexdigest()[:32]
            pending = {'project_key':project_key,'keys':keys,'idempotency_key':token,'destination':dest,'card':card,'started_at':datetime.now(timezone.utc).isoformat()}
            state['pending']=pending; write(state_path,state)
        if not pending.get('message_id'):
            if datetime.now(timezone.utc)-instant(pending['started_at']) > timedelta(hours=1):
                raise RuntimeError('Uncertain send older than one hour; reconcile chat before retry')
            argv = ['lark-cli','im','+messages-send','--as',dest['as'],'--user-id' if dest['type']=='user' else '--chat-id',dest['id'],'--msg-type','interactive','--content',json.dumps(pending['card'],ensure_ascii=False,separators=(',',':')),'--idempotency-key',pending['idempotency_key'],'--json']
            receipt=call(argv)['data']; pending['message_id']=receipt['message_id']; pending['chat_id']=receipt.get('chat_id'); write(state_path,state)
        result=call(['lark-cli','im','+messages-mget','--as',dest['as'],'--message-ids',pending['message_id'],'--no-reactions','--json'])['data']['messages']
        if len(result)!=1 or result[0].get('message_id') != pending['message_id'] or (pending.get('chat_id') and result[0].get('chat_id') != pending['chat_id']) or (dest['type']=='chat' and result[0].get('chat_id') != dest['id']) or result[0].get('deleted') or result[0].get('msg_type')!='interactive':
            raise RuntimeError('Message readback failed; retain receipt and do not resend')
        if pending['card']['header']['title']['content'] not in result[0].get('content',''):
            raise RuntimeError('Readback title mismatch')
        for key in pending['keys']: state.setdefault('completed',{})[key]=pending['message_id']
        state.pop('pending'); write(state_path,state)
        return {'status':'sent_and_read_back','message_id':result[0]['message_id'],'link':result[0].get('message_app_link')}


def main():
    ap=argparse.ArgumentParser(); ap.add_argument('action',choices=['validate','collect','due','deliver'])
    ap.add_argument('--config',required=True); ap.add_argument('--project'); ap.add_argument('--snapshot');ap.add_argument('--output');ap.add_argument('--state');ap.add_argument('--card');ap.add_argument('--triggers');ap.add_argument('--send',action='store_true')
    a=ap.parse_args(); c=config(a.config)
    if a.action=='validate': result={'valid':True,'projects':[p['key'] for p in c['projects']],'enabled':c['enabled']}
    elif a.action=='collect':
        p=next(p for p in c['projects'] if p['key']==a.project);result=collect(c,p)
    elif a.action=='due':
        state=read(a.state) if a.state and Path(a.state).exists() else {}
        result=due(c,read(a.snapshot),state,datetime.now(timezone.utc))
    else:
        if not a.send: raise ValueError('Delivery requires --send and existing recipient authorization')
        result=deliver(c,read(a.snapshot),read(a.card),a.state,read(a.triggers))
    if a.output:write(a.output,result); print(json.dumps({'output':str(Path(a.output).resolve())}))
    else:print(json.dumps(result,ensure_ascii=False))
if __name__=='__main__':main()
