#!/usr/bin/env python3
"""Small CGI API for detached, serialized DLD trial deployments.

Only the fixed, administrator-owned CONFIG_PATH selects local files. HTTP input
can select a digit, never a command, SSH option, gateway path, or configuration.
"""
from __future__ import print_function

import binascii
import errno
import fcntl
import hashlib
import hmac
import json
import os
import re
import subprocess
import sys
import time
from http.cookies import CookieError, SimpleCookie
from urllib.parse import parse_qs


CONFIG_PATH = '/etc/clock-controller/dld-trial.json'
COOKIE_NAME = 'dld_trial_session'
MAX_BODY = 4096
MAX_OUTPUT = 65536
HEX = re.compile(r'\A[0-9a-f]{64}\Z')
JOB_ID = re.compile(r'\A[0-9a-f]{32}\Z')
DIGIT = re.compile(r'\A(?:h(?:0[1-9]|1[0-2])|m[0-5][0-9])\Z')


class ApiError(Exception):
    def __init__(self, status, message, active_job=None):
        Exception.__init__(self, message)
        self.status = status
        self.payload = {'error': message}
        if active_job is not None:
            self.payload['active_job'] = active_job


def random_hex(size):
    return binascii.hexlify(os.urandom(size)).decode('ascii')


def atomic_json(path, value):
    temporary = path + '.' + random_hex(8) + '.tmp'
    descriptor = os.open(temporary, os.O_WRONLY | os.O_CREAT | os.O_EXCL, 0o600)
    try:
        with os.fdopen(descriptor, 'w') as stream:
            json.dump(value, stream, sort_keys=True)
            stream.write('\n')
            stream.flush()
            os.fsync(stream.fileno())
        os.rename(temporary, path)
    finally:
        if os.path.exists(temporary):
            os.unlink(temporary)


def read_json(path):
    with open(path, 'r') as stream:
        return json.load(stream)


def load_config():
    value = read_json(CONFIG_PATH)
    if (not isinstance(value, dict) or
            set(value) != set(['gateway_dir', 'state_dir'])):
        raise ValueError('Invalid DLD gateway configuration')
    for key in ('gateway_dir', 'state_dir'):
        if not isinstance(value[key], str) or not os.path.isabs(value[key]):
            raise ValueError('Gateway configuration paths must be absolute')
        if not os.path.isdir(value[key]):
            raise ValueError('Configured directory does not exist: ' + value[key])
    return value


def lock_state(config, blocking=False):
    descriptor = os.open(os.path.join(config['state_dir'], 'deploy.lock'),
                         os.O_RDWR | os.O_CREAT, 0o600)
    try:
        flags = fcntl.LOCK_EX
        if not blocking:
            flags |= fcntl.LOCK_NB
        fcntl.flock(descriptor, flags)
        return descriptor
    except IOError as error:
        os.close(descriptor)
        if error.errno in (errno.EAGAIN, errno.EACCES):
            return None
        raise


def secret(config):
    # A separate short-held lock avoids a reader seeing a partially written key.
    path = os.path.join(config['state_dir'], 'session-secret')
    descriptor = os.open(path, os.O_RDWR | os.O_CREAT, 0o600)
    with os.fdopen(descriptor, 'r+b') as stream:
        fcntl.flock(stream.fileno(), fcntl.LOCK_EX)
        value = stream.read()
        if not value:
            value = os.urandom(32)
            stream.write(value)
            stream.flush()
        if len(value) != 32:
            raise ValueError('Invalid stored session secret')
        return value


def cookie_session(environ):
    cookies = SimpleCookie()
    try:
        cookies.load(environ.get('HTTP_COOKIE', ''))
        value = cookies[COOKIE_NAME].value
    except (KeyError, ValueError, CookieError):
        return None
    return value if HEX.match(value) else None


def sign_token(key, session, nonce):
    message = (session + ':' + nonce).encode('ascii')
    return hmac.new(key, message, hashlib.sha256).hexdigest()


