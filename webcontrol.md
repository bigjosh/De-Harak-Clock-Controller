# Web controls

The Pi serves static pages through Apache and runs CGI scripts as `www-data`.
The normal `control.html` page sends animation commands through `light.cgi` to
`/tmp/clockcommands`, which the existing `pipereader.sh` service consumes.

For the DLD deployment page, use the [GitHub installer](#one-time-setup-on-the-pi)
below; it handles missing packages and chooses the CGI module. To set up the
older control pages manually, install Apache and enable CGI for its current MPM:

```sh
sudo apt-get install apache2 python3 openssh-client
if sudo apache2ctl -M 2>/dev/null | grep -q mpm_prefork_module; then
  sudo a2enmod cgi
else
  sudo a2enmod cgid
fi
sudo apache2ctl configtest
sudo systemctl reload apache2
```

After changing web files, run this from the controller checkout:

```sh
sh webcontrol/install.sh
```

This full-web installer copies static files into `/var/www/html`, installs executable
CGI scripts into `/usr/lib/cgi-bin`, and reloads Apache. It also works when
invoked by an absolute path from another directory. It can replace existing
control files; the DLD installers use its `--dld-only` mode to preserve them.

## Trial deployment of DLD

Open **`/deploy.html`** directly on the Pi's web server. The normal control
page and index do not link to it. It displays the clock as **12 columns and
6 rows**: `H01`–`H12` across the top, followed by `M00`–`M59` from left to
right across the five lower rows. Smaller screens can scroll the grid
horizontally without changing its physical arrangement.

Click a digit to start its trial deployment immediately. The page shows the
deployment's console output and final result. Only one web deployment can run
at a time. Output updates about once per second; a lost browser connection or
closed tab does not cancel the deployment. Reload the page to recover the
active job, or return to a saved job URL to read its result.

The new page intentionally has **no login**. Keeping its URL out of the normal
menu only makes it less discoverable; anyone who knows the URL can deploy.
The CGI uses POST requests, a browser-bound token, and a strict digit-name
allowlist to prevent cross-site or malformed requests from starting jobs.
The browser cannot supply shell commands, paths, SSH options, or FFS indices.

The browser token is checked independently of Apache's hostname so the page
also works through an HTTPS proxy that rewrites the backend `Host` header.

### One-time setup on the Pi

The Pi can install the page and its complete DLD runtime directly from this
public GitHub repository. No local checkout, gateway directory, GitHub login,
compiler, or separate DLD release is needed. Push all the deployment-page
files, including `webcontrol/dld-runtime.tar.gz` and its checksum, before running
the command. The example uses the development branch `add-snow`; change `ref`
if the changes are published under another branch, tag, or commit.

Paste this into the Pi's SSH terminal:

```sh
(
  set -eu
  ref=add-snow
  installer=$(mktemp /tmp/install-clock-deploy.XXXXXX)
  curl --fail --location --proto '=https' --proto-redir '=https' \
    --output "$installer" \
    "https://raw.githubusercontent.com/bigjosh/De-Harak-Clock-Controller/$ref/webcontrol/install-from-github.sh"
  sudo sh "$installer" "$ref"
)
```

If `curl` is missing, first run
`sudo apt-get update && sudo apt-get install -y curl ca-certificates`.
The installer installs other missing prerequisites through `apt-get`, selects
the Apache CGI module for its current configuration, and reloads Apache.
Older OpenSSH clients are supported: the bundled launcher uses their default
SCP protocol. For newer clients it selects that protocol with `scp -O` after a
local capability check. No client upgrade is needed just to add this option.

The download is a single controller snapshot over verified HTTPS. Before
installation, the script checks the runtime archive checksum, all nested native
file checksums, the BBG kernel requirement, and the exact match between the
launcher bootstrap and the bundled copy. It extracts only the required files.
The package/checksum pair detects corruption; it is not an independent signature.
The native payload targets **ARMv7 Linux 3.8.13-bone80 on the BBGs**. The Pi itself
can be 32-bit or 64-bit.

Only the new deployment page, its assets, and its CGI are installed. Existing
`control.html`, `index.html`, `light.cgi`, and any existing shared Bootstrap CSS
are preserved. The installer never contacts a digit or changes the running
clock mode. Open **`/deploy.html`** directly after it finishes.

To download and validate without installing, replace the final command in the
block with `sh "$installer" "$ref" --check`. This does not need sudo. Downloads
and verified source are retained in the printed `/tmp/clock-deploy-install.*`
directory for inspection. Rerun the install command to update the page and
runtime from a newer pushed ref; a tag or full commit SHA selects a fixed version.

### Installing from an existing local DLD directory

The original local-directory installer remains available. Stage a **current**
checkout or gateway package from the
[DLD repository](https://github.com/bigjosh/deharrak-leds-driver) on the Pi.
It must contain these matching files:

```text
tools/deploy-trial-digit.sh
tools/deploy-trial.sh
tools/trial-remote.py
build/dld-trial.tar.gz
```

The original DLD `v0.1.0` release predates the named-digit wrapper, FFS, and
automatic LEDscape import. Updating only its shell script is insufficient;
use a current bundle and its matching bootstrap. The Pi needs an OpenSSH
client; the current Linux launcher supports both old and new `scp` versions.

From the controller checkout, substitute the location of that DLD directory:

```sh
sudo sh webcontrol/install-dld-trial.sh /path/to/current-dld-gateway
```

This installs a private writable job directory for `www-data`, copies only
the four runtime files into a new root-owned directory under
`/opt/clock-controller`, writes `/etc/clock-controller/dld-trial.json`, and
installs the web files. It does not contact a digit or change the clock mode.
Apache never runs the deployment as local root, and no general sudo access
is granted to the web server.

The configuration contains two absolute paths:

```json
{
  "gateway_dir": "/opt/clock-controller/dld-gateway.EXAMPLE",
  "state_dir": "/var/lib/clock-controller/dld-trial"
}
```

The installer fills in the actual generated gateway directory. Job logs and
status files live in the state directory; deployment code and bundle files
are readable but not writable by `www-data`.

DNS must resolve the digit names on the Pi, and noninteractive SSH to the
BBGs must work as `www-data`. For a read-only connection check:

```sh
sudo -u www-data ssh -o BatchMode=yes -o ConnectTimeout=10 \
  -o StrictHostKeyChecking=no -o UserKnownHostsFile=/dev/null \
  -o GlobalKnownHostsFile=/dev/null root@m34 true
```

This uses the same host-key acceptance policy as the DLD trial launcher.
An SSH setup that works only through the Pi user's private keys or SSH agent
does not automatically work for Apache; resolve that access before using
the deploy page. This installation does not copy private keys.

### What a click does

The CGI launches the installed DLD `tools/deploy-trial-digit.sh` with exactly
one validated digit name. That shared wrapper owns the name-to-index mapping:
`h01=0`, `h12=11`, `m00=12`, `m34=46`, and `m59=71`.

The DLD launcher imports strip lengths and color order from the target's
`/etc/ledscape-config.json`,
sets the FFS index, uploads the bundle into a fresh BBG `/run` directory,
validates it, stops the old LEDscape or DLD process, initializes the driver,
and starts its UDP receiver. The controller's running clock/animation process
continues to send its existing UDP packets during the handover.

All six legacy RGB channel-order permutations are supported. LEDscape's setting
names the order in memory, and its PRU transmits those bytes in reverse order;
for example, legacy `GBR` becomes DLD profile `ws2811-hs-rbg` (RBG on the wire).
The original LEDscape file is preserved. These compatibility profiles use the
same DLD pulse timing; they change channel placement, not waveform durations.
If an older bundle rejects legacy `GBR`, `GRB`, or `RBG`, rerun the current
GitHub installer to update the complete runtime, then retry the digit. Changing
only the importer is insufficient because the commands, kernel helper, and PRU
firmware must all recognize the added profiles. Color-order import failures
occur before the helper stops the digit's existing receiver.

The handover remains a trial: the target's persistent LEDscape files and boot
setup are preserved. A target reboot restores its existing boot behavior.
The browser reports command failure and retains the console output; it does
not report a successful deployment simply because the job was accepted.

### Input protocols and indicators

Both inputs run at the same time on each deployed BBG:

| Input | UDP port | Panel color |
| --- | --- | --- |
| Existing OPC packets | 7890 | First RGB pixel, repeated uniformly across every enabled string |
| Full Frame Snapshot (FFS) | 6565 | RGB value at the panel's `ffs_index` in a 216-byte packet |

An FFS packet contains exactly 72 consecutive three-byte RGB values, with no
header. Send it by broadcast on the clock's subnet. The values follow the
display from left to right, top to bottom: `H01`–`H12`, then `M00`–`M59`.
Whichever valid packet the receiver reads last supplies the color, regardless
of protocol. FFS is disabled when `ffs_index` is absent; named-digit deployment
always sets it. The existing Pi clock scripts keep sending OPC during a trial.

The OPC shim provides one color for the whole panel. It does not reproduce
spatial images or animations within a panel from the remaining packet pixels.

The web launcher uses the receiver's default indicators: one green smooth flash
at startup and a red smooth flash after more than 60 seconds since the latest
received datagram or completion of the previous red flash. Each flash ramps up
for 0.5 seconds and back down for 0.5 seconds. A completed flash leaves the panel
black until another valid color arrives. Accepted color input interrupts either flash at the next frame,
so the startup flash may be cut short while the clock is already streaming.
Repeated red flashes indicate that the receiver is not receiving UDP traffic.
Even malformed datagrams reset the idle timer, although they do not change the
color or interrupt an active flash. The command-line digit wrapper
offers `--no-startup-flash` and `--no-idle-flash`; the browser uses the defaults.

### Update or troubleshoot

Rerun the GitHub install command with a newer pushed ref, or use
`install-dld-trial.sh` with a newer matching DLD directory, to update the gateway
copy. Installation refuses while a web deployment holds the job lock.
Earlier gateway copies and job records are retained.

If the page reports that deployment is not configured, run the setup command
above. For permission or CGI failures, check Apache's error log and the
ownership of `/var/lib/clock-controller/dld-trial`. For a failed deployment,
read the output on the page; the underlying launcher prints the target's
temporary directory for its detailed logs. A CGI/job lock serializes web
deployments only; avoid running a separate manual deployment concurrently.

There is no automatic whole-job timeout or retry. If an SSH connection stalls
after connecting, inspect the saved log and the Pi's SSH processes before
intervening; the target may already be partway through its handover.

Older SSH clients may print `Could not create directory '/var/www/.ssh'` when
running as Apache's `www-data`. That warning alone is not a deployment failure:
the launcher uses `/dev/null` for the host-key file and can still connect. Read
the final DLD error and exit status to identify a failed deployment.

The standalone backend checks in `webcontrol/tests/test_dld_trial.py` run on
Linux with fake deployment scripts. They do not contact the clock's panels.

```sh
python3 -m unittest discover -s webcontrol/tests -p test_dld_trial.py
```

The runtime and backend suite support Python 3.2+. The installer fixture suite
uses Python 3.4+ and runs on Windows or Linux without changing system paths:

```sh
python3 webcontrol/tests/test_install_dld_trial.py
```

### Refreshing the bundled runtime before publishing

`webcontrol/dld-runtime.tar.gz` is a generated snapshot of the four deployment
runtime files, with checksums and upstream provenance in `runtime.json`. Make
DLD code changes in its owning repository; do not edit the packaged copies.
After building and testing a matching native DLD bundle, refresh the snapshot
from the controller checkout on the packaging computer (Python 3.8+):

```sh
python3 webcontrol/package-dld-runtime.py ../deharrak-leds-driver
```

Commit and push both `webcontrol/dld-runtime.tar.gz` and
`webcontrol/dld-runtime.sha256` with the web installer changes. The packager
validates the native bundle against the upstream validator and excludes
unrelated build files, credentials, and live panel configurations. Its metadata
records the upstream base commit and whether that checkout had uncommitted
changes; it does not pretend a working snapshot is a published release.

Additional local checks (no panels or installed system files are touched):

```sh
python3 webcontrol/tests/test_install_from_github.py
python3 webcontrol/tests/test_install_legacy_scp.py
python3 webcontrol/tests/test_install_web.py
python3 webcontrol/tests/test_package_dld_runtime.py
```

The packaging helper and its tests need Python 3.8+. The shell installer tests
use `/bin/sh` on Linux or Git for Windows' shell on Windows. These checks cover
download validation, selective installation, package integrity, and deployment
job handling; physical waveform qualification is documented in the DLD repository.
