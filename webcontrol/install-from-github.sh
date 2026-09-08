#!/bin/sh
# Install the standalone DLD deployment page and its bundled runtime from GitHub.
set -eu

usage() {
    printf '%s\n' 'usage: sudo sh install-from-github.sh [REF] [--check]' \
        '  REF is a controller branch, tag, or commit (default: master).' \
        '  --check downloads and validates only; no sudo or installed changes.' \
        '  Installs /deploy.html without changing the existing clock controls.'
}
fail() { printf 'install-from-github: %s\n' "$1" >&2; exit 1; }
ref=master
have_ref=no
check=no
for argument do
    case "$argument" in
        --help) usage; exit 0 ;;
        --check) check=yes ;;
        -*|'') usage >&2; exit 2 ;;
        *) [ "$have_ref" = no ] || { usage >&2; exit 2; }
           ref=$argument; have_ref=yes ;;
    esac
done
case "$ref" in *[!A-Za-z0-9._/-]*) fail 'REF must be a branch, tag, or commit name.' ;; esac
if [ "$check" = no ] && [ "$(id -u)" -ne 0 ]; then
    fail 'Run with sudo, or use --check to download and validate without installing.'
fi

# The live clock Pi normally has these already. Install only missing tools.
packages=
for pair in curl:curl python3:python3; do
    command -v "${pair%%:*}" >/dev/null 2>&1 || packages="$packages ${pair#*:}"
done
if [ "$check" = no ]; then
    command -v ssh >/dev/null 2>&1 && command -v scp >/dev/null 2>&1 || packages="$packages openssh-client"
    command -v apache2ctl >/dev/null 2>&1 || packages="$packages apache2"
fi
if [ -n "$packages" ]; then
    [ "$check" = no ] || fail "Missing tools. Install these packages first:$packages"
    command -v apt-get >/dev/null 2>&1 || fail "Install these packages first:$packages"
    apt-get update
    # Package names above are fixed, not supplied by the caller.
    apt-get install -y ca-certificates $packages
fi

umask 077
stage=$(mktemp -d /tmp/clock-deploy-install.XXXXXX)
printf 'Downloading controller %s into %s\n' "$ref" "$stage"
curl --fail --location --proto '=https' --proto-redir '=https' \
    --retry 2 --connect-timeout 20 --max-time 300 \
    --output "$stage/controller.tar.gz" \
    "https://codeload.github.com/bigjosh/De-Harak-Clock-Controller/tar.gz/$ref"

# Read only the required regular files; never extract arbitrary archive paths,
# symlinks, or unrelated controller programs into the Pi's live directories.
python3 - "$stage" <<'PY'
from __future__ import print_function
import hashlib
import io
import json
import os
import re
import sys
import tarfile

WEB_FILES = (
    'webcontrol/install.sh', 'webcontrol/install-dld-trial.sh',
    'webcontrol/dld-runtime.tar.gz', 'webcontrol/dld-runtime.sha256',
    'webcontrol/var_www/deploy.html', 'webcontrol/var_www/css/deploy.css',
    'webcontrol/var_www/css/bootstrap.min.css', 'webcontrol/var_www/js/deploy.js',
    'webcontrol/usr_lib_cgi-bin/dld-trial.cgi',
)
RUNTIME_FILES = set(('tools/deploy-trial-digit.sh', 'tools/deploy-trial.sh',
                     'tools/trial-remote.py', 'build/dld-trial.tar.gz'))
NATIVE_FILES = set(('build/dld-init', 'build/dld-send', 'build/dld-udp',
                    'build/dld-config-check', 'build/build-report.txt',
                    'kernel/dld_quiet.ko', 'tools/bench_prepare.py',
                    'tools/trial-remote.py'))

def fail(message):
    raise ValueError(message)

def sha(data):
    return hashlib.sha256(data).hexdigest()

def read_archive(archive, required, optional=(), github=False):
    allowed = set(required) | set(optional)
    files = {}
    total = 0
    roots = set()
    for member in archive:
        name = member.name
        if github:
            root, separator, name = name.partition('/')
            roots.add(root)
            if not separator or name not in allowed:
                continue
        elif name not in allowed:
            fail('Unexpected runtime archive member: ' + name)
        if not member.isfile() or name in files:
            fail('Expected a unique regular file: ' + name)
        total += member.size
        if member.size <= 0 or total > 16 * 1024 * 1024:
            fail('Archive payload is empty or exceeds 16 MiB.')
        files[name] = archive.extractfile(member).read()
    missing = set(required) - set(files)
    if missing:
        fail('Missing required files: ' + ', '.join(sorted(missing)) +
             '. Push the complete deploy-page changes and runtime package to this GitHub ref first.')
    if github and len(roots) != 1:
        fail('Expected one controller snapshot in the GitHub archive.')
    return files

