"""Controller installers must accept old OpenSSH scp without a -O option.

Run actual shell preflights with harmless fixture tools. Downloads, Python
staging, Apache changes and child installation never execute for real.
"""
from __future__ import print_function

import os
import shutil
import subprocess
import tempfile
import unittest


HERE = os.path.dirname(os.path.abspath(__file__))
SHELL = (os.path.join(os.environ.get('ProgramFiles', 'C:\\Program Files'),
                      'Git', 'usr', 'bin', 'sh.exe') if os.name == 'nt' else '/bin/sh')


def shell_path(path):
    path = os.path.abspath(path).replace('\\', '/')
    return '/' + path[0].lower() + path[2:] if os.name == 'nt' else path


def quote(value):
    return "'" + value.replace("'", "'\\''") + "'"


@unittest.skipUnless(os.path.isfile(SHELL), 'POSIX shell or Windows Git sh required')
class LegacyScpInstallerTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.mkdtemp(prefix='clock-legacy-scp-test-')
        self.addCleanup(self.cleanup)
        self.bin = os.path.join(self.temp, 'bin')
        self.log = os.path.join(self.temp, 'commands.log')
        self.gateway = os.path.join(self.temp, 'gateway')
        os.mkdir(self.bin)
        os.mkdir(self.gateway)
        self.prefix = '#!/bin/sh\nset -eu\n'
        self.record = 'printf "%s\\n" "$(basename -- "$0") $*" >> ' + quote(shell_path(self.log)) + '\n'
        self.tool('id', 'printf "0\\n"\n')
        self.tool('ssh', self.record + 'exit 0\n')
        self.tool('scp', self.record +
                  'for arg do\n'
                  '  if [ "$arg" = -O ]; then echo "scp: unknown option -- O" >&2; exit 1; fi\n'
                  'done\nexit 0\n')
        self.tool('curl', self.record +
                  'output=\n'
                  'while [ "$#" -gt 0 ]; do\n'
                  '  if [ "$1" = --output ]; then shift; output=$1; fi\n'
                  '  shift\n'
                  'done\n'
                  '[ -n "$output" ]\n'
                  'printf "fixture archive\\n" > "$output"\n')
        self.tool('python3', self.record +
                  'cat >/dev/null\n'
                  'if [ "$#" -eq 2 ]; then\n'
                  '  mkdir -p "$2/controller/webcontrol" "$2/gateway"\n'
                  '  printf "fixture child installer\\n" > "$2/controller/webcontrol/install-dld-trial.sh"\n'
                  'fi\n'
                  'echo "Fixture Python staging reached"\n')
        self.tool('apache2ctl', self.record +
                  'case "$1" in -M) echo " cgi_module (shared)" ;; configtest) exit 0 ;; *) exit 99 ;; esac\n')
        self.tool('sh', self.record + '[ -f "$1" ]\necho "Fixture child installer reached"\n')
        for name in ('apt-get', 'a2enmod', 'systemctl', 'sudo'):
            self.tool(name, self.record + 'echo "Unexpected fixture action" >&2\nexit 99\n')

    def cleanup(self):
        target = os.path.realpath(self.temp)
        root = os.path.realpath(tempfile.gettempdir())
        self.assertEqual(os.path.normcase(os.path.dirname(target)), os.path.normcase(root))
        self.assertTrue(os.path.basename(target).startswith('clock-legacy-scp-test-'))
        self.assertFalse(os.path.islink(self.temp))
        shutil.rmtree(target)

    def tool(self, name, body):
        path = os.path.join(self.bin, name)
        with open(path, 'wb') as stream:
            stream.write((self.prefix + body).encode('utf-8'))
        os.chmod(path, 0o755)

    def run_script(self, name, arguments):
        with open(os.path.join(HERE, '..', name), 'r') as stream:
            script = stream.read()
        # No system temporary directory or installed path can be used even if
        # a fixture changes later. The embedded Python is consumed, not run.
        script = script.replace('/tmp/clock-deploy-install.XXXXXX',
                                quote(shell_path(os.path.join(self.temp, 'stage.XXXXXX'))))
        for original, replacement in (('/opt/clock-controller', 'private-opt'),
                                      ('/etc/clock-controller', 'private-etc'),
                                      ('/var/lib/clock-controller', 'private-var')):
            script = script.replace(original, shell_path(os.path.join(self.temp, replacement)))
        path = os.path.join(self.temp, name)
        with open(path, 'wb') as stream:
            stream.write(script.encode('utf-8'))
        # Explicit shell path ensures the fake child 'sh' cannot replace the
        # entry point; PATH stubs apply only to commands inside the installer.
        command = ('PATH=' + quote(shell_path(self.bin)) + ':' +
                   quote(shell_path(os.path.dirname(SHELL))) + ':"$PATH"; export PATH; exec ' +
                   quote(shell_path(SHELL)) + ' ' + quote(shell_path(path)))
        command += ''.join(' ' + quote(value) for value in arguments)
        process = subprocess.Popen([SHELL, '-c', command], cwd=self.temp,
                                   stdout=subprocess.PIPE, stderr=subprocess.PIPE)
        output, errors = process.communicate()
        log = ''
        if os.path.exists(self.log):
            with open(self.log, 'r') as stream:
                log = stream.read()
        return process.returncode, output, errors, log

    def assert_no_scp_probe_or_live_actions(self, log):
        self.assertFalse(any(line.startswith('scp ') for line in log.splitlines()), log)
        for name in ('ssh ', 'apt-get ', 'sudo ', 'systemctl ', 'a2enmod '):
            self.assertFalse(any(line.startswith(name) for line in log.splitlines()), log)

    def test_gateway_installer_accepts_old_scp(self):
        status, output, errors, log = self.run_script('install-dld-trial.sh', [shell_path(self.gateway)])
        self.assertEqual(status, 0, errors)
        self.assertIn(b'Fixture Python staging reached', output)
        self.assertIn('python3 - ' + shell_path(self.gateway), log)
        self.assert_no_scp_probe_or_live_actions(log)

    def test_github_installer_accepts_old_scp_and_reaches_child_install(self):
        status, output, errors, log = self.run_script('install-from-github.sh', ['fixture-branch'])
        self.assertEqual(status, 0, errors)
        self.assertIn(b'Fixture child installer reached', output)
        self.assertIn('https://codeload.github.com/bigjosh/De-Harak-Clock-Controller/tar.gz/fixture-branch', log)
        self.assertIn('apache2ctl configtest', log)
        self.assertIn('/controller/webcontrol/install-dld-trial.sh ', log)
        self.assert_no_scp_probe_or_live_actions(log)


if __name__ == '__main__':
    unittest.main()
