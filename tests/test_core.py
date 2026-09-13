import hashlib
import io
import json
import subprocess
import tempfile
import unittest
from unittest.mock import MagicMock, patch
from pathlib import Path

from PIL import Image, ImageDraw

from cosmmd.publish_guard import audit, violations
from cosmmd.qa import inspect_frames
from cosmmd.tripo import TripoError, download_image, generate, prepare_tpose, submit_once


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


class TposeTests(unittest.TestCase):
    def test_prepared_image_becomes_the_3d_input(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            photo = root / 'photo.png'
            Image.new('RGB', (30, 40), '#bb8877').save(photo)
            prepared = io.BytesIO()
            Image.new('RGB', (40, 40), '#dddddd').save(prepared, format='PNG')
            client = MagicMock()
            client.upload_image.side_effect = ['photo-token', 'tpose-token']
            client.request.side_effect = [
                {'task_id': 'pose-task'}, {'task_id': 'model-task'},
                {'riggable': True, 'rig_type': 'biped'}, {'task_id': 'rig-task'}]
            client.wait.side_effect = [
                {'output': {'generated_image_url': 'https://example.com/pose.png'}},
                {'output': {'model_url': 'https://example.com/source.glb'}},
                {'output': {'model_url': 'https://example.com/rig.glb'}}]
            with patch('cosmmd.tripo.TripoClient', return_value=client), \
                 patch('cosmmd.tripo.urlopen', return_value=io.BytesIO(prepared.getvalue())), \
                 patch('cosmmd.tripo.download_model'):
                pose_result = prepare_tpose(photo, root / 'run', execute=True)
                result = generate(pose_result['t_pose'], root / 'run/model', execute=True)
            generation = client.request.call_args_list[1].args
            self.assertEqual(generation[1], '/generation/image-to-model')
            self.assertEqual(generation[2]['input'], 'tpose-token')
            uploaded_pose = Path(client.upload_image.call_args_list[1].args[0])
            self.assertEqual(uploaded_pose, Path(pose_result['t_pose']))
            self.assertNotEqual(uploaded_pose.read_bytes(), photo.read_bytes())
            self.assertEqual(result['status'], 'generated_and_auto_rigged')

    def test_prepare_plan_is_offline_and_selects_nano_banana_pro(self):
        with patch('cosmmd.tripo.TripoClient') as client:
            plan = prepare_tpose('photo.jpg', 'private/character')
        client.assert_not_called()
        self.assertEqual((plan['model'], plan['template']), ('banana_pro', 't_pose'))
        self.assertEqual(plan['paid_task_submissions_at_most'], 1)

    def test_download_failure_resumes_the_same_image_task(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            photo = root / 'photo.png'
            Image.new('RGB', (30, 40), '#bb8877').save(photo)
            client = MagicMock()
            client.upload_image.return_value = 'original-token'
            client.request.return_value = {'task_id': 'pose-task'}
            client.wait.return_value = {'output': {'generated_image_url': 'https://example.com/pose.png'}}
            def downloaded(result, path):
                Image.new('RGB', (40, 40), '#dddddd').save(path)
            with patch('cosmmd.tripo.TripoClient', return_value=client), \
                 patch('cosmmd.tripo.download_image', side_effect=TripoError('connection lost')):
                with self.assertRaises(TripoError):
                    prepare_tpose(photo, root / 'run', execute=True)
            self.assertFalse((root / 'run/.tpose.lock').exists())
            with patch('cosmmd.tripo.TripoClient', return_value=client), \
                 patch('cosmmd.tripo.download_image', side_effect=downloaded):
                result = prepare_tpose(photo, root / 'run', execute=True)
                Image.new('RGB', (30, 40), '#112233').save(photo)
                with self.assertRaises(TripoError):
                    prepare_tpose(photo, root / 'run', execute=True)
            self.assertEqual(client.request.call_count, 1)
            self.assertEqual(client.upload_image.call_count, 1)
            method, endpoint, payload = client.request.call_args.args
            self.assertEqual((method, endpoint), ('POST', '/generation/image-to-image'))
            self.assertEqual(payload['model'], 'banana_pro')
            self.assertEqual(payload['template'], 't_pose')
            self.assertEqual(payload['input'], 'original-token')
            self.assertEqual(result['status'], 't_pose_ready_for_review')
            provenance = json.loads((root / 'run/tpose_provenance.json').read_text())
            self.assertEqual(provenance['tpose_sha256'], hashlib.sha256(Path(result['t_pose']).read_bytes()).hexdigest())

    def test_download_uses_no_authorization_and_rejects_non_images(self):
        image_bytes = io.BytesIO()
        Image.new('RGB', (20, 20), '#112233').save(image_bytes, format='PNG')
        url = 'https://example.com/pose.png'
        with tempfile.TemporaryDirectory() as tmp:
            target = Path(tmp) / 't_pose.png'
            with patch('cosmmd.tripo.urlopen', return_value=io.BytesIO(image_bytes.getvalue())) as opened:
                download_image({'output': {'generated_image_url': url}}, target)
                opened.assert_called_once_with(url, timeout=180)
            with Image.open(target) as decoded:
                self.assertEqual(decoded.size, (20, 20))
            before = target.read_bytes()
            with patch('cosmmd.tripo.urlopen', return_value=io.BytesIO(b'not an image')):
                with self.assertRaises(TripoError):
                    download_image({'output': {'generated_image_url': url}}, target)
            self.assertEqual(target.read_bytes(), before)
            self.assertFalse(target.with_suffix('.download').exists())


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
