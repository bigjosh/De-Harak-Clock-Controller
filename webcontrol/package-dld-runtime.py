#!/usr/bin/env python3
"""Refresh the bundled DLD runtime snapshot from a trusted checkout; Python 3.8+."""

import argparse
import gzip
import hashlib
import io
import json
from pathlib import Path
import re
import runpy
import subprocess
import tarfile


UPSTREAM_URL = "https://github.com/bigjosh/deharrak-leds-driver"
RUNTIME_FILES = (
    "tools/deploy-trial-digit.sh", "tools/deploy-trial.sh",
    "tools/trial-remote.py", "build/dld-trial.tar.gz",
)
LICENSE_NAMES = ("LICENSE", "LICENSE.md", "LICENSE.txt", "COPYING")


def digest(data):
    return hashlib.sha256(data).hexdigest()


def read_source(root, name):
    path = root / name
    if path.is_symlink() or not path.is_file():
        raise ValueError("source must be a regular file: " + name)
    path.resolve().relative_to(root)
    data = path.read_bytes()
    if not data:
        raise ValueError("source is empty: " + name)
    return data


def normalized_text(data, name):
    normalized = data.replace(b"\r\n", b"\n")
    normalized.decode("utf-8")
    if b"\r" in normalized or b"\0" in normalized:
        raise ValueError("source contains unsupported text bytes: " + name)
    return normalized


def package(root, output_directory):
    """Only include the explicit deployment runtime, never upstream build trees."""
    root = Path(root).resolve()
    output_directory = Path(output_directory).resolve()
    sources = {name: read_source(root, name) for name in RUNTIME_FILES}
    payloads = {name: normalized_text(data, name) if name.endswith((".sh", ".py"))
                else data for name, data in sources.items()}

    # Reuse the owning project's complete native manifest and checksum checks.
    # Loading this helper executes trusted checkout code on the packaging PC;
    # no Python packaging/build tools are needed on the destination Pi.
    helper_name = "tools/package-gateway.py"
    helper = read_source(root, helper_name)
    check_bundle = runpy.run_path(str(root / helper_name))["check_bundle"]
    native_manifest = check_bundle(payloads["build/dld-trial.tar.gz"],
                                   payloads["tools/trial-remote.py"])

    commit = subprocess.check_output(
        ["git", "rev-parse", "HEAD"], cwd=str(root)).decode("ascii").strip()
    if not re.fullmatch(r"[0-9a-f]{40}", commit):
        raise ValueError("upstream HEAD is not a complete commit SHA")
    dirty = bool(subprocess.check_output(
        ["git", "status", "--porcelain", "--untracked-files=normal"], cwd=str(root)))

    license_name = None
    for name in LICENSE_NAMES:
        if (root / name).exists() or (root / name).is_symlink():
            payloads["LICENSE"] = normalized_text(read_source(root, name), name)
            license_name = name
            break

    metadata = {
        "schema": 1,
        "description": "Packaged DLD runtime snapshot, not a separate editable codebase. "
                       "Refresh with package-dld-runtime.py from the upstream checkout. "
                       "The base commit identifies that checkout's HEAD; it does not "
                       "claim these bytes came from a clean commit or a published release.",
        "upstream_url": UPSTREAM_URL,
        "upstream_base_commit": commit,
        "upstream_dirty": dirty,
        "upstream_license_file": license_name,
        "source_files_sha256": {name: digest(data) for name, data in sorted(sources.items())},
        "validator_source_sha256": digest(helper),
        "files": {name: digest(data) for name, data in sorted(payloads.items())},
        "native_bundle_sha256": digest(payloads["build/dld-trial.tar.gz"]),
        "native_kernel_release": native_manifest["kernel_release"],
        "native_architecture": "armv7l",
    }
    payloads["runtime.json"] = (json.dumps(metadata, indent=2, sort_keys=True) + "\n").encode("utf-8")

    buffer = io.BytesIO()
    with gzip.GzipFile(filename="", fileobj=buffer, mode="wb", mtime=0) as compressed:
        with tarfile.open(fileobj=compressed, mode="w", format=tarfile.USTAR_FORMAT) as archive:
            for name, data in sorted(payloads.items()):
                member = tarfile.TarInfo(name)
                member.size = len(data)
                member.mode = 0o755 if name.endswith(".sh") else 0o644
                member.mtime = 0
                archive.addfile(member, io.BytesIO(data))
    packed = buffer.getvalue()
    output_directory.mkdir(parents=True, exist_ok=True)
    output = output_directory / "dld-runtime.tar.gz"
    checksum = output_directory / "dld-runtime.sha256"
    if output.is_symlink() or checksum.is_symlink():
        raise ValueError("refusing a symlink output")
    output.write_bytes(packed)
    checksum.write_bytes((digest(packed) + "  dld-runtime.tar.gz\n").encode("ascii"))
    return output, metadata


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("dld_directory", type=Path,
                        help="trusted upstream DLD checkout with a current native build/dld-trial.tar.gz")
    parser.add_argument("--output-dir", type=Path, default=Path(__file__).resolve().parent)
    args = parser.parse_args()
    output, metadata = package(args.dld_directory, args.output_dir)
    print(output)
    print((output.parent / "dld-runtime.sha256").read_text().strip())
    print("Upstream base: " + metadata["upstream_base_commit"] +
          (" (working tree has changes)" if metadata["upstream_dirty"] else " (working tree clean)"))


if __name__ == "__main__":
    try:
        main()
    except (OSError, UnicodeError, ValueError, tarfile.TarError,
            subprocess.CalledProcessError) as error:
        raise SystemExit("package-dld-runtime: " + str(error))
