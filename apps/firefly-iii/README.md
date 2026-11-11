# Firefly III

Firefly III manages personal finances, bills, and recurring transactions at
`https://firefly-iii.dejima.men`. The official container is pinned to
`version-6.7.9`; PostgreSQL and its backup client use the official pinned
`postgres:17.11-trixie` image. Both workloads use plain Kubernetes manifests.
PostgreSQL initializes a dedicated `firefly` database and non-superuser account
on an empty data volume. The application never receives the administrator password.

This replaces Wallos with a fresh Firefly III installation. The old Wallos
workloads and all three PVCs are pruned; existing subscriptions, database,
logos, and NAS backups are discarded. There is no data migration or rollback
copy. The `wallos` Argo CD Application remains only to reconcile deletion and
run the NAS cleanup hook; see [the retirement guide](../wallos/README.md).

## Before the first sync

Create the encrypted credentials from the example. `APP_KEY` and
`STATIC_CRON_TOKEN` must each be exactly 32 characters; generate independent
values with `openssl rand -hex 16`. Use different random database and PostgreSQL
administrator passwords, and replace `SITE_OWNER` with your email address.
Preserve `APP_KEY` across upgrades and restores.

```sh
cp apps/firefly-iii/secrets/credentials.secret.example /secure/path/firefly-iii-credentials.secret.yaml
# Replace every placeholder. Do not commit this plaintext file.
kubeseal \
  --controller-name sealed-secrets-controller \
  --controller-namespace kube-system \
  --format yaml \
  < /secure/path/firefly-iii-credentials.secret.yaml \
  > apps/firefly-iii/secrets/credentials.sealed-secret.yaml
```

The operator must create and commit the SealedSecret before deploying. Only the
template and a bootstrap ConfigMap are supplied here; without the Secret,
database and application pods cannot start. The separate `firefly-iii-secrets`
Argo CD Application reconciles credentials in wave 0, before the main application
in wave 1. Changes to Secret-backed environment variables require a pod restart.
Database initialization runs only on an empty PVC: rotating a database password
also requires changing the corresponding PostgreSQL role password; a restart
alone does not update it.

Configure gateway routing, DNS, and TLS for `firefly-iii.dejima.men` to reach
Traefik's HTTP entry point. The gateway must terminate TLS and redirect HTTP to
HTTPS for this hostname. A Traefik middleware sets `X-Forwarded-Proto: https`
and `X-Forwarded-Port: 443` for this public route so Firefly III generates
HTTPS links, redirects, and form actions without the internal HTTP port.
The application trusts proxy headers and uses secure cookies. Use the HTTPS
hostname; no direct HTTP LAN alias is configured. Restrict initial access until
you have created the first administrator account in the web interface. Firefly
III uses its own authentication. Mail currently goes to application logs;
configure SMTP separately if email delivery is needed. The optional Data Importer
is not deployed.

## Storage and scheduled jobs

The application and PostgreSQL run on `n100`. PostgreSQL's 10Gi data PVC and the
10Gi `firefly-iii-upload` PVC use `local-path`. Only uploaded attachments are
persisted from the application container, at `/var/www/html/storage/upload`,
matching the upstream Docker deployment. Sessions and caches are ephemeral.

The application and PostgreSQL each reserve `25m` CPU, with no CPU limit so
initialization and requests can use available CPU. Together they reserve `50m`;
including the `25m` backup job and `10m` cron job, Firefly III reserves at most
`85m` CPU across these workloads. At the initial deployment, `n100` had `95m`
of unreserved CPU despite only about 24% actual CPU usage. The former `100m`
request on each Deployment left both pods Pending with `Insufficient cpu`.
Recheck node CPU reservations when adding workloads; these values do not reserve
capacity for other applications. Memory requests and limits remain unchanged.

`firefly-iii-cron` calls the internal cron API at 03:00 Asia/Tokyo each
day, using the Secret's `STATIC_CRON_TOKEN`. This processes recurring transactions
and other scheduled tasks. The timezone matches the previous Wallos deployment.

`firefly-iii-backup` runs at 05:15 UTC daily on `n100`, mounting uploads read-only.
It creates a PostgreSQL custom-format dump, then archives it with `upload/`.
Only a successful dump and archive are published as a `.tar.gz`; failures leave
previous completed backups intact. Completed backups are retained for 14 days
on the 20Gi NFS PVC via `nfs-client-firefly-iii`:

```text
/Pi-NAS/firefly-iii/
└── firefly-iii-backups/
    └── firefly-iii-YYYYMMDDTHHMMSSZ.tar.gz
```

The NAS must permit UID/GID 33 to write to the backup directory and must protect
these archives as sensitive financial data. The StorageClass retains NAS data
when a PVC is removed. Local-path data remains tied to `n100`; it is not highly
available. Keep an independent secure copy of the credentials, especially
`APP_KEY`, because backup archives do not include Kubernetes Secrets.

The database dump is transactionally consistent, but attachments are copied
while the application is running. For a coordinated recovery point, pause
application writes before taking a manual backup.

## Restore

During an explicitly authorized maintenance window, pause the scheduled jobs
and stop application writes. Extract a chosen archive in a secure location;
it contains `database.dump` and `upload/`. Restore the dump into an empty
`firefly` database owned by `firefly`, using a PostgreSQL 17 client:

```sh
pg_restore --host=firefly-iii-postgresql --username=firefly \
  --dbname=firefly --no-owner --no-privileges --exit-on-error database.dump
```

Supply the database password securely, restore `upload/` to the application PVC
with ownership UID/GID 33, and restore the original credentials before starting
the pinned application image. Verify login, accounts, attachments, and recurring
transactions before resuming writes and scheduled jobs. Argo CD self-heal must
be accounted for when temporarily stopping workloads.

## Upstream references

- [Pinned Firefly III release](https://github.com/firefly-iii/firefly-iii/releases/tag/v6.7.9)
- [Pinned environment configuration](https://github.com/firefly-iii/firefly-iii/blob/v6.7.9/.env.example)
- [Official Docker deployment](https://github.com/firefly-iii/docker/blob/main/docker-compose.yml)
