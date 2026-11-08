# Wallos

Wallos tracks recurring subscriptions and expenses. It is available through
the TLS-terminating gateway at `https://wallos.dejima.men` and directly on the
LAN at `http://wallos.n100.lan`. Create the first account promptly after the
application becomes reachable; Wallos presents a registration page on a fresh
database.

The single replica runs on `n100`. The `wallos-db` and `wallos-logos` PVCs use
`local-path` storage for SQLite and uploaded images, respectively. The upstream
container listens on port 80 and starts nginx, PHP-FPM and its own scheduled
jobs. Its startup script requires root to change the `www-data` ownership of
these directories and start the services. The pod has no Kubernetes API token.

The `wallos-backup` CronJob runs daily at 05:00 UTC. It makes a SQLite online
backup and archives uploaded logos into
`/Pi-NAS/wallos/wallos-backups/wallos-<UTC timestamp>/`. It retains backups for
14 days on the dedicated `nfs-client-wallos` StorageClass. To restore, stop the
Wallos deployment, copy `wallos.db` into the DB PVC, remove any stale
`wallos.db-wal` and `wallos.db-shm` files, extract `logos.tar.gz` into the logos
PVC, and restart the deployment. Keep an off-NAS copy for NAS failure recovery.

The image is pinned to Wallos 5.11.1. Review the
[upstream releases](https://github.com/ellite/Wallos/releases) before updating.

## Optional setup

The container timezone is `Asia/Tokyo`; select JPY as the main currency in
Wallos after creating the account. Configure an exchange-rate provider if
tracking subscriptions in other currencies.

Future options include payment and cancellation reminders through the existing
ntfy service, and OIDC login through Authentik. Internal integration endpoints
may require the Wallos SSRF allowlist; see the
[upstream configuration](https://github.com/ellite/Wallos#oidc).
For backup operations, consider failure notifications, periodic restore tests,
and NAS snapshots or replication to another device. These integrations are
not configured by the current manifests.