def equal_bytes(left, right):
    # compare_digest is unavailable on the oldest supported Python (3.2).
    if len(left) != len(right):
        return False
    difference = 0
    for first, second in zip(bytearray(left.encode('ascii')),
                             bytearray(right.encode('ascii'))):
        difference |= first ^ second
    return difference == 0


def valid_token(key, session, token):
    if session is None or not isinstance(token, str):
        return False
    parts = token.split('.')
    return (len(parts) == 2 and HEX.match(parts[0]) is not None and
            HEX.match(parts[1]) is not None and
            equal_bytes(parts[1], sign_token(key, session, parts[0])))


def check_request_context(environ):
    # The public Origin and Apache Host can differ behind Dataplicity. The
    # signed, session-bound token is the CSRF check; no CORS access is granted.
    # Fetch Metadata adds a browser-side check without trusting proxy headers.
    if environ.get('HTTP_SEC_FETCH_SITE') == 'cross-site':
        raise ApiError(403, 'Cross-site deployment requests are not allowed.')


def job_path(config, identifier, suffix):
    return os.path.join(config['state_dir'], identifier + suffix)


def read_job(config, identifier):
    if not isinstance(identifier, str) or not JOB_ID.match(identifier):
        raise ApiError(400, 'Invalid job ID.')
    try:
        return read_json(job_path(config, identifier, '.json'))
    except IOError as error:
        if error.errno == errno.ENOENT:
            raise ApiError(404, 'Deployment job not found.')
        raise


def public_job(config, metadata, reconcile=True):
    if metadata['state'] == 'running' and reconcile:
        descriptor = lock_state(config)
        if descriptor is not None:
            try:
                # No worker or deployment process holds the lock. Re-read in
                # case it completed between our first read and taking the lock.
                metadata = read_job(config, metadata['id'])
                if metadata['state'] == 'running':
                    metadata['state'] = 'failed'
                    metadata['exit_code'] = 125
                    metadata['finished_at'] = time.time()
                    with open(job_path(config, metadata['id'], '.log'), 'a') as log:
                        log.write('\nDeployment worker exited without a final status. '
                                  'Inspect the digit before retrying.\n')
                    atomic_json(job_path(config, metadata['id'], '.json'), metadata)
            finally:
                os.close(descriptor)
    path = job_path(config, metadata['id'], '.log')
    try:
        with open(path, 'rb') as stream:
            stream.seek(0, os.SEEK_END)
            size = stream.tell()
            stream.seek(max(0, size - MAX_OUTPUT))
            output = stream.read(MAX_OUTPUT).decode('utf-8', 'replace')
    except IOError as error:
        if error.errno != errno.ENOENT:
            raise
        size, output = 0, ''
    return {
        'id': metadata['id'], 'digit': metadata['digit'],
        'state': metadata['state'], 'exit_code': metadata['exit_code'],
        'output': output, 'truncated': size > MAX_OUTPUT}


def active_job(config):
    try:
        pointer = read_json(os.path.join(config['state_dir'], 'active.json'))
    except IOError as error:
        if error.errno == errno.ENOENT:
            return None
        raise
    job = public_job(config, read_job(config, pointer['id']))
    return job if job['state'] == 'running' else None


def spawn_worker(config, identifier, lock_descriptor):
    command = [sys.executable, '-u', os.path.abspath(__file__), '--worker',
               config['gateway_dir'], config['state_dir'], identifier,
               str(lock_descriptor)]
    environment = os.environ.copy()
    # Apache may turn an ISINDEX query into argv; only our non-CGI child may
    # use the private worker entry point, even if HTTP input resembles it.
    environment.pop('REQUEST_METHOD', None)
    environment['PYTHONUNBUFFERED'] = '1'
    with open(os.devnull, 'rb') as null, open(job_path(config, identifier, '.log'), 'ab') as log:
        process = subprocess.Popen(command, stdin=null, stdout=log, stderr=log,
                                   close_fds=True, pass_fds=(lock_descriptor,),
                                   start_new_session=True, env=environment)
    return process.pid


