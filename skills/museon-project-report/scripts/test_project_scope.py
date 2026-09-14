"""Regression checks for same-customer AI/UGC routing; no network or sends."""
import copy
import unittest
from unittest.mock import patch

import report
import render_card


class ProjectScopeTests(unittest.TestCase):
    def setUp(self):
        self.ai = dict(key='ai-client', name='Same Customer', project_type='ai',
                       source='hireaicreator', workspace_id='workspace',
                       campaign_id='ai-project', timezone='Asia/Shanghai')
        self.ugc = dict(self.ai, key='ugc-client', project_type='ugc',
                        source='museon', campaign_id='ugc-project')

    def test_explicit_type_source_pairs(self):
        report.validate_project_scope(self.ai)
        report.validate_project_scope(self.ugc)
        for p in (dict(self.ai, source='museon'), dict(self.ugc, source='hireaicreator'),
                  dict(self.ai, project_type=None), dict(self.ai, source=None)):
            with self.assertRaises(ValueError):
                report.validate_project_scope(p)

    def test_ugc_or_legacy_never_enters_ai_collection(self):
        for p in (self.ugc, {k:v for k,v in self.ai.items() if k not in ('project_type','source')}):
            with patch.object(report, 'call') as cli:
                with self.assertRaises(ValueError):
                    report.collect({}, p)
                cli.assert_not_called()

    def test_ai_uses_hireaicreator_and_exact_id(self):
        rows = [dict(id='a', workspace_id='workspace', campaign_id='ai-project'),
                dict(id='b', workspace_id='workspace', campaign_id='ugc-project')]
        with patch.object(report, 'call', return_value={'data':{'total':2,'items':rows,'has_more':False}}) as cli:
            snap = report.collect({'cli':['museoncli'],'history_days':7}, self.ai)
        self.assertEqual([v['id'] for v in snap['videos']], ['a'])
        self.assertEqual(cli.call_args.args[0][1:4], ['hireaicreator','video','+list'])

    def test_ugc_cannot_render_or_schedule_or_send_as_ai(self):
        snap = {'project':self.ugc}
        with self.assertRaises(ValueError):
            render_card.render(snap)
        with self.assertRaises(ValueError):
            report.due({}, snap, {}, None)
        with patch.object(report, 'call') as cli:
            with self.assertRaises(ValueError):
                report.deliver({}, snap, {}, None, [])
            cli.assert_not_called()

    def test_explicit_ai_still_renders(self):
        snap = {'project':copy.deepcopy(self.ai),'observed_at':'2026-09-15T00:00:00Z',
                'videos':[], 'posts':{}, 'performance':{}}
        card = render_card.render(snap)
        self.assertEqual(card['schema'], '2.0')
        self.assertEqual(card['header']['template'], 'yellow')


if __name__ == '__main__':
    unittest.main()
