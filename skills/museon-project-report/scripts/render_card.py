#!/usr/bin/env python3
"""Render a local CLI snapshot into a Feishu schema 2.0 card (no network IO)."""
import argparse
import json
import re
from collections import Counter
from datetime import datetime
from decimal import Decimal, ROUND_HALF_UP
from pathlib import Path
from urllib.parse import urlparse
from zoneinfo import ZoneInfo

LIMIT = 30000
STAGES = (("promotable", "推广内容"), ("warmup", "养号内容"))


def instant(value):
    if not value:
        return None
    result = datetime.fromisoformat(value.replace("Z", "+00:00"))
    if result.tzinfo is None or result.utcoffset() is None:
        raise ValueError("Timestamps must include an explicit timezone: " + value)
    return result


def number(value):
    if value is None or isinstance(value, bool):
        return None
    try:
        result = Decimal(str(value))
        return result if result.is_finite() and result >= 0 else None
    except Exception:
        return None


def plain(value, cap=160):
    text = re.sub(r"[\[\]<>*_`\\]", "", " ".join(str(value or "").split()))
    return text if len(text) <= cap else text[:cap - 1] + "…"


def md(text, center=False):
    result = {"tag": "markdown", "content": text}
    if center:
        result["text_align"] = "center"
    return result


def box(elements, color="grey-50"):
    return {"tag": "column_set", "flex_mode": "none", "horizontal_spacing": "8px", "columns": [{"tag": "column", "width": "weighted", "weight": 1,
            "padding": "12px", "background_style": color, "vertical_spacing": "8px", "elements": elements}]}


def kpis(values):
    return {"tag": "column_set", "flex_mode": "none", "horizontal_spacing": "8px", "columns": [{"tag": "column", "width": "weighted", "weight": 1,
            "background_style": "grey-50", "padding": "12px", "vertical_spacing": "4px", "elements": [md("**" + value + "**", True), md(label, True)]}
            for value, label in values]}