def check_hashes(manifest, files, names):
    hashes = manifest.get('files')
    if not isinstance(hashes, dict) or set(hashes) != set(names):
        fail('Manifest file list does not match the package.')
    for name in names:
        if hashes[name] != sha(files[name]):
            fail('Checksum mismatch: ' + name)

def write_files(destination, files):
    for name, data in files.items():
        path = os.path.join(destination, name)
        parent = os.path.dirname(path)
        if not os.path.isdir(parent):
            os.makedirs(parent)
        with open(path, 'wb') as stream:
            stream.write(data)

def prepare(stage):
    with tarfile.open(os.path.join(stage, 'controller.tar.gz'), 'r:gz') as archive:
        web = read_archive(archive, WEB_FILES, github=True)
    packed = web['webcontrol/dld-runtime.tar.gz']
    sidecar = web['webcontrol/dld-runtime.sha256'].decode('ascii')
    match = re.match(r'\A([0-9a-f]{64})  dld-runtime\.tar\.gz\n?\Z', sidecar)
    if not match or match.group(1) != sha(packed):
        fail('DLD runtime package checksum mismatch.')
    with tarfile.open(fileobj=io.BytesIO(packed), mode='r:gz') as archive:
        runtime = read_archive(archive, RUNTIME_FILES | set(('runtime.json',)), ('LICENSE',))
    metadata = json.loads(runtime['runtime.json'].decode('utf-8'))
    if (not isinstance(metadata, dict) or type(metadata.get('schema')) is not int
            or metadata.get('schema') != 1 or metadata.get('native_architecture') != 'armv7l'
            or metadata.get('native_kernel_release') != '3.8.13-bone80'):
        fail('Unsupported DLD runtime metadata.')
    check_hashes(metadata, runtime, set(runtime) - set(('runtime.json',)))
    bundle = runtime['build/dld-trial.tar.gz']
    if metadata.get('native_bundle_sha256') != sha(bundle):
        fail('Native bundle checksum mismatch.')
    with tarfile.open(fileobj=io.BytesIO(bundle), mode='r:gz') as archive:
        native = read_archive(archive, NATIVE_FILES | set(('manifest.json',)))
    manifest = json.loads(native['manifest.json'].decode('utf-8'))
    if (not isinstance(manifest, dict) or type(manifest.get('schema')) is not int
            or manifest.get('schema') != 1 or manifest.get('kernel_release') != '3.8.13-bone80'
            or manifest.get('lock_path') != '/run/dld.lock'):
        fail('Unsupported native DLD bundle; expected ARMv7 Linux 3.8.13-bone80.')
    check_hashes(manifest, native, NATIVE_FILES)
    if native['tools/trial-remote.py'] != runtime['tools/trial-remote.py']:
        fail('DLD launcher bootstrap differs from its native bundle.')
    for name in ('tools/deploy-trial-digit.sh', 'tools/deploy-trial.sh', 'tools/trial-remote.py'):
        if b'\r' in runtime[name]:
            fail('DLD script must use Linux line endings: ' + name)
    write_files(os.path.join(stage, 'controller'), web)
    write_files(os.path.join(stage, 'gateway'), runtime)
    print('Verified deployment page and matching DLD runtime: ' + sha(packed))
    print('BBG target: ARMv7 Linux 3.8.13-bone80; no compilation on the Pi.')

if __name__ == '__main__':
    try:
        prepare(sys.argv[1])
    except (ValueError, KeyError, TypeError, UnicodeError, IOError, tarfile.TarError) as error:
        sys.exit('install-from-github: ' + str(error))
PY

if [ "$check" = yes ]; then
    printf 'Validation complete. Downloaded files retained in %s\nNo installed files or panels were changed.\n' "$stage"
    exit 0
fi

scp_usage=$(LC_ALL=C scp -O </dev/null 2>&1 || :)
case "$scp_usage" in
    *'unknown option'*|*'illegal option'*|*'invalid option'*)
        fail 'This Pi has an old scp client. Update openssh-client to a version supporting scp -O, then rerun.' ;;
esac
modules=$(apache2ctl -M 2>&1) || fail "Apache configuration check failed: $modules"
case "$modules" in
    *cgi_module*|*cgid_module*) ;;
    *mpm_prefork_module*) a2enmod cgi ;;
    *) a2enmod cgid ;;
esac
apache2ctl configtest
sh "$stage/controller/webcontrol/install-dld-trial.sh" "$stage/gateway"
printf 'Download and verified source retained in %s\n' "$stage"
