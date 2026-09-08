#!/usr/bin/env python3
"""Validate GitHub installer archives in private fixtures; Python 3.4+."""
from __future__ import print_function

import hashlib
import io
import json
import os
import shutil
import tarfile
import tempfile
import unittest
from contextlib import redirect_stdout


HERE = os.path.dirname(os.path.abspath(__file__))
WEB_ROOT = os.path.abspath(os.path.join(HERE, '..'))
ROOT = os.path.dirname(WEB_ROOT)
INSTALLER = os.path.join(WEB_ROOT, 'install-from-github.sh')


def digest(data):
    return hashlib.sha256(data).hexdigest()


def encode_json(value):
    return (json.dumps(value, sort_keys=True) + '\n').encode('utf-8')


def pack(files, extras=()):
    output = io.BytesIO()
    with tarfile.open(fileobj=output, mode='w:gz') as archive:
        for name, data in sorted(files.items()):
            member = tarfile.TarInfo(name)
            member.size = len(data)
            archive.addfile(member, io.BytesIO(data))
        for member, data in extras:
            archive.addfile(member, io.BytesIO(data) if data is not None else None)
    return output.getvalue()


def unpack(data):
    with tarfile.open(fileobj=io.BytesIO(data), mode='r:gz') as archive:
        return dict((member.name, archive.extractfile(member).read()) for member in archive)


def extra_file(name, data=b'fixture\n', kind=None):
    member = tarfile.TarInfo(name)
    if kind is None:
        member.size = len(data)
    else:
        member.type = kind
        member.linkname = '/etc/passwd'
        data = None
    return member, data


class GithubInstallerTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        with open(INSTALLER, 'r') as stream:
            shell = stream.read()
        source = shell.split("<<'PY'\n", 1)[1].split('\nPY\n', 1)[0]
        cls.api = {'__name__': 'github_installer_test', '__file__': INSTALLER}
        exec(compile(source, INSTALLER, 'exec'), cls.api)
        cls.original_web = {}
        for name in cls.api['WEB_FILES']:
            with open(os.path.join(ROOT, name), 'rb') as stream:
                cls.original_web[name] = stream.read()
        cls.original_runtime = unpack(cls.original_web['webcontrol/dld-runtime.tar.gz'])
        cls.original_native = unpack(cls.original_runtime['build/dld-trial.tar.gz'])

    def setUp(self):
        self.stage = tempfile.mkdtemp(prefix='clock-github-installer-test-')
        self.web = dict(self.original_web)
        self.runtime = dict(self.original_runtime)
        self.native = dict(self.original_native)

    def tearDown(self):
        target = os.path.realpath(self.stage)
        temporary_root = os.path.realpath(tempfile.gettempdir())
        self.assertEqual(os.path.normcase(os.path.dirname(target)),
                         os.path.normcase(temporary_root))
        self.assertTrue(os.path.basename(target).startswith('clock-github-installer-test-'))
        self.assertFalse(os.path.islink(self.stage))
        shutil.rmtree(target)

    def runtime_archive(self, extras=(), refresh_hashes=False):
        if refresh_hashes:
            metadata = json.loads(self.runtime['runtime.json'].decode('utf-8'))
            hashes = dict((name, digest(data)) for name, data in self.runtime.items()
                          if name != 'runtime.json')
            metadata['files'] = hashes
            metadata['source_files_sha256'] = hashes
            metadata['native_bundle_sha256'] = digest(self.runtime['build/dld-trial.tar.gz'])
            self.runtime['runtime.json'] = encode_json(metadata)
        packed = pack(self.runtime, extras)
        self.web['webcontrol/dld-runtime.tar.gz'] = packed
        self.web['webcontrol/dld-runtime.sha256'] = (
            digest(packed) + '  dld-runtime.tar.gz\n').encode('ascii')

    def native_archive(self, extras=()):
        self.runtime['build/dld-trial.tar.gz'] = pack(self.native, extras)
        self.runtime_archive(refresh_hashes=True)

    def prepare(self, extras=()):
        files = dict(('snapshot/' + name, data) for name, data in self.web.items())
        with open(os.path.join(self.stage, 'controller.tar.gz'), 'wb') as stream:
            stream.write(pack(files, extras))
        with redirect_stdout(io.StringIO()):
            self.api['prepare'](self.stage)

    def rejected(self, extras=(), message=None):
        with self.assertRaises(ValueError) as error:
            self.prepare(extras)
        if message is not None:
            self.assertIn(message, str(error.exception))
        self.assertFalse(os.path.exists(os.path.join(self.stage, 'controller')))
        self.assertFalse(os.path.exists(os.path.join(self.stage, 'gateway')))

    def test_real_pack_validates_and_extracts_only_selected_files(self):
        self.prepare()
        for name, expected in self.original_web.items():
            with open(os.path.join(self.stage, 'controller', name), 'rb') as stream:
                self.assertEqual(stream.read(), expected)
        for name, expected in self.original_runtime.items():
            with open(os.path.join(self.stage, 'gateway', name), 'rb') as stream:
                self.assertEqual(stream.read(), expected)
        self.assertEqual(sorted(os.listdir(self.stage)), ['controller', 'controller.tar.gz', 'gateway'])

    def test_unrelated_controller_files_and_traversal_are_never_extracted(self):
        extras = [extra_file('snapshot/leds.c'),
                  extra_file('snapshot/../../outside'),
                  extra_file('snapshot/ignored-link', kind=tarfile.SYMTYPE)]
        self.prepare(extras)
        extracted = []
        controller = os.path.join(self.stage, 'controller')
        for directory, unused, names in os.walk(controller):
            extracted.extend(os.path.relpath(os.path.join(directory, name), controller).replace('\\', '/')
                             for name in names)
        self.assertEqual(set(extracted), set(self.api['WEB_FILES']))
        self.assertFalse(os.path.exists(os.path.join(self.stage, 'outside')))

    def test_missing_web_file_rejected_before_any_extraction(self):
        del self.web['webcontrol/var_www/deploy.html']
        self.rejected(message='Missing required files')

    def test_duplicate_web_file_rejected(self):
        self.rejected([extra_file('snapshot/webcontrol/var_www/deploy.html')], 'unique regular file')

    def test_required_web_symlink_rejected(self):
        del self.web['webcontrol/var_www/deploy.html']
        self.rejected([extra_file('snapshot/webcontrol/var_www/deploy.html', kind=tarfile.SYMTYPE)],
                      'unique regular file')

    def test_multiple_github_roots_rejected(self):
        self.rejected([extra_file('second-snapshot/unrelated')], 'one controller snapshot')

    def test_runtime_sidecar_hash_failure_rejected(self):
        self.web['webcontrol/dld-runtime.sha256'] = b'0' * 64 + b'  dld-runtime.tar.gz\n'
        self.rejected(message='runtime package checksum mismatch')

    def test_missing_runtime_member_rejected(self):
        del self.runtime['tools/deploy-trial-digit.sh']
        self.runtime_archive()
        self.rejected(message='Missing required files')

    def test_duplicate_runtime_member_rejected(self):
        self.runtime_archive([extra_file('tools/deploy-trial-digit.sh')])
        self.rejected(message='unique regular file')

    def test_runtime_traversal_rejected(self):
        self.runtime_archive([extra_file('../escape')])
        self.rejected(message='Unexpected runtime archive member')

    def test_runtime_symlink_rejected(self):
        del self.runtime['tools/deploy-trial-digit.sh']
        self.runtime_archive([extra_file('tools/deploy-trial-digit.sh', kind=tarfile.SYMTYPE)])
        self.rejected(message='unique regular file')

    def test_runtime_file_hash_failure_rejected(self):
        self.runtime['tools/deploy-trial.sh'] += b'# changed\n'
        self.runtime_archive()
        self.rejected(message='Checksum mismatch')

    def test_native_bootstrap_mismatch_rejected(self):
        self.runtime['tools/trial-remote.py'] += b'# changed\n'
        self.runtime_archive(refresh_hashes=True)
        self.rejected(message='bootstrap differs')

    def test_native_file_hash_failure_rejected(self):
        self.native['build/dld-init'] += b'changed'
        self.native_archive()
        self.rejected(message='Checksum mismatch')

    def test_wrong_native_kernel_rejected(self):
        manifest = json.loads(self.native['manifest.json'].decode('utf-8'))
        manifest['kernel_release'] = 'wrong-kernel'
        self.native['manifest.json'] = encode_json(manifest)
        self.native_archive()
        self.rejected(message='Unsupported native')

    def test_duplicate_native_member_rejected(self):
        self.native_archive([extra_file('build/dld-init')])
        self.rejected(message='unique regular file')

    def test_native_traversal_rejected(self):
        self.native_archive([extra_file('../escape')])
        self.rejected(message='Unexpected runtime archive member')

    def test_runtime_metadata_wrong_type_rejected_cleanly(self):
        for value in ([], None, 'metadata', 1, True):
            with self.subTest(value=value):
                self.runtime['runtime.json'] = encode_json(value)
                self.runtime_archive()
                self.rejected(message='metadata')

    def test_native_manifest_wrong_type_rejected_cleanly(self):
        for value in ([], None, 'manifest', 1, True):
            with self.subTest(value=value):
                self.native['manifest.json'] = encode_json(value)
                self.native_archive()
                self.rejected(message='native')

    def test_runtime_schema_requires_integer_one(self):
        for value in (True, 1.0, '1', None):
            with self.subTest(value=value):
                metadata = json.loads(self.original_runtime['runtime.json'].decode('utf-8'))
                metadata['schema'] = value
                self.runtime['runtime.json'] = encode_json(metadata)
                self.runtime_archive()
                self.rejected(message='metadata')

    def test_native_schema_requires_integer_one(self):
        for value in (True, 1.0, '1', None):
            with self.subTest(value=value):
                manifest = json.loads(self.original_native['manifest.json'].decode('utf-8'))
                manifest['schema'] = value
                self.native['manifest.json'] = encode_json(manifest)
                self.native_archive()
                self.rejected(message='native')

    def test_linux_script_line_endings_required(self):
        self.runtime['tools/deploy-trial.sh'] += b'# bad line ending\r\n'
        self.runtime_archive(refresh_hashes=True)
        self.rejected(message='Linux line endings')

    def test_empty_selected_file_rejected(self):
        self.web['webcontrol/var_www/deploy.html'] = b''
        self.rejected(message='empty')

    def test_oversized_selected_payload_rejected(self):
        self.web['webcontrol/var_www/deploy.html'] = b'x' * (16 * 1024 * 1024 + 1)
        self.rejected(message='16 MiB')


if __name__ == '__main__':
    unittest.main()
