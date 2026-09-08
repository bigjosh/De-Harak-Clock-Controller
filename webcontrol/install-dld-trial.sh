#!/bin/sh
# Stage a current DLD gateway for Apache, then install the web UI and CGI.
set -eu

usage() {
    printf '%s\n' 'usage: sudo sh webcontrol/install-dld-trial.sh GATEWAY_DIRECTORY' \
        '  Use a current DLD checkout or gateway package containing build/dld-trial.tar.gz.' \
        '  Installs an unlinked /deploy.html page. It does not add authentication.'
}
if [ "$#" -eq 1 ] && [ "$1" = --help ]; then usage; exit 0; fi
[ "$#" -eq 1 ] || { usage >&2; exit 2; }
[ "$(id -u)" -eq 0 ] || { printf '%s\n' 'Run this installer with sudo.' >&2; exit 2; }
for tool in python3 ssh scp; do
    command -v "$tool" >/dev/null 2>&1 || { printf '%s is required.\n' "$tool" >&2; exit 2; }
done
scp_usage=$(LC_ALL=C scp -O </dev/null 2>&1 || :)
case "$scp_usage" in
    *'unknown option'*|*'illegal option'*|*'invalid option'*)
        printf '%s\n' 'The Pi needs an OpenSSH scp client supporting -O. Update openssh-client before installing.' >&2
        exit 2 ;;
esac
script_dir=$(CDPATH= cd -- "$(dirname -- "$0")" && pwd)

python3 - "$1" "$script_dir/install.sh" <<'PY'
from __future__ import print_function
import errno
import fcntl
import json
import os
import pwd
import shutil
import stat
import subprocess
import sys
import tempfile

source = os.path.realpath(sys.argv[1])
files = ('tools/deploy-trial-digit.sh', 'tools/deploy-trial.sh',
         'tools/trial-remote.py', 'build/dld-trial.tar.gz')
for name in files:
    path = os.path.join(source, name)
    if not os.path.isfile(path) or not os.path.getsize(path):
        sys.exit('Missing current DLD gateway file: ' + path +
                 '\nThe original v0.1.0 release does not support named-digit FFS deployment.')

account = pwd.getpwnam('www-data')
base = '/opt/clock-controller'
config_dir = '/etc/clock-controller'
state_parent = '/var/lib/clock-controller'
state_dir = os.path.join(state_parent, 'dld-trial')

def directory(path, owner, mode):
    if os.path.islink(path):
        sys.exit('Refusing a symlink directory: ' + path)
    if not os.path.isdir(path):
        os.makedirs(path, mode)
    os.chown(path, owner, account.pw_gid if owner == account.pw_uid else 0)
    os.chmod(path, mode)

for path in (base, config_dir, state_parent):
    directory(path, 0, 0o755)
directory(state_dir, account.pw_uid, 0o700)

lock = os.open(os.path.join(state_dir, 'deploy.lock'),
               os.O_CREAT | os.O_RDWR | os.O_NOFOLLOW, 0o600)
try:
    if not stat.S_ISREG(os.fstat(lock).st_mode):
        sys.exit('Deployment lock must be a regular file.')
    os.fchown(lock, account.pw_uid, account.pw_gid)
    os.fchmod(lock, 0o600)
    try:
        fcntl.flock(lock, fcntl.LOCK_EX | fcntl.LOCK_NB)
    except IOError as error:
        if error.errno in (errno.EACCES, errno.EAGAIN):
            sys.exit('A web deployment is active. Wait for it to finish before updating the gateway.')
        raise

    # Each update gets a complete new copy. Earlier bundles and job logs remain
    # available; a partial copy never replaces the configured gateway.
    gateway = tempfile.mkdtemp(prefix='dld-gateway.', dir=base)
    os.chmod(gateway, 0o755)
    for name in files:
        destination = os.path.join(gateway, name)
        parent = os.path.dirname(destination)
        if not os.path.isdir(parent):
            os.makedirs(parent, 0o755)
        os.chmod(parent, 0o755)
        shutil.copyfile(os.path.join(source, name), destination)
        os.chmod(destination, 0o755 if name.endswith('.sh') else 0o644)

    # Keep the deployment lock until the web code is installed too. Reloading
    # Apache avoids terminating its detached jobs via a service restart.
    subprocess.check_call(['/bin/sh', sys.argv[2], '--dld-only'], close_fds=True)
    descriptor, temporary = tempfile.mkstemp(prefix='.dld-trial-', dir=config_dir)
    with os.fdopen(descriptor, 'w') as stream:
        json.dump({'gateway_dir': gateway, 'state_dir': state_dir}, stream, indent=2)
        stream.write('\n')
    os.chmod(temporary, 0o644)
    os.rename(temporary, os.path.join(config_dir, 'dld-trial.json'))
    print('DLD gateway staged for www-data: ' + gateway)
    print('Job logs: ' + state_dir)
finally:
    os.close(lock)
PY

printf '%s\n' 'Open /deploy.html directly; the normal control page has no link to it.' \
    'This installer has not connected to any digit or changed the running clock mode.'
