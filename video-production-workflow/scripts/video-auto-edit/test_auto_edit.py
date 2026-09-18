import json
from pathlib import Path
import subprocess
import sys
import tempfile
import unittest

CLI = Path(__file__).with_name('auto_edit.py')


class PlanCLI(unittest.TestCase):
    def test_explicit_multisource_plan(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            for name in ('a', 'b'):
                subprocess.run(['ffmpeg', '-v', 'error', '-f', 'lavfi', '-i',
                                'color=size=160x90:rate=25:duration=2', '-f', 'lavfi',
                                '-i', 'sine=duration=2', '-shortest', str(root / f'{name}.mp4')], check=True)
            request = {'version': '1', 'fps': 25, 'sources': {'a': 'a.mp4', 'b': 'b.mp4'},
                       'timeline': [
                           {'id': 'one', 'op': 'keep', 'sourceId': 'a', 'sourceStart': .02,
                            'sourceEnd': 1.02, 'targetStart': 0, 'text': 'first'},
                           {'id': 'two', 'op': 'keep', 'sourceId': 'b', 'sourceStart': 1,
                            'sourceEnd': 2, 'targetStart': 1, 'text': 'second'}]}
            path = root / 'input.json'
            path.write_text(json.dumps(request), encoding='utf-8')
            result = subprocess.run([sys.executable, str(CLI), 'plan', str(root), '--input', str(path)],
                                    capture_output=True, text=True)
            self.assertEqual(result.returncode, 0, result.stderr)
            plan = json.loads((root / 'Rough/edit-plan.v1.json').read_text(encoding='utf-8'))
            self.assertEqual(plan['timeline'][0]['sourceStartFrame'], 1)
            self.assertEqual(plan['timeline'][0]['sourceEndFrame'], 26)
            self.assertEqual(plan['timeline'][1]['sourceStartFrame'], 25)
            self.assertEqual(plan['durationFrames'], 50)
            invalid_cases = [({'sourceEnd': float('nan')}, 'finite'),
                             ({'sourceEnd': float('inf')}, 'finite'),
                             ({'sourceStart': -.1}, 'nonnegative'),
                             ({'sourceEnd': 0}, 'positive'),
                             ({'sourceEnd': 3}, 'bounds'),
                             ({'sourceId': 'missing'}, 'sourceId'),
                             ({'targetStart': .5}, 'overlap')]
            for changes, message in invalid_cases:
                with self.subTest(changes=changes):
                    invalid = dict(request, timeline=[request['timeline'][0], dict(request['timeline'][1], **changes)])
                    path.write_text(json.dumps(invalid), encoding='utf-8')
                    result = subprocess.run([sys.executable, str(CLI), 'validate', str(root), '--plan', str(path)], capture_output=True, text=True)
                    self.assertEqual(result.returncode, 1)
                    self.assertIn(message, result.stderr)
            cross = dict(request, timeline=[request['timeline'][0], dict(request['timeline'][1], targetStart=0, track='Overlay')])
            path.write_text(json.dumps(cross), encoding='utf-8')
            result = subprocess.run([sys.executable, str(CLI), 'validate', str(root), '--plan', str(path)], capture_output=True, text=True)
            self.assertTrue((root / 'Rough/auto-cut-validation.json').is_file())
            self.assertTrue((root / 'Rough/auto-cut-report.md').is_file())
            for command in ('subtitles', 'preview'):
                result = subprocess.run([sys.executable, str(CLI), command, str(root)], capture_output=True, text=True)
                self.assertEqual(result.returncode, 0, result.stderr)
            self.assertIn('00:00:01,000 --> 00:00:02,000', (root / 'Rough/auto-cut.srt').read_text(encoding='utf-8'))
            draft_cli = CLI.parent.parent / 'video-jianying-draft/jianying.py'
            command = [sys.executable, str(draft_cli), 'apply_edit_plan', '--plan',
                       str(root / 'Rough/edit-plan.v1.json'), '--output-dir', str(root / 'Drafts')]
            first = subprocess.run(command, capture_output=True, text=True)
            self.assertEqual(first.returncode, 0, first.stderr)
            second = subprocess.run(command, capture_output=True, text=True)
            self.assertEqual(second.returncode, 0, second.stderr)
            self.assertEqual(json.loads(first.stdout)['draft'], json.loads(second.stdout)['draft'])
            draft_dir = Path(json.loads(first.stdout)['draft']).parent
            self.assertTrue((draft_dir / 'draft_meta_info.json').is_file())
            meta = json.loads((draft_dir / 'draft_meta_info.json').read_text(encoding='utf-8'))
            self.assertEqual(meta['draft_name'], draft_dir.name)
            result = subprocess.run([sys.executable, str(CLI), 'verify-draft', str(root), '--draft',
                                     json.loads(first.stdout)['draft']], capture_output=True, text=True)
            self.assertEqual(result.returncode, 0, result.stderr)
            custom_command = [sys.executable, str(draft_cli), 'apply_edit_plan', '--plan',
                              str(root / 'Rough/edit-plan.v1.json'), '--output-dir', str(root / 'Drafts'),
                              '--draft-id', 'custom_named_draft']
            custom_res = subprocess.run(custom_command, capture_output=True, text=True)
            self.assertEqual(custom_res.returncode, 0, custom_res.stderr)
            self.assertTrue((root / 'Drafts/custom_named_draft/draft_content.json').is_file())
            self.assertTrue((root / 'Drafts/custom_named_draft/draft_meta_info.json').is_file())


if __name__ == '__main__':
    unittest.main()
