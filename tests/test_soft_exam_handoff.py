"""Real loopback handoff: draft waits, browser dispatch and frozen submissions."""
from concurrent.futures import ThreadPoolExecutor
import contextlib
import io
import json
from pathlib import Path
import subprocess
import sys
import tempfile
import threading
import time
import unittest
from unittest.mock import patch
from urllib.request import ProxyHandler, Request, build_opener

from test_soft_exam_lab import fixtures, lab, SKILL


class HandoffTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.contexts = contextlib.ExitStack()
        self.addCleanup(self.contexts.close)
        self.root = Path(self.temp.name)
        pack, rubric = fixtures()
        lab.atomic(self.root / 'pack.json', pack)
        lab.atomic(self.root / 'rubric.json', rubric)
        self.path = lab.prepare(self.root / 'archive', self.root / 'pack.json', self.root / 'rubric.json')
        self.engine = lab.Session(self.path)
        self.http = build_opener(ProxyHandler({}))

    def start_server(self, open_browser=False, **mock_options):
        output = io.StringIO()
        opened = threading.Event()
        errors = []
        def browser(*args, **kwargs):
            opened.set()
            if mock_options.get('fail'):
                raise OSError('no desktop')
            return True
        mock = self.contexts.enter_context(patch.object(lab.webbrowser, 'open', side_effect=browser))
        self.contexts.enter_context(contextlib.redirect_stdout(output))
        def run():
            try:
                lab.serve(self.path, open_browser=open_browser)
            except BaseException as exc:
                errors.append(exc)
        thread = threading.Thread(target=run, daemon=True)
        thread.start()
        def stop():
            if thread.is_alive():
                state = self.engine.state()
                lab.atomic(self.path / 'state.json', dict(state, status='archived'))
                thread.join(3)
            self.assertFalse(thread.is_alive())
            self.assertEqual(errors, [])
        self.addCleanup(stop)
        deadline = time.monotonic() + 4
        while time.monotonic() < deadline:
            url = lab.service_url(self.engine)
            if url:
                if open_browser:
                    self.assertTrue(opened.wait(1))
                return url, mock, output
            if errors:
                raise errors[0]
            time.sleep(.02)
        self.fail('server did not become healthy')

    def request(self, url, action=None, body=None, token=None):
        request = Request(url + ('/api/' + action if action else '/'))
        if action:
            request.data = json.dumps(body).encode()
            request.add_header('Content-Type', 'application/json')
            request.add_header('Origin', url)
            request.add_header('X-Lab-Token', token)
        with self.http.open(request, timeout=2) as response:
            raw = response.read().decode()
        return json.loads(raw) if action else raw

    def submit_http(self, url):
        page = self.request(url)
        data = json.loads(page.split('<script id="lab-data" type="application/json">')[1].split('</script>')[0])
        state = data['state']
        body = {'attempt_id': state['attempt_id'], 'revision': state['revision']}
        state = self.request(url, 'start', body, data['token'])
        state['answers']['q-write']['markdown'] = '数据库先提交成功，再删除旧缓存。'
        body = {'attempt_id': state['attempt_id'], 'revision': state['revision'], 'answers': state['answers']}
        return self.request(url, 'submit', body, data['token'])

    def test_default_serve_requests_actual_loopback_browser_and_health_is_public_only(self):
        url, mock, output = self.start_server(open_browser=True)
        mock.assert_called_once_with(url, new=2)
        self.assertTrue(url.startswith('http://127.0.0.1:'))
        with self.http.open(url + '/api/health') as response:
            health = json.load(response)
        self.assertEqual(health, {'attempt_id': self.engine.state()['attempt_id'], 'status': 'draft'})
        self.assertEqual(json.loads(output.getvalue().splitlines()[0])['url'], url)

    def test_cli_default_open_and_no_open_option(self):
        for flags, expected in (([], True), (['--no-open'], False)):
            with self.subTest(flags=flags), patch.object(sys, 'argv', ['lab.py', 'serve', '--session', str(self.path), *flags]), patch.object(lab, 'serve') as serve:
                lab.main()
                serve.assert_called_once_with(str(self.path), 0, expected)

    def test_no_open_keeps_link_usable(self):
        url, mock, _ = self.start_server()
        self.assertIn('lab-data', self.request(url))
        mock.assert_not_called()

    def test_browser_failure_keeps_service_and_url(self):
        url, _, output = self.start_server(open_browser=True, fail=True)
        self.assertIn('lab-data', self.request(url))
        self.assertIn('browser_open_failed', output.getvalue())

    def test_draft_timeout_does_not_mutate_or_submit(self):
        url, _, _ = self.start_server()
        before = (self.path / 'state.json').read_bytes()
        result = lab.wait_for_submission(self.path, timeout=.08, interval=.02)
        self.assertEqual((result['event'], result['status'], result['url']), ('timeout', 'draft', url))
        self.assertEqual(before, (self.path / 'state.json').read_bytes())
        self.assertFalse((self.path / 'submission.json').exists())

    def test_real_http_submit_wakes_waiter_and_preserves_answer(self):
        url, _, _ = self.start_server()
        with ThreadPoolExecutor(max_workers=1) as pool:
            waiting = pool.submit(lab.wait_for_submission, self.path, 3, .02)
            submitted = self.submit_http(url)
            result = waiting.result(timeout=4)
        self.assertEqual(result['event'], 'submitted')
        self.assertEqual(result['attempt_id'], submitted['attempt_id'])
        self.assertEqual(lab.read(result['submission'])['answers'], submitted['answers'])

    def test_cli_wait_and_status_reuse_current_service(self):
        url, _, _ = self.start_server()
        for command in ('status', 'wait'):
            args = [sys.executable, str(SKILL / 'scripts/lab.py'), command, '--session', str(self.path)]
            if command == 'wait':
                args += ['--timeout', '0']
            call = subprocess.run(args, capture_output=True, text=True, check=True)
            self.assertEqual(json.loads(call.stdout)['url'], url)

    def test_stale_file_and_foreign_attempt_are_not_live_links(self):
        url, _, _ = self.start_server()
        service = lab.read(self.path / 'service.json')
        lab.atomic(self.path / 'service.json', dict(service, attempt_id='other'))
        self.assertIsNone(lab.service_url(self.engine))
        # The file claims the correct identity, but the actual server belongs elsewhere.
        other = lab.prepare(self.root / 'other', self.root / 'pack.json', self.root / 'rubric.json')
        other_engine = lab.Session(other)
        lab.atomic(other / 'service.json', dict(service, attempt_id=other_engine.state()['attempt_id']))
        self.assertIsNone(lab.service_url(other_engine))
        self.assertEqual(lab.wait_for_submission(other, timeout=0)['event'], 'service_unavailable')
        lab.atomic(self.path / 'service.json', dict(service, port=0))
        self.assertIsNone(lab.service_url(self.engine))

    def test_missing_service_reports_unavailable_without_changing_draft(self):
        result = lab.wait_for_submission(self.path, timeout=0)
        self.assertEqual(result['event'], 'service_unavailable')
        self.assertEqual(self.engine.state()['status'], 'draft')

    def test_stopped_server_is_not_reported_as_listening(self):
        process = subprocess.Popen([sys.executable, str(SKILL / 'scripts/lab.py'), 'serve', '--session', str(self.path), '--no-open'], stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True)
        try:
            ready = json.loads(process.stdout.readline())
            self.assertTrue(ready['url'].startswith('http://127.0.0.1:'))
        finally:
            process.terminate()
            process.communicate(timeout=3)
        self.assertIsNone(lab.service_url(self.engine))
        self.assertEqual(lab.wait_for_submission(self.path, timeout=0)['event'], 'service_unavailable')

    def test_tampered_submission_rejected_and_terminal_state_does_not_need_service(self):
        state = self.engine.state()
        self.engine.update('start', {'attempt_id': state['attempt_id'], 'revision': state['revision']})
        state = self.engine.state()
        self.engine.update('submit', {'attempt_id': state['attempt_id'], 'revision': state['revision']})
        self.assertEqual(lab.wait_for_submission(self.path, timeout=0)['event'], 'submitted')
        frozen = lab.read(self.path / 'submission.json')
        frozen['answers']['q-write']['markdown'] = 'tampered'
        lab.atomic(self.path / 'submission.json', frozen)
        with self.assertRaises(lab.LabError):
            lab.wait_for_submission(self.path, timeout=0)

    def test_wait_rejects_unbounded_durations(self):
        for timeout, interval in ((-1, 1), (61, 1), (1, 0), (float('nan'), 1), (1, float('inf'))):
            with self.subTest(timeout=timeout, interval=interval), self.assertRaises(lab.LabError):
                lab.wait_for_submission(self.path, timeout, interval)


if __name__ == '__main__':
    unittest.main()
