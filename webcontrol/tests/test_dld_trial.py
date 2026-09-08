"""Offline POSIX tests: every deployed command is a temporary fake shell script.

Run: python3 -m unittest discover -s webcontrol/tests -p test_dld_trial.py
No SSH connections, network listeners, or real panel deployments are made.
"""
from __future__ import print_function

import json
import os
import shutil
import signal
import subprocess
import sys
import tempfile
import time
import unittest

if os.name != 'posix':
    raise unittest.SkipTest('CGI deployment locking and detachment require POSIX')

SOURCE = os.path.abspath(os.path.join(os.path.dirname(__file__), '..',
                                      'usr_lib_cgi-bin', 'dld-trial.cgi'))
try:
    from importlib.machinery import SourceFileLoader
    from importlib.util import module_from_spec, spec_from_loader
    loader = SourceFileLoader('dld_trial', SOURCE)
    spec = spec_from_loader(loader.name, loader)
    api = module_from_spec(spec)
    loader.exec_module(api)
except ImportError:
    import imp
    api = imp.load_source('dld_trial', SOURCE)


class DeploymentTests(unittest.TestCase):
    def setUp(self):
        self.directory = tempfile.mkdtemp(prefix='dld-cgi-test-')
        self.gateway = os.path.join(self.directory, 'gateway')
        self.state = os.path.join(self.directory, 'state')
        os.mkdir(self.gateway)
        os.mkdir(os.path.join(self.gateway, 'tools'))
        os.mkdir(self.state)
        self.config = {'gateway_dir': self.gateway, 'state_dir': self.state}
        self.script = os.path.join(self.gateway, 'tools', 'deploy-trial-digit.sh')
        self.release = os.path.join(self.directory, 'release')
        self.worker_pids = []
        self.write_script('printf "ARG=%s\\n" "$1"\nexit 0\n')
        self.environment = {'REQUEST_METHOD': 'GET', 'QUERY_STRING': 'action=session',
                            'HTTP_HOST': 'clock.example', 'HTTPS': 'on'}
        status, result, headers = api.request(self.environment, b'', self.config)
        self.assertEqual(status, 200)
        self.token = result['token']
        self.cookie = dict(headers)['Set-Cookie'].split(';', 1)[0]
        self.assertIn('HttpOnly', dict(headers)['Set-Cookie'])
        self.assertIn('SameSite=Strict', dict(headers)['Set-Cookie'])
        self.assertIn('Secure', dict(headers)['Set-Cookie'])
        self.environment.update(REQUEST_METHOD='POST', QUERY_STRING='',
                                HTTP_COOKIE=self.cookie, CONTENT_TYPE='application/json',
                                HTTP_ORIGIN='https://clock.example')

    def tearDown(self):
        with open(self.release, 'w') as stream:
            stream.write('done')
        deadline = time.time() + 4
        while time.time() < deadline:
            try:
                active = api.active_job(self.config)
            except Exception:
                active = None
            if active is None:
                break
            time.sleep(0.05)
        for pid in self.worker_pids:
            try:
                os.killpg(pid, signal.SIGTERM)
            except OSError:
                pass
            try:
                os.waitpid(pid, 0)
            except OSError:
                pass
        shutil.rmtree(self.directory)

    def write_script(self, content):
        with open(self.script, 'w') as stream:
            stream.write('#!/bin/sh\nset -eu\n' + content)

    def gated_script(self, exit_code=0):
        self.write_script('printf "ARG=%s\\nLIVE\\n" "$1"\n'
                          'count=0\n'
                          'while [ ! -f "' + self.release + '" ]; do\n'
                          '  count=$((count + 1))\n'
                          '  [ "$count" -lt 15 ] || exit 99\n'
                          '  sleep 1\n'
                          'done\n'
                          'echo FINISHED\nexit ' + str(exit_code) + '\n')

    def tracked_spawn(self, config, identifier, descriptor):
        pid = api.spawn_worker(config, identifier, descriptor)
        self.worker_pids.append(pid)
        return pid

    def post(self, digit='m34', token=None, environment=None, spawn=None):
        body = json.dumps({'digit': digit, 'token': token or self.token}).encode('utf-8')
        return api.request(environment or self.environment, body, self.config,
                           spawn or self.tracked_spawn)

    def fresh_token(self):
        environment = dict(self.environment, REQUEST_METHOD='GET', QUERY_STRING='action=session')
        return api.request(environment, b'', self.config)[1]['token']

    def wait_for(self, identifier, predicate):
        deadline = time.time() + 8
        while time.time() < deadline:
            job = api.public_job(self.config, api.read_job(self.config, identifier))
            if predicate(job):
                return job
            time.sleep(0.05)
        self.fail('Timed out waiting for job: ' + repr(job))

    def assert_api_error(self, status, call):
        try:
            call()
        except api.ApiError as error:
            self.assertEqual(error.status, status, str(error))
            return error
        self.fail('Expected API error ' + str(status))

    def test_uppercase_digit_uses_fixed_script_and_one_lowercase_argument(self):
        status, result, headers = self.post('M34')
        self.assertEqual(status, 202)
        job = self.wait_for(result['job']['id'], lambda item: item['state'] != 'running')
        self.assertEqual(job['state'], 'succeeded')
        self.assertEqual(job['exit_code'], 0)
        self.assertEqual(job['digit'], 'm34')
        self.assertIn('ARG=m34\n', job['output'])
        self.assertIn('exit code 0', job['output'])

    def test_rejects_bad_digits_and_option_injection(self):
        for digit in ('h00', 'h13', 'm60', 'm-1', 'm1', 'm034', '../m34',
                      'm34;touch x', '-m34', 'm34\n', ' m34', None, 34, True):
            self.assert_api_error(400, lambda: self.post(digit))
        self.assertFalse(os.path.exists(os.path.join(self.state, 'active.json')))

    def test_all_72_digit_names_accepted_without_running_commands(self):
        names = ['h%02d' % value for value in range(1, 13)]
        names += ['m%02d' % value for value in range(60)]
        calls = []
        for digit in names:
            status, result, headers = self.post(digit, self.fresh_token(),
                                               spawn=lambda *args: calls.append(args))
            self.assertEqual(status, 202)
        self.assertEqual(len(calls), 72)

    def test_cookie_and_token_are_both_required_and_bound_together(self):
        for update in ({'HTTP_COOKIE': ''}, {'HTTP_COOKIE': api.COOKIE_NAME + '=' + 'a' * 64}):
            environment = dict(self.environment, **update)
            self.assert_api_error(403, lambda: self.post(environment=environment))
        for token in ('invalid', 'a' * 64 + '.' + 'b' * 64, 23, ['invalid']):
            self.assert_api_error(403, lambda: self.post(token=token))

    def test_cross_site_browser_context_rejected_even_with_valid_token(self):
        environment = dict(self.environment, HTTP_SEC_FETCH_SITE='cross-site')
        self.assert_api_error(403, lambda: self.post(environment=environment))

    def test_proxy_rewritten_host_accepts_valid_session_bound_token(self):
        environment = dict(self.environment, HTTP_HOST='localhost',
                           HTTP_ORIGIN='https://clock.dataplicity.example',
                           HTTP_SEC_FETCH_SITE='same-origin')
        calls = []
        status, result, headers = self.post(environment=environment,
                                           spawn=lambda *args: calls.append(args))
        self.assertEqual(status, 202)
        self.assertEqual(len(calls), 1)
        self.assert_api_error(403, lambda: self.post(environment=environment,
                                                   token='a' * 64 + '.' + 'b' * 64))

    def test_get_never_deploys_and_bad_payloads_fail(self):
        environment = dict(self.environment, REQUEST_METHOD='GET', QUERY_STRING='digit=m34')
        self.assert_api_error(400, lambda: api.request(environment, b'', self.config))
        for body in (b'', b'{', b'[]', b'{"digit":"m34"}', b'\xff', b'x' * 4097):
            status = 413 if len(body) > 4096 else 400
            self.assert_api_error(status, lambda: api.request(self.environment, body, self.config))
        environment = dict(self.environment, CONTENT_TYPE='text/plain')
        self.assert_api_error(415, lambda: self.post(environment=environment))
        environment = dict(self.environment, REQUEST_METHOD='PUT')
        self.assert_api_error(405, lambda: self.post(environment=environment))

    def test_duplicate_token_returns_same_job_and_other_digit_conflicts(self):
        self.gated_script()
        status, result, headers = self.post()
        identifier = result['job']['id']
        self.wait_for(identifier, lambda item: 'LIVE' in item['output'])
        status, duplicate, headers = self.post()
        self.assertEqual(status, 200)
        self.assertEqual(duplicate['job']['id'], identifier)
        self.assertEqual(len(self.worker_pids), 1)
        self.assert_api_error(409, lambda: self.post('h01'))
        error = self.assert_api_error(409, lambda: self.post('h01', self.fresh_token()))
        self.assertEqual(error.payload['active_job']['id'], identifier)

    def test_completed_request_stays_idempotent_and_fresh_token_can_redeploy(self):
        status, result, headers = self.post()
        self.wait_for(result['job']['id'], lambda item: item['state'] != 'running')
        status, duplicate, headers = self.post()
        self.assertEqual(status, 200)
        self.assertEqual(len(self.worker_pids), 1)
        status, next_job, headers = self.post(token=self.fresh_token())
        self.assertEqual(status, 202)
        self.assertNotEqual(next_job['job']['id'], duplicate['job']['id'])

    def test_live_output_is_readable_before_failure_exit(self):
        self.gated_script(23)
        status, result, headers = self.post('h01')
        identifier = result['job']['id']
        job = self.wait_for(identifier, lambda item: 'LIVE' in item['output'])
        self.assertEqual(job['state'], 'running')
        self.assertIsNone(job['exit_code'])
        with open(self.release, 'w') as stream:
            stream.write('go')
        job = self.wait_for(identifier, lambda item: item['state'] != 'running')
        self.assertEqual(job['exit_code'], 23)
        self.assertEqual(job['state'], 'failed')
        self.assertIn('FINISHED', job['output'])

    def test_output_is_bounded_and_utf8_errors_do_not_break_status(self):
        status, result, headers = self.post(spawn=lambda *args: None)
        identifier = result['job']['id']
        with open(api.job_path(self.config, identifier, '.log'), 'wb') as log:
            log.write(b'x' * (api.MAX_OUTPUT + 200) + b'\xffEND')
        job = api.public_job(self.config, api.read_job(self.config, identifier), reconcile=False)
        self.assertTrue(job['truncated'])
        self.assertEqual(len(job['output']), api.MAX_OUTPUT)
        self.assertTrue(job['output'].endswith('\ufffdEND'))

    def test_dead_worker_marked_failed_only_when_its_lock_is_free(self):
        held = []
        def hold(config, identifier, descriptor):
            held.append(os.dup(descriptor))
        status, result, headers = self.post(spawn=hold)
        identifier = result['job']['id']
        try:
            job = api.public_job(self.config, api.read_job(self.config, identifier))
            self.assertEqual(job['state'], 'running')
        finally:
            os.close(held[0])
        job = api.public_job(self.config, api.read_job(self.config, identifier))
        self.assertEqual(job['state'], 'failed')
        self.assertEqual(job['exit_code'], 125)
        self.assertIn('without a final status', job['output'])

    def test_worker_failure_keeps_lock_until_deployment_subprocess_exits(self):
        self.gated_script()
        status, result, headers = self.post()
        identifier = result['job']['id']
        self.wait_for(identifier, lambda item: 'LIVE' in item['output'])
        os.kill(self.worker_pids[0], signal.SIGKILL)
        os.waitpid(self.worker_pids[0], 0)
        self.assert_api_error(409, lambda: self.post('h01', self.fresh_token()))
        job = api.public_job(self.config, api.read_job(self.config, identifier))
        self.assertEqual(job['state'], 'running')
        with open(self.release, 'w') as stream:
            stream.write('go')
        job = self.wait_for(identifier, lambda item: item['state'] != 'running')
        self.assertEqual(job['exit_code'], 125)

    def test_spawn_failure_is_durable_and_does_not_hold_lock(self):
        def broken(*args):
            raise OSError('fake spawn failure')
        self.assert_api_error(500, lambda: self.post(spawn=broken))
        pointer = api.read_json(os.path.join(self.state, 'active.json'))
        job = api.public_job(self.config, api.read_job(self.config, pointer['id']))
        self.assertEqual(job['state'], 'failed')
        self.assertIn('fake spawn failure', job['output'])
        descriptor = api.lock_state(self.config)
        self.assertIsNotNone(descriptor)
        os.close(descriptor)

    def test_invalid_and_missing_job_ids(self):
        self.assert_api_error(400, lambda: api.read_job(self.config, '../secret'))
        self.assert_api_error(400, lambda: api.read_job(self.config, '0' * 32 + '\n'))
        self.assert_api_error(404, lambda: api.read_job(self.config, '0' * 32))

    def cgi_process(self, digit, token):
        wrapper = os.path.join(self.directory, 'request-' + api.random_hex(6) + '.py')
        with open(wrapper, 'w') as stream:
            stream.write('values = {"__name__": "cgi_test", "__file__": ' + repr(SOURCE) + '}\n'
                         'with open(' + repr(SOURCE) + ', "r") as source:\n'
                         '    code = compile(source.read(), ' + repr(SOURCE) + ', "exec")\n'
                         'exec(code, values)\n'
                         'values["load_config"] = lambda: ' + repr(self.config) + '\n'
                         'values["main"]()\n')
        environment = os.environ.copy()
        environment.update(self.environment)
        body = json.dumps({'digit': digit, 'token': token}).encode('utf-8')
        environment['CONTENT_LENGTH'] = str(len(body))
        process = subprocess.Popen([sys.executable, wrapper], stdin=subprocess.PIPE,
                                   stdout=subprocess.PIPE, stderr=subprocess.PIPE, env=environment)
        return process, body

    def test_cgi_response_closes_while_detached_worker_continues(self):
        self.gated_script()
        process, body = self.cgi_process('m34', self.token)
        started = time.time()
        output, errors = process.communicate(body)
        self.assertEqual(process.returncode, 0, errors)
        self.assertLess(time.time() - started, 3)
        result = json.loads(output.decode('utf-8').split('\n\n', 1)[1])
        job = self.wait_for(result['job']['id'], lambda item: 'LIVE' in item['output'])
        self.assertEqual(job['state'], 'running')
        self.assertIn('Status: 202', output.decode('utf-8'))

    def test_parallel_duplicate_cgis_start_only_one_job(self):
        self.gated_script()
        first, first_body = self.cgi_process('m34', self.token)
        second, second_body = self.cgi_process('m34', self.token)
        # Send both requests before waiting for either response.
        first.stdin.write(first_body)
        first.stdin.flush()
        second.stdin.write(second_body)
        second.stdin.flush()
        first_output, first_errors = first.communicate()
        second_output, second_errors = second.communicate()
        outputs = [first_output.decode('utf-8'), second_output.decode('utf-8')]
        results = [json.loads(value.split('\n\n', 1)[1]) for value in outputs]
        statuses = sorted(int(value.split(' ', 2)[1]) for value in outputs)
        # Before the winner publishes metadata, a duplicate may receive a
        # transient conflict. It must never start a second deployment.
        self.assertIn(statuses, ([200, 202], [202, 409]))
        identifiers = set(value['job']['id'] for value in results if 'job' in value)
        self.assertEqual(len(identifiers), 1)
        identifier = list(identifiers)[0]
        job = self.wait_for(identifier, lambda item: 'LIVE' in item['output'])
        self.assertEqual(job['output'].count('ARG=m34'), 1)
        status, duplicate, headers = self.post()
        self.assertEqual(status, 200)
        self.assertEqual(duplicate['job']['id'], identifier)

    def test_apache_isindex_arguments_cannot_enter_private_worker_mode(self):
        environment = os.environ.copy()
        environment.update(REQUEST_METHOD='GET', QUERY_STRING='--worker+malicious')
        process = subprocess.Popen([sys.executable, SOURCE, '--worker', '/bad/gateway',
                                    '/bad/state', '0' * 32, '99'],
                                   stdout=subprocess.PIPE, stderr=subprocess.PIPE,
                                   env=environment)
        output, errors = process.communicate()
        # A CGI response (even when CONFIG_PATH is absent on the test host),
        # never a worker traceback or invocation, proves argv was not trusted.
        self.assertEqual(process.returncode, 0, errors)
        self.assertTrue(output.decode('utf-8').startswith('Status: '))


if __name__ == '__main__':
    unittest.main()
