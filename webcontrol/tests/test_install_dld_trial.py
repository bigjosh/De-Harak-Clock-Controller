#!/usr/bin/env python3
"""Exercise installer staging in private directories; never install or contact a digit."""
from __future__ import print_function

import errno
import io
import json
import os
import shutil
import sys
import tempfile
import types
import unittest
from contextlib import redirect_stdout
from unittest import mock


HERE = os.path.dirname(os.path.abspath(__file__))
INSTALLER = os.path.join(HERE, '..', 'install-dld-trial.sh')
FILES = ('tools/deploy-trial-digit.sh', 'tools/deploy-trial.sh',
         'tools/trial-remote.py', 'build/dld-trial.tar.gz')


class InstallerTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.mkdtemp(prefix='clock-installer-test-')
        self.source = os.path.join(self.temp, 'source with spaces')
        self.base = os.path.join(self.temp, 'opt')
        self.config_dir = os.path.join(self.temp, 'etc')
        self.state_parent = os.path.join(self.temp, 'var')
        self.config = os.path.join(self.config_dir, 'dld-trial.json')
        self.busy = False
        self.lock_fd = None
        self.modes = {}
        self.web_installs = []
        self.web_failure = False
        for name in FILES:
            path = os.path.join(self.source, name)
            if not os.path.isdir(os.path.dirname(path)):
                os.makedirs(os.path.dirname(path))
            with open(path, 'wb') as stream:
                stream.write(('fixture ' + name + '\n').encode('ascii'))
        with open(INSTALLER, 'r') as stream:
            text = stream.read()
        self.code = text.split("<<'PY'\n", 1)[1].split('\nPY\n', 1)[0]
        for old, new in (('/opt/clock-controller', self.base),
                         ('/etc/clock-controller', self.config_dir),
                         ('/var/lib/clock-controller', self.state_parent)):
            self.code = self.code.replace(repr(old), repr(new))

    def tearDown(self):
        target = os.path.realpath(self.temp)
        temporary_root = os.path.realpath(tempfile.gettempdir())
        self.assertEqual(os.path.normcase(os.path.dirname(target)),
                         os.path.normcase(temporary_root))
        self.assertTrue(os.path.basename(target).startswith('clock-installer-test-'))
        self.assertFalse(os.path.islink(self.temp))
        shutil.rmtree(target)

    def old_config(self):
        os.makedirs(self.config_dir)
        with open(self.config, 'w') as stream:
            stream.write('{"gateway_dir":"old-gateway"}\n')
        with open(self.config, 'rb') as stream:
            return stream.read()

    def run_installer(self):
        previous_config = None
        if os.path.exists(self.config):
            with open(self.config, 'rb') as stream:
                previous_config = stream.read()
        fake_fcntl = types.ModuleType('fcntl')
        fake_fcntl.LOCK_EX = 2
        fake_fcntl.LOCK_NB = 4

        def flock(descriptor, operation):
            if self.busy:
                raise IOError(errno.EAGAIN, 'fixture active deployment')
            self.lock_fd = descriptor

        fake_fcntl.flock = flock
        fake_pwd = types.ModuleType('pwd')
        fake_pwd.getpwnam = lambda name: types.SimpleNamespace(pw_uid=112, pw_gid=118)

        def web_install(command, **kwargs):
            # A still-open lock descriptor proves install/reload is in the
            # staging critical section, rather than after the Python exits.
            self.assertIsNotNone(self.lock_fd)
            os.fstat(self.lock_fd)
            # Publish the new gateway only after the web files install.
            if previous_config is None:
                self.assertFalse(os.path.exists(self.config))
            else:
                with open(self.config, 'rb') as stream:
                    self.assertEqual(stream.read(), previous_config)
            self.web_installs.append(command)
            if self.web_failure:
                raise IOError('fixture web installation failure')
            return 0

        def chmod(path, mode):
            self.modes[os.path.abspath(path)] = mode

        with mock.patch.dict(sys.modules, {'fcntl': fake_fcntl, 'pwd': fake_pwd}), \
                mock.patch.object(sys, 'argv', [INSTALLER, self.source, os.path.join(HERE, '..')]), \
                mock.patch.object(os, 'chown', create=True), \
                mock.patch.object(os, 'fchown', create=True), \
                mock.patch.object(os, 'fchmod', create=True), \
                mock.patch.object(os, 'chmod', side_effect=chmod), \
                mock.patch.object(os, 'rename', side_effect=os.replace), \
                mock.patch.object(os, 'O_NOFOLLOW', getattr(os, 'O_NOFOLLOW', 0), create=True), \
                mock.patch('subprocess.check_call', side_effect=web_install), \
                redirect_stdout(io.StringIO()):
            exec(compile(self.code, INSTALLER, 'exec'), {'__name__': '__main__'})

    def test_stages_complete_gateway_and_publishes_readable_config(self):
        self.run_installer()
        self.assertEqual(len(self.web_installs), 1)
        with open(self.config, 'r') as stream:
            config = json.load(stream)
        self.assertEqual(config['state_dir'], os.path.join(self.state_parent, 'dld-trial'))
        self.assertEqual(os.path.dirname(config['gateway_dir']), self.base)
        self.assertEqual(self.modes[config['gateway_dir']], 0o755)
        self.assertEqual(self.modes[config['state_dir']], 0o700)
        for name in FILES:
            installed = os.path.join(config['gateway_dir'], name)
            with open(installed, 'rb') as stream:
                actual = stream.read()
            with open(os.path.join(self.source, name), 'rb') as stream:
                self.assertEqual(actual, stream.read())
            self.assertEqual(self.modes[os.path.abspath(installed)], 0o755 if name.endswith('.sh') else 0o644)
            self.assertEqual(self.modes[os.path.abspath(os.path.dirname(installed))], 0o755)

    def test_missing_gateway_file_leaves_old_config_and_gateway_alone(self):
        previous = self.old_config()
        os.unlink(os.path.join(self.source, FILES[-1]))
        with self.assertRaises(SystemExit):
            self.run_installer()
        with open(self.config, 'rb') as stream:
            self.assertEqual(stream.read(), previous)
        self.assertFalse(os.path.exists(self.base))

    def test_active_job_refuses_update_without_replacing_config(self):
        previous = self.old_config()
        self.busy = True
        with self.assertRaises(SystemExit) as error:
            self.run_installer()
        self.assertIn('active', str(error.exception))
        with open(self.config, 'rb') as stream:
            self.assertEqual(stream.read(), previous)
        self.assertEqual(os.listdir(self.base), [])
        self.assertEqual(self.web_installs, [])

    def test_failed_web_install_does_not_switch_existing_gateway(self):
        previous = self.old_config()
        self.web_failure = True
        with self.assertRaises(IOError):
            self.run_installer()
        with open(self.config, 'rb') as stream:
            self.assertEqual(stream.read(), previous)
        self.assertEqual(len(self.web_installs), 1)

    def test_update_replaces_config_after_web_installation(self):
        self.old_config()
        self.run_installer()
        with open(self.config, 'r') as stream:
            self.assertEqual(os.path.dirname(json.load(stream)['gateway_dir']), self.base)
        self.assertEqual(len(self.web_installs), 1)

    def test_copy_failure_never_switches_existing_config(self):
        previous = self.old_config()
        copyfile = shutil.copyfile
        count = [0]

        def fail_second_copy(source, destination):
            count[0] += 1
            if count[0] == 2:
                raise IOError('fixture disk failure')
            return copyfile(source, destination)

        with mock.patch('shutil.copyfile', side_effect=fail_second_copy):
            with self.assertRaises(IOError):
                self.run_installer()
        with open(self.config, 'rb') as stream:
            self.assertEqual(stream.read(), previous)
        self.assertEqual(self.web_installs, [])


if __name__ == '__main__':
    unittest.main()