def start_job(config, digit, token, key, spawn=spawn_worker):
    identifier = hmac.new(key, token.encode('ascii'), hashlib.sha256).hexdigest()[:32]
    try:
        previous = read_job(config, identifier)
    except ApiError as error:
        if error.status != 404:
            raise
    else:
        if previous['digit'] != digit:
            raise ApiError(409, 'This request token already belongs to another digit.')
        return 200, {'job': public_job(config, previous)}
    descriptor = lock_state(config)
    if descriptor is None:
        # Another copy of the same POST may have created its job meanwhile.
        try:
            previous = read_job(config, identifier)
        except ApiError as error:
            if error.status != 404:
                raise
        else:
            if previous['digit'] == digit:
                return 200, {'job': public_job(config, previous)}
        raise ApiError(409, 'A deployment or gateway installation is already running.',
                       active_job(config))
    try:
        # Recheck after taking the lock: a duplicate request could have finished.
        if os.path.exists(job_path(config, identifier, '.json')):
            previous = read_job(config, identifier)
            if previous['digit'] != digit:
                raise ApiError(409, 'This request token already belongs to another digit.')
            return 200, {'job': public_job(config, previous, reconcile=False)}
        script = os.path.join(config['gateway_dir'], 'tools', 'deploy-trial-digit.sh')
        if not os.path.isfile(script) or not os.access(script, os.R_OK):
            raise ApiError(503, 'The DLD gateway is not installed or readable.')
        metadata = {'id': identifier, 'digit': digit, 'state': 'running',
                    'exit_code': None, 'started_at': time.time()}
        with open(job_path(config, identifier, '.log'), 'w') as log:
            log.write('Starting DLD trial deployment to ' + digit.upper() + '\n')
        atomic_json(job_path(config, identifier, '.json'), metadata)
        atomic_json(os.path.join(config['state_dir'], 'active.json'), {'id': identifier})
        try:
            spawn(config, identifier, descriptor)
        except Exception as error:
            metadata['state'], metadata['exit_code'] = 'failed', 125
            with open(job_path(config, identifier, '.log'), 'a') as log:
                log.write('Cannot start deployment worker: ' + str(error) + '\n')
            atomic_json(job_path(config, identifier, '.json'), metadata)
            raise ApiError(500, 'Could not start the deployment worker.')
        return 202, {'job': public_job(config, metadata, reconcile=False)}
    finally:
        # Worker inherited this open file description; closing the CGI's copy
        # does not release its flock. Never explicitly LOCK_UN here.
        os.close(descriptor)


def request(environ, body, config, spawn=spawn_worker):
    method = environ.get('REQUEST_METHOD', 'GET')
    headers = []
    query = parse_qs(environ.get('QUERY_STRING', ''), keep_blank_values=True)
    if method == 'GET':
        action = query.get('action', [''])[0]
        if action == 'session' and set(query) == set(['action']) and len(query['action']) == 1:
            session = cookie_session(environ)
            if session is None:
                session = random_hex(32)
                cookie = (COOKIE_NAME + '=' + session +
                          '; Path=/cgi-bin/; HttpOnly; SameSite=Strict')
                if environ.get('HTTPS', '').lower() in ('on', '1'):
                    cookie += '; Secure'
                headers.append(('Set-Cookie', cookie))
            nonce = random_hex(32)
            token = nonce + '.' + sign_token(secret(config), session, nonce)
            return 200, {'token': token, 'active_job': active_job(config)}, headers
        if (action == 'status' and set(query) == set(['action', 'job']) and
                len(query['action']) == 1 and len(query['job']) == 1):
            return 200, {'job': public_job(config, read_job(config, query['job'][0]))}, headers
        raise ApiError(400, 'Use action=session or action=status with a job ID.')
    if method != 'POST':
        raise ApiError(405, 'Only GET and POST are supported.')
    check_request_context(environ)
    if query:
        raise ApiError(400, 'Deployment POST requests do not accept query parameters.')
    if environ.get('CONTENT_TYPE', '').split(';', 1)[0].strip().lower() != 'application/json':
        raise ApiError(415, 'Send application/json.')
    if len(body) > MAX_BODY:
        raise ApiError(413, 'Request is too large.')
    try:
        payload = json.loads(body.decode('utf-8'))
    except (ValueError, UnicodeError):
        raise ApiError(400, 'Invalid JSON.')
    if not isinstance(payload, dict) or set(payload) != set(['digit', 'token']):
        raise ApiError(400, 'Expected exactly digit and token.')
    digit = payload['digit']
    if not isinstance(digit, str) or not DIGIT.match(digit.lower()):
        raise ApiError(400, 'Digit must be H01-H12 or M00-M59.')
    key = secret(config)
    if not valid_token(key, cookie_session(environ), payload['token']):
        raise ApiError(403, 'Invalid session token. Reload the deploy page and try again.')
    status, result = start_job(config, digit.lower(), payload['token'], key, spawn)
    return status, result, headers


