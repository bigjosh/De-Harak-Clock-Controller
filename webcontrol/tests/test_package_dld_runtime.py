#!/usr/bin/env python3
"""Test runtime snapshot packaging without GitHub, a compiler, or any digit."""

import hashlib
import json
from pathlib import Path
import runpy
import shutil
import tempfile
import unittest
from unittest import mock
import tarfile


HERE = Path(__file__).resolve().parent
PACKAGER = runpy.run_path(str(HERE.parent / "package-dld-runtime.py"))
PACKAGE = PACKAGER["package"]
FILES = PACKAGER["RUNTIME_FILES"]
COMMIT = "a" * 40
VALIDATOR = '''import json
def check_bundle(data, bootstrap):
    bundle = json.loads(data.decode("utf-8"))
    if bundle["bootstrap"].encode("utf-8") != bootstrap:
        raise ValueError("native bundle and gateway bootstrap differ")
    return {"kernel_release": "3.8.13-bone80"}
'''


class RuntimePackageTests(unittest.TestCase):
    def setUp(self):
        self.temporary = Path(tempfile.mkdtemp(prefix="clock-runtime-test-"))
        self.source = self.temporary / "source"
        self.output = self.temporary / "output"
        self.write("tools/deploy-trial-digit.sh", b"#!/bin/sh\necho digit\n")
        self.write("tools/deploy-trial.sh", b"#!/bin/sh\necho deploy\n")
        self.bootstrap = b"#!/usr/bin/env python3\nprint('bootstrap')\n"
        self.write("tools/trial-remote.py", self.bootstrap)
        self.write("build/dld-trial.tar.gz", json.dumps({
            "bootstrap": self.bootstrap.decode("utf-8")}).encode("utf-8"))
        self.write("tools/package-gateway.py", VALIDATOR.encode("utf-8"))
        self.git = mock.patch.object(PACKAGER["subprocess"], "check_output",
                                     side_effect=self.git_output)
        self.git.start()
        self.addCleanup(self.git.stop)

    def tearDown(self):
        # Do not recursively delete an unexpected computed path on Windows.
        resolved = self.temporary.resolve()
        if (self.temporary.is_symlink() or resolved.parent != Path(tempfile.gettempdir()).resolve()
                or not resolved.name.startswith("clock-runtime-test-")):
            raise RuntimeError("unsafe test cleanup path: " + str(resolved))
        shutil.rmtree(str(resolved))

    def git_output(self, command, cwd):
        self.assertEqual(str(self.source), cwd)
        if command == ["git", "rev-parse", "HEAD"]:
            return (COMMIT + "\n").encode("ascii")
        self.assertEqual(["git", "status", "--porcelain", "--untracked-files=normal"], command)
        return b" M tools/deploy-trial.sh\n"

    def write(self, name, data):
        path = self.source / name
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_bytes(data)

    def contents(self, output):
        with tarfile.open(str(output), "r:gz") as archive:
            for member in archive:
                self.assertTrue(member.isfile())
                self.assertEqual(0, member.mtime)
                self.assertEqual(0, member.uid)
                self.assertEqual(0, member.gid)
                self.assertEqual(0o755 if member.name.endswith(".sh") else 0o644, member.mode)
            return {member.name: archive.extractfile(member).read() for member in archive}

    def test_reproducible_allowlisted_snapshot_and_honest_provenance(self):
        self.write("build/do-not-package.key", b"fixture secret must not be packaged")
        self.write("tools/unrelated.sh", b"echo unrelated")
        first, metadata = PACKAGE(self.source, self.output)
        packed = first.read_bytes()
        second, second_metadata = PACKAGE(self.source, self.temporary / "second")
        self.assertEqual(packed, second.read_bytes())
        self.assertEqual(metadata, second_metadata)
        files = self.contents(first)
        self.assertEqual(set(FILES) | {"runtime.json"}, set(files))
        self.assertEqual(COMMIT, metadata["upstream_base_commit"])
        self.assertIs(True, metadata["upstream_dirty"])
        self.assertEqual("armv7l", metadata["native_architecture"])
        self.assertEqual("3.8.13-bone80", metadata["native_kernel_release"])
        for name in FILES:
            self.assertEqual(hashlib.sha256(files[name]).hexdigest(), metadata["files"][name])
        self.assertEqual(hashlib.sha256(packed).hexdigest() + "  dld-runtime.tar.gz\n",
                         (self.output / "dld-runtime.sha256").read_text())

    def test_missing_digit_wrapper_fails_before_writing(self):
        (self.source / "tools/deploy-trial-digit.sh").unlink()
        with self.assertRaisesRegex(ValueError, "regular file.*deploy-trial-digit"):
            PACKAGE(self.source, self.output)
        self.assertFalse(self.output.exists())

    def test_corrupt_or_mismatched_native_bundle_cannot_replace_snapshot(self):
        output, unused = PACKAGE(self.source, self.output)
        previous = output.read_bytes()
        for invalid in (b"not a native bundle", b'{"bootstrap": "mismatch"}'):
            self.write("build/dld-trial.tar.gz", invalid)
            with self.assertRaises(ValueError):
                PACKAGE(self.source, self.output)
            self.assertEqual(previous, output.read_bytes())

    def test_crlf_normalization_must_match_native_bootstrap(self):
        self.write("tools/trial-remote.py", self.bootstrap.replace(b"\n", b"\r\n"))
        output, metadata = PACKAGE(self.source, self.output)
        self.assertEqual(self.bootstrap, self.contents(output)["tools/trial-remote.py"])
        self.assertNotEqual(metadata["source_files_sha256"]["tools/trial-remote.py"],
                            metadata["files"]["tools/trial-remote.py"])
        self.write("build/dld-trial.tar.gz", json.dumps({
            "bootstrap": self.bootstrap.replace(b"\n", b"\r\n").decode("utf-8")}).encode("utf-8"))
        with self.assertRaisesRegex(ValueError, "bootstrap differ"):
            PACKAGE(self.source, self.output)

    def test_license_is_preserved_in_snapshot(self):
        self.write("LICENSE.txt", b"Example upstream license\r\n")
        output, metadata = PACKAGE(self.source, self.output)
        files = self.contents(output)
        self.assertEqual(set(FILES) | {"runtime.json", "LICENSE"}, set(files))
        self.assertEqual(b"Example upstream license\n", files["LICENSE"])
        self.assertEqual("LICENSE.txt", metadata["upstream_license_file"])
        self.assertEqual(hashlib.sha256(files["LICENSE"]).hexdigest(), metadata["files"]["LICENSE"])


if __name__ == "__main__":
    unittest.main()
