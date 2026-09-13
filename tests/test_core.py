import hashlib
import json
import subprocess
import tempfile
import unittest
from pathlib import Path

from PIL import Image, ImageDraw

from cosmmd.publish_guard import audit, violations
from cosmmd.qa import inspect_frames
from cosmmd.tripo import TripoError, generate, submit_once


class Client:
    def __init__(self, fail=False):
        self.submits = 0
        self.fail = fail
    def request(self, *args):
        self.submits += 1
        if self.fail:
            raise TripoError('timeout')
        return {'task_id': 'task_test'}
    def wait(self, task):
        return {'status': 'success', 'task_id': task}


class APITests(unittest.TestCase):
    def test_plan_makes_no_request_and_needs_no_secret(self):
        self.assertEqual(generate('reference.png', 'private/run')['paid_task_submissions_at_most'], 2)

    def test_resume_does_not_charge_again(self):
        with tempfile.TemporaryDirectory() as tmp:
            journal = Path(tmp) / 'tasks.json'
            c = Client()
            first = submit_once(c, journal, 'generation', '/generation/image-to-model', {'input': 'a'})
            again = submit_once(c, journal, 'generation', '/generation/image-to-model', {'input': 'a'})
            self.assertEqual(first, again)
            self.assertEqual(c.submits, 1)
            with self.assertRaises(TripoError):
                submit_once(c, journal, 'generation', '/generation/image-to-model', {'input': 'b'})

    def test_ambiguous_post_is_not_retried(self):
        with tempfile.TemporaryDirectory() as tmp:
            c = Client(fail=True)
            for _ in range(2):
                with self.assertRaises(TripoError):
                    submit_once(c, Path(tmp) / 'tasks.json', 'rig', '/animations/rig', {'input': 'a'})
            self.assertEqual(c.submits, 1)


class QATests(unittest.TestCase):
    def test_black_character_on_valid_background_is_flagged(self):
        with tempfile.TemporaryDirectory() as tmp:
            for n, color in [(1, '#dd7777'), (2, '#000000')]:
                im = Image.new('RGB', (160,160), '#443344')
                ImageDraw.Draw(im).rectangle((50,35,110,135), fill=color)
                im.save(Path(tmp) / f'frame_{n:06}.png')
            result = inspect_frames(tmp, expected=2, step=1)
            self.assertFalse(result['errors'])
            self.assertEqual(result['suspicious_frames'], ['frame_000002.png'])

    def test_corrupt_and_missing_frames_fail(self):
        with tempfile.TemporaryDirectory() as tmp:
            Image.new('RGB',(20,20),'white').save(Path(tmp)/'frame_000001.png')
            (Path(tmp)/'frame_000003.png').write_bytes(b'broken')
            self.assertTrue(inspect_frames(tmp, expected=3, step=1)['errors'])


class PublicationTests(unittest.TestCase):
    def test_secret_binary_and_motion_rejected(self):
        for path, data in [('notes.txt', ('tsk_' + 'x'*40).encode()),
                           ('data.txt', b'Vocaloid Motion Data 0002'),
                           ('motion.VMD', b'data'), ('demo.blend1', b'data'),
                           ('private/data.txt', b'anything')]:
            self.assertTrue(violations(path, data, {}), path)

    def test_media_needs_exact_allowlist_hash(self):
        path, data = 'docs/media/result.gif', b'GIF89a'
        approved = {path: {'sha256': hashlib.sha256(data).hexdigest(), 'rights': 'Reviewed demo render'}}
        self.assertFalse(violations(path, data, approved))
        self.assertTrue(violations(path, data + b'changed', approved))

    def test_audit_reads_staged_blob_not_clean_worktree(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            def git(*args):
                return subprocess.check_output(['git','-C',tmp,*args], stderr=subprocess.DEVNULL)
            git('init','-q')
            (root/'note.txt').write_text('tsk_' + 'x'*40)
            git('add','note.txt')
            (root/'note.txt').write_text('now clean locally')
            self.assertFalse(audit(root, history=False)['ok'])


if __name__ == '__main__':
    unittest.main()