def render(snapshot, title_cap=76, detail=True):
    project = snapshot["project"]
    if project.get('project_type') != 'ai' or project.get('source') != 'hireaicreator':
        raise ValueError('AI renderer requires an explicitly confirmed ai/hireaicreator project. Reconfirm legacy scope or use the UGC reporting route.')
    tz = ZoneInfo(project["timezone"])
    now = instant(snapshot["observed_at"])
    if now is None:
        raise ValueError("observed_at is required")
    now = now.astimezone(tz)
    videos = snapshot["videos"]
    identities = [v["id"] for v in videos]
    if len(identities) != len(set(identities)):
        raise ValueError("Duplicate video IDs: finish stable pagination before rendering")
    perf, posts = snapshot.get("performance", {}), snapshot.get("posts", {})
    for v in videos:
        if v.get("workspace_id") and v["workspace_id"] != project["workspace_id"]:
            raise ValueError("Snapshot contains another workspace")
        if project.get("campaign_id") and v.get("campaign_id") != project["campaign_id"]:
            raise ValueError("Snapshot contains another or unknown campaign")
    def local(value):
        result = instant(value)
        return result.astimezone(tz) if result else None
    def active(rows):
        return [r for r in rows if r.get("status") != "cancelled"]
    def published(rows):
        return [r for r in rows if r.get("status") == "published"]
    def cids(rows):
        return sorted({r["published_content_id"] for r in published(rows) if r.get("published_content_id")})
    def metrics(rows):
        ids = cids(rows)
        known = [number(perf.get(cid, {}).get("views")) for cid in ids]
        known = [n for n in known if n is not None]
        average = str((sum(known) / len(known)).quantize(Decimal("0.1"), rounding=ROUND_HALF_UP)) if known else "—"
        return average, len(known), len(ids)
    def actual_today(rows):
        return [r for r in published(rows) if local(posts.get(r.get("published_content_id"), {}).get("published_at"))
                and local(posts[r["published_content_id"]]["published_at"]).date() == now.date()]
    def scheduled_today(rows):
        return [r for r in active(rows) if local(r.get("scheduled_at")) and local(r["scheduled_at"]).date() == now.date()]
    a = active(videos)
    today = scheduled_today(videos)
    future = [r for r in a if local(r.get("scheduled_at")) and local(r["scheduled_at"]) > now]
    elements = [box([md(f"**项目总计｜今日排期已发 {len(published(today))} / 应发 {len(today)} 条**"),
        md(f"今日实际发布 {len(cids(actual_today(a)))} 帖 · 已登记未来 {len(future)} 条（含今日未到期）")], "yellow-50")]
    unknown = Counter(str(v.get("account_operation_stage") or "空值") for v in videos if v.get("account_operation_stage") not in dict(STAGES))
    if unknown:
        elements.append(box([md("**分类待核对**"), md("；".join(f"{plain(k)}：{n} 条" for k, n in unknown.items()) + "。已计入项目总计，未猜测归入推广或养号。")]))
    for stage, label in STAGES:
        rows = [v for v in videos if v.get("account_operation_stage") == stage]
        elements.append(box([md(f"**{label}**", True)], "blue-50"))
        if not rows:
            elements.append(md("没有" + label))
            continue
        live = active(rows)
        stoday = scheduled_today(rows)
        future_times = sorted({local(v["scheduled_at"]) for v in live if local(v.get("scheduled_at")) and local(v["scheduled_at"]) > now})
        avg, known, total = metrics(actual_today(live))
        elements.append(kpis([(f"{len(published(stoday))}/{len(stoday)}", "今日排期已发 / 应发"),
            (avg, f"今日实际发布均播 · {known}/{total} 帖有数据"),
            (future_times[0].strftime("%m/%d %H:%M") if future_times else "—", "下一波时间")]))
        times = sorted({local(v["scheduled_at"]) for v in rows if local(v.get("scheduled_at"))}, reverse=True)
        table_rows = []
        for when in times:
            wave = [v for v in rows if local(v.get("scheduled_at")) == when]
            wa = active(wave)
            counts = Counter(v.get("status") or "unknown" for v in wa)
            names = {"scheduled": "已排期" if when > now else "待发布确认", "planned": "计划中", "missed": "错过窗口", "publishing": "发布中", "generating": "生成中", "pending-review": "待审核", "approved": "已审核", "pending": "待处理"}
            state = [f"{count} {names.get(status, status)}" for status, count in sorted(counts.items()) if status != "published"]
            failures = sum(v.get("render_job_status") == "failed" for v in wa)
            if failures:
                state.append(f"其中渲染失败 {failures}")
            pf = sum(v.get("publish_task_status") == "failed" for v in wa)
            if pf:
                state.append(f"其中发布任务失败 {pf}")
            if not state:
                state = ["已发完" if wa and len(published(wa)) == len(wa) else "无有效排期"]
            if len(wave) > len(wa):
                state.append(f"取消 {len(wave)-len(wa)}")
            mean, count, count_total = metrics(wa)
            engagement_values = [[number(perf.get(cid, {}).get(k)) for k in ("likes", "comments", "shares", "collects")] for cid in cids(wa)]
            complete = [vals for vals in engagement_values if all(n is not None for n in vals)]
            interaction = str(sum(sum(vals) for vals in complete)) if complete else "—"
            if complete and len(complete) != len(engagement_values): interaction += f" ({len(complete)}/{len(engagement_values)})"
            table_rows.append({"engagement": interaction, "wave": when.strftime("%Y/%m/%d %H:%M") + (" · 未来" if when > now else ""),
                "progress": f"{len(published(wa))}/{len(wa)}", "average": f"{mean} ({count}/{count_total})", "state": "；".join(state)})
        if table_rows:
            elements.append({"tag": "table", "page_size": 10, "row_height": "auto", "columns": [
                {"name": key, "display_name": title, "data_type": "text", "width": width}
                for key, title, width in [("wave", "近期及未来排期", "25%"), ("progress", "已发/应发", "15%"),
                    ("average", "均播(覆盖)", "16%"), ("engagement", "累计互动", "12%"), ("state", "状态", "32%")]], "rows": table_rows})
        unscheduled = sum(not v.get("scheduled_at") for v in rows)
        if unscheduled:
            elements.append(md(f"无排期时间 {unscheduled} 条，未纳入波次表。"))
        elapsed = sorted({local(v["scheduled_at"]) for v in live if local(v.get("scheduled_at")) and local(v["scheduled_at"]) <= now})
        top_elements = [md("**最近已到排期波次 · 播放 TOP 3**")]
        if elapsed:
            latest = elapsed[-1]
            batch = [v for v in live if local(v.get("scheduled_at")) == latest]
            ranked = sorted([cid for cid in cids(batch) if number(perf.get(cid, {}).get("views")) is not None],
                            key=lambda cid: (-number(perf[cid]["views"]), cid))[:10]
            top_elements.append(md(latest.strftime("%m/%d %H:%M") + "；累计播放排名，不代表相同发布年龄。"))
            top_rows = []
            for rank, cid in enumerate(ranked, 1):
                post = posts.get(cid, {})
                data = post.get("platform_data") or {}
                url = data.get("share_url") or data.get("share_link") or post.get("post_url")
                if not isinstance(url, str) or urlparse(url).scheme not in ("http", "https") or any(c in url for c in "\n\r"):
                    url = None
                title = plain(post.get("title") or post.get("description") or "帖子 " + cid, title_cap)
                title = f"[{title}]({url.replace(')', '%29')})" if url else title + "（缺少帖子链接）"
                author = post.get("author") or ("@" + urlparse(url).path.split("/@", 1)[1].split("/", 1)[0] if url and "/@" in urlparse(url).path else "")
                author_label = " · " + plain(author, 50) if author else ""
                top_rows.append(md(f"**{rank}. {number(perf[cid]['views']):,} 次播放**{author_label}\n{title}"))
            top_elements.extend(top_rows[:3])
            if len(top_rows) > 3:
                top_elements.append({"tag": "collapsible_panel", "expanded": False,
                    "header": {"title": {"tag": "plain_text", "content": f"展开第 4–{len(top_rows)} 名"}}, "elements": top_rows[3:]})
            if not ranked:
                top_elements.append(md("本波尚无已发布且播放数据可用的帖子。"))
        else:
            top_elements.append(md("尚无已到排期波次。"))
        elements.append(box(top_elements))
        issues = Counter()
        for v in live:
            when = local(v.get("scheduled_at"))
            prefix = when.strftime("%m/%d %H:%M") if when else "无排期时间"
            code = v.get("materialize_block_code")
            if code:
                issues[f"{prefix} · 物化阻塞 {plain(code, 70)}"] += 1
            for field, desc in (("render_job_status", "渲染失败"), ("publish_task_status", "发布任务失败")):
                if v.get(field) == "failed":
                    issues[f"{prefix} · {desc}"] += 1
            if when and when <= now and v.get("status") != "published":
                issues[f"{prefix} · 到期仍为 {plain(v.get('status') or 'unknown', 30)}"] += 1
        focus = "\n".join(f"{key}：{count} 条" for key, count in issues.items()) or "未发现字段标明的失败、阻塞或到期未完成项。"
        if not detail and len(focus) > 1500:
            focus = f"共有 {sum(issues.values())} 项状态/错误标记（同一内容可重复计数）；为满足卡片大小限制，详细错误分组已省略，请查看输入快照。"
        elements.append(box([md("**当前关注**"), md(focus + "\n状态和错误标记可重叠；未确认发布不等于平台未发，原因仅以字段为准。")]))
    ids = cids(a)
    updates = [local(perf[cid].get("updated_at")) for cid in ids if cid in perf and perf[cid].get("updated_at")]
    updates = [u for u in updates if u]
    coverage = sum(number(perf.get(cid, {}).get("views")) is not None for cid in ids)
    interactions = []
    for key, label in (("likes", "赞"), ("comments", "评论"), ("shares", "分享"), ("collects", "收藏")):
        nums = [number(perf.get(cid, {}).get(key)) for cid in ids]
        nums = [n for n in nums if n is not None]
        interactions.append(f"{label} {sum(nums):,}（{len(nums)}/{len(ids)}）" if nums else f"{label} —（0/{len(ids)}）")
    freshness = f"{min(updates):%m/%d %H:%M}–{max(updates):%m/%d %H:%M}" if updates else "未知"
    elements.append(md(f"范围：输入快照全部已登记排期；未来表可翻页。今日按 {now:%Y-%m-%d} / {plain(project['timezone'])}。今日进度按排期日；今日均播仅按帖子实际 published_at 当日，缺发布时间不纳入。均播按去重 content_id 的已发布且播放可用帖子计算，含明确 0，缺失不作 0；括号为指标覆盖帖数。播放覆盖 {coverage}/{len(ids)}；累计互动：{' · '.join(interactions)}。指标更新时间 {freshness}，采集时间不等于平台指标更新时间。取消不计应发。"))
    name = plain(project["name"], 60)
    return {"schema": "2.0", "config": {"update_multi": True, "width_mode": "fill", "summary": {"content": f"{name}｜推广与养号发布快报"}},
        "header": {"template": "yellow", "title": {"tag": "plain_text", "content": name + "｜项目发布快报"},
            "subtitle": {"tag": "plain_text", "content": now.strftime("%Y/%m/%d %H:%M") + " · " + project["timezone"]}},
        "body": {"direction": "vertical", "padding": "12px", "vertical_spacing": "12px", "elements": elements}}


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--snapshot", required=True, type=Path)
    parser.add_argument("--output", required=True, type=Path)
    args = parser.parse_args()
    snapshot = json.loads(args.snapshot.read_text())
    for cap, detail in ((76, True), (36, False), (16, False)):
        card = render(snapshot, cap, detail)
        payload = json.dumps(card, ensure_ascii=False, separators=(",", ":"))
        if len(payload.encode("utf-8")) <= LIMIT:
            args.output.parent.mkdir(parents=True, exist_ok=True)
            args.output.write_text(payload)
            print(json.dumps({"output": str(args.output), "bytes": len(payload.encode()), "title_limit": cap}))
            return
    raise SystemExit("Card exceeds 30000 bytes even after compression. No output written; split the snapshot into explicitly labelled card parts. All future schedule rows were preserved.")


if __name__ == "__main__":
    main()