def worker(gateway_dir, state_dir, identifier, lock_descriptor):
    config = {'gateway_dir': gateway_dir, 'state_dir': state_dir}
    metadata = read_job(config, identifier)
    script = os.path.join(gateway_dir, 'tools', 'deploy-trial-digit.sh')
    code = 125
    try:
        environment = os.environ.copy()
        environment['PYTHONUNBUFFERED'] = '1'
        with open(os.devnull, 'rb') as null:
            process = subprocess.Popen(['/bin/sh', script, metadata['digit']],
                                       stdin=null, stdout=sys.stdout, stderr=sys.stderr,
                                       env=environment, close_fds=True,
                                       pass_fds=(lock_descriptor,))
            code = process.wait()
    except Exception as error:
        print('Deployment worker failed: ' + str(error))
    print('\nDeployment finished with exit code {0}.'.format(code))
    sys.stdout.flush()
    metadata.update(state='succeeded' if code == 0 else 'failed', exit_code=code,
                    finished_at=time.time())
    atomic_json(job_path(config, identifier, '.json'), metadata)
    os.close(lock_descriptor)
    return 0


def main():
    os.umask(0o077)
    if (not os.environ.get('REQUEST_METHOD') and len(sys.argv) == 6 and
            sys.argv[1] == '--worker'):
        return worker(sys.argv[2], sys.argv[3], sys.argv[4], int(sys.argv[5]))
    try:
        config = load_config()
        try:
            length = int(os.environ.get('CONTENT_LENGTH', '0'))
        except ValueError:
            raise ApiError(400, 'Invalid content length.')
        if length < 0 or length > MAX_BODY:
            raise ApiError(413, 'Request is too large.')
        body = sys.stdin.buffer.read(length)
        if len(body) != length:
            raise ApiError(400, 'Incomplete request body.')
        status, payload, headers = request(os.environ, body, config)
    except ApiError as error:
        status, payload, headers = error.status, error.payload, []
    except Exception as error:
        print('dld-trial.cgi: ' + str(error), file=sys.stderr)
        status, payload, headers = 503, {'error': 'DLD trial deployment is unavailable. Check the gateway installation and Apache error log.'}, []
    reasons = {200: 'OK', 202: 'Accepted', 400: 'Bad Request', 403: 'Forbidden',
               404: 'Not Found', 405: 'Method Not Allowed', 409: 'Conflict',
               413: 'Content Too Large', 415: 'Unsupported Media Type',
               500: 'Internal Server Error', 503: 'Service Unavailable'}
    print('Status: {0} {1}'.format(status, reasons[status]))
    print('Content-Type: application/json; charset=utf-8')
    print('Cache-Control: no-store')
    print('X-Content-Type-Options: nosniff')
    print('X-Frame-Options: DENY')
    for name, value in headers:
        print(name + ': ' + value)
    print('')
    print(json.dumps(payload))
    return 0


if __name__ == '__main__':
    sys.exit(main())
