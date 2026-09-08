#!/bin/sh
# Install the web files from any working directory.
set -eu
script_dir=$(CDPATH= cd -- "$(dirname -- "$0")" && pwd)
if [ "$(id -u)" -ne 0 ]; then
    exec sudo sh "$script_dir/install.sh" "$@"
fi
case "$#:$*" in
    0:) mode=all ;;
    1:--dld-only) mode=dld ;;
    *) printf '%s\n' 'usage: sh webcontrol/install.sh [--dld-only]' >&2; exit 2 ;;
esac
install -d -m 0755 /var/www/html /usr/lib/cgi-bin
if [ "$mode" = dld ]; then
    install -d -m 0755 /var/www/html/css /var/www/html/js
    install -m 0644 "$script_dir/var_www/deploy.html" /var/www/html/deploy.html
    install -m 0644 "$script_dir/var_www/css/deploy.css" /var/www/html/css/deploy.css
    install -m 0644 "$script_dir/var_www/js/deploy.js" /var/www/html/js/deploy.js
    # The existing control page may already use its own Bootstrap copy.
    if [ ! -e /var/www/html/css/bootstrap.min.css ]; then
        install -m 0644 "$script_dir/var_www/css/bootstrap.min.css" /var/www/html/css/bootstrap.min.css
    fi
    install -m 0755 "$script_dir/usr_lib_cgi-bin/dld-trial.cgi" /usr/lib/cgi-bin/dld-trial.cgi
else
    cp -R "$script_dir/var_www/." /var/www/html/
    for script in "$script_dir"/usr_lib_cgi-bin/*; do
        [ -f "$script" ] || continue
        install -m 0755 "$script" /usr/lib/cgi-bin/
    done
fi
systemctl reload apache2
