"""Run the web shell installer against private fixture directories only.

The two production destinations are rewritten before execution; id, sudo and
systemctl are harmless local fixtures. No live installation is performed.
"""
from __future__ import print_function

import os
import shutil
import stat
import subprocess
import tempfile
import unittest


HERE = os.path.dirname(os.path.abspath(__file__))
INSTALLER = os.path.abspath(os.path.join(HERE, '..', 'install.sh'))
SHELL = (os.path.join(os.environ.get('ProgramFiles', 'C:\\Program Files'),
                      'Git', 'bin', 'sh.exe') if os.name == 'nt' else '/bin/sh')


def shell_path(path):
    path = os.path.abspath(path).replace('\\', '/')
    if os.name == 'nt':
        return '/' + path[0].lower() + path[2:]
    return path


def quoted(value):
    return "'" + value.replace("'", "'\\''") + "'"


@unittest.skipUnless(os.path.isfile(SHELL), 'A POSIX shell (Git sh on Windows) is required')
class WebInstallerTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.mkdtemp(prefix='clock-web-install-test-')
        self.addCleanup(self.cleanup)
        self.source = os.path.join(self.temp, 'source with spaces')
        self.live = os.path.join(self.temp, 'private live tree')
        self.web = os.path.join(self.live, 'html')
        self.cgi = os.path.join(self.live, 'cgi-bin')
        self.bin = os.path.join(self.temp, 'fixture-bin')
        self.reload_log = os.path.join(self.temp, 'reload.log')
        self.script = os.path.join(self.source, 'install.sh')
        self.sources = {
            'var_www/deploy.html': b'new deployment page\n',
            'var_www/css/deploy.css': b'new deployment styles\n',
            'var_www/js/deploy.js': b'new deployment javascript\n',
            'var_www/css/bootstrap.min.css': b'bundled bootstrap\n',
            'var_www/control.html': b'repository control page\n',
            'var_www/index.html': b'repository index page\n',
            'var_www/js/jquery.min.js': b'repository jquery\n',
            'usr_lib_cgi-bin/dld-trial.cgi': b'#!/bin/sh\necho deployment CGI\n',
            'usr_lib_cgi-bin/light.cgi': b'#!/bin/sh\necho repository light CGI\n',
            'usr_lib_cgi-bin/checkdigitsHTML.sh': b'#!/bin/sh\necho repository check\n',
        }
        for name, content in self.sources.items():
            self.write(os.path.join(self.source, *name.split('/')), content)
        with open(INSTALLER, 'r') as stream:
            script = stream.read()
        # Rewrite ALL fixed destination occurrences, including those with a
        # suffix, to quoted paths inside this test's private temporary tree.
        for original, destination in (('/var/www/html', self.web),
                                      ('/usr/lib/cgi-bin', self.cgi)):
            self.assertIn(original, script)
            script = script.replace(original, quoted(shell_path(destination)))
            self.assertNotIn(original, script)
        self.write(self.script, script.encode('utf-8'))
        self.write(os.path.join(self.bin, 'id'), b'#!/bin/sh\nprintf "0\\n"\n', 0o755)
        self.write(os.path.join(self.bin, 'sudo'),
                   b'#!/bin/sh\necho "Unexpected sudo fixture call" >&2\nexit 99\n', 0o755)
        systemctl = ('#!/bin/sh\nprintf "%s\\n" "$*" >> ' +
                     quoted(shell_path(self.reload_log)) + '\n')
        self.write(os.path.join(self.bin, 'systemctl'), systemctl.encode('utf-8'), 0o755)

    def cleanup(self):
        target = os.path.realpath(self.temp)
        temporary_root = os.path.realpath(tempfile.gettempdir())
        self.assertEqual(os.path.normcase(os.path.dirname(target)),
                         os.path.normcase(temporary_root))
        self.assertTrue(os.path.basename(target).startswith('clock-web-install-test-'))
        self.assertFalse(os.path.islink(self.temp))
        shutil.rmtree(target)

    def write(self, path, value, mode=0o644):
        parent = os.path.dirname(path)
        if not os.path.isdir(parent):
            os.makedirs(parent)
        with open(path, 'wb') as stream:
            stream.write(value)
        os.chmod(path, mode)

    def read(self, path):
        with open(path, 'rb') as stream:
            return stream.read()

    def run_installer(self, arguments):
        # Set PATH inside the shell explicitly. This works with both Windows
        # native Python/Git sh and a native POSIX Python without PATH conversion
        # ambiguity, and keeps every privileged command stubbed out.
        command = 'PATH=' + quoted(shell_path(self.bin)) + ':"$PATH"; export PATH; exec sh ' + quoted(shell_path(self.script))
        command += ''.join(' ' + quoted(value) for value in arguments)
        process = subprocess.Popen([SHELL, '-c', command], cwd=self.temp,
                                   stdout=subprocess.PIPE, stderr=subprocess.PIPE)
        output, errors = process.communicate()
        return process.returncode, output, errors

    def existing_files(self):
        existing = {
            os.path.join(self.web, 'control.html'): b'custom running control page\n',
            os.path.join(self.web, 'index.html'): b'custom running index page\n',
            os.path.join(self.web, 'css', 'bootstrap.min.css'): b'custom running bootstrap\n',
            os.path.join(self.web, 'js', 'jquery.min.js'): b'custom running jquery\n',
            os.path.join(self.cgi, 'light.cgi'): b'custom running light CGI\n',
            os.path.join(self.cgi, 'checkdigitsHTML.sh'): b'custom running checks\n',
            os.path.join(self.web, 'unrelated.txt'): b'keep unrelated files\n',
        }
        for path, content in existing.items():
            self.write(path, content, 0o640)
        return existing

    def assert_new_files(self):
        for name in ('deploy.html', 'css/deploy.css', 'js/deploy.js'):
            path = os.path.join(self.web, *name.split('/'))
            self.assertEqual(self.read(path), self.sources['var_www/' + name])
            if os.name == 'posix':
                self.assertEqual(stat.S_IMODE(os.stat(path).st_mode), 0o644)
        path = os.path.join(self.cgi, 'dld-trial.cgi')
        self.assertEqual(self.read(path), self.sources['usr_lib_cgi-bin/dld-trial.cgi'])
        if os.name == 'posix':
            self.assertEqual(stat.S_IMODE(os.stat(path).st_mode), 0o755)
            for directory in (self.web, self.cgi, os.path.join(self.web, 'css'),
                              os.path.join(self.web, 'js')):
                self.assertEqual(stat.S_IMODE(os.stat(directory).st_mode), 0o755)
        self.assertEqual(self.read(self.reload_log), b'reload apache2\n')

    def test_dld_only_preserves_existing_pages_cgis_and_dependencies(self):
        existing = self.existing_files()
        status, output, errors = self.run_installer(['--dld-only'])
        self.assertEqual(status, 0, errors)
        self.assert_new_files()
        for path, content in existing.items():
            self.assertEqual(self.read(path), content)
            if os.name == 'posix':
                self.assertEqual(stat.S_IMODE(os.stat(path).st_mode), 0o640)

    def test_dld_only_first_install_adds_bootstrap_and_no_control_files(self):
        status, output, errors = self.run_installer(['--dld-only'])
        self.assertEqual(status, 0, errors)
        self.assert_new_files()
        bootstrap = os.path.join(self.web, 'css', 'bootstrap.min.css')
        self.assertEqual(self.read(bootstrap), self.sources['var_www/css/bootstrap.min.css'])
        if os.name == 'posix':
            self.assertEqual(stat.S_IMODE(os.stat(bootstrap).st_mode), 0o644)
        for path in (os.path.join(self.web, 'control.html'),
                     os.path.join(self.web, 'index.html'),
                     os.path.join(self.cgi, 'light.cgi'),
                     os.path.join(self.web, 'js', 'jquery.min.js')):
            self.assertFalse(os.path.exists(path), path)

    def test_full_install_still_copies_all_repository_web_and_cgi_files(self):
        self.existing_files()
        status, output, errors = self.run_installer([])
        self.assertEqual(status, 0, errors)
        for name, content in self.sources.items():
            prefix, remainder = name.split('/', 1)
            base = self.web if prefix == 'var_www' else self.cgi
            path = os.path.join(base, *remainder.split('/'))
            self.assertEqual(self.read(path), content)
            if os.name == 'posix' and prefix == 'usr_lib_cgi-bin':
                self.assertEqual(stat.S_IMODE(os.stat(path).st_mode), 0o755)
        self.assertEqual(self.read(os.path.join(self.web, 'unrelated.txt')), b'keep unrelated files\n')
        self.assertEqual(self.read(self.reload_log), b'reload apache2\n')

    def test_invalid_arguments_do_not_create_destinations_or_reload(self):
        for arguments in (['--bogus'], ['--dld-only', 'extra'], ['--dld-only extra']):
            status, output, errors = self.run_installer(arguments)
            self.assertEqual(status, 2, errors)
            self.assertIn(b'usage:', errors)
            self.assertFalse(os.path.exists(self.live))
            self.assertFalse(os.path.exists(self.reload_log))

    def test_invalid_arguments_preserve_existing_destination_contents(self):
        existing = self.existing_files()
        status, output, errors = self.run_installer(['--dld-only', '--dld-only'])
        self.assertEqual(status, 2, errors)
        for path, content in existing.items():
            self.assertEqual(self.read(path), content)
        self.assertFalse(os.path.exists(os.path.join(self.web, 'deploy.html')))
        self.assertFalse(os.path.exists(os.path.join(self.cgi, 'dld-trial.cgi')))
        self.assertFalse(os.path.exists(self.reload_log))


if __name__ == '__main__':
    unittest.main()
