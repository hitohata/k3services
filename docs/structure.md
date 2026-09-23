# System structure

## GitOps layout

`root-app/apps.yaml` is the Argo CD app-of-apps entry point. It defines each
Argo CD `Application`, which in turn deploys an application or infrastructure
component from this repository or an external Helm chart.

The `argocd-crds` application manages the upstream Argo CD CRDs pinned to the
version of the directly installed Argo CD controllers. It does not prune CRDs:
removing a cluster API type can also remove its custom resources.

```text
root-app/apps.yaml
├── infrastructure/nfs-provisioner     NFS dynamic provisioning
├── infrastructure/traefik/            trusted forwarded headers for K3s Traefik
├── apps/keda/                          event-driven autoscaling and HTTP interception
├── apps/authentik/                    identity and access management
├── apps/homepage/                     service dashboard
├── sealed-secrets Helm chart           encrypted-secret controller
├── apps/nextcloud/
│   ├── values.yaml                     Nextcloud Helm configuration
│   └── secrets/                        encrypted Nextcloud credentials
├── apps/mealie/
│   ├── values.yaml                     Mealie Helm configuration
│   ├── postgresql-values.yaml          Mealie PostgreSQL Helm configuration
│   ├── resources/                      backup PVC and CronJob
│   └── secrets/                        encrypted PostgreSQL credentials
├── apps/vaultwarden/
│   ├── deployment.yaml                 application, storage, service and ingress
│   └── backup.yaml                     backup PVC and CronJob
├── apps/it-tools/
│   └── deployment.yaml                 stateless application, service and ingress
├── apps/netdata/
│   ├── values.yaml                     Netdata Helm configuration
│   └── resources/                      restricted cluster RBAC
├── apps/linkwarden/
│   ├── postgresql-values.yaml           PostgreSQL Helm configuration
│   ├── resources/                       Linkwarden, Meilisearch, and backup manifests
│   └── secrets/                         encrypted Linkwarden credentials
├── apps/paperless/
│   ├── postgresql-values.yaml          Paperless PostgreSQL Helm configuration
│   ├── resources/                      application, Valkey, ingress and backups
│   └── secrets/                        encrypted application/database credentials
├── apps/forgejo/
│   ├── values.yaml                     Forgejo Helm configuration
│   ├── postgresql-values.yaml          Forgejo PostgreSQL Helm configuration
│   ├── resources/                      backup PVC and CronJob
│   └── secrets/                        encrypted administrator and database credentials
├── apps/jellyfin/
│   ├── deployment.yaml                 media server, storage, service and ingress
│   └── backup.yaml                     configuration backup PVC and CronJob
├── apps/stirling-pdf/
│   └── deployment.yaml                 application, configuration storage, service and ingress
├── apps/n8n/
    └── deployment.yaml                 workflow automation, data storage, service and ingress
├── apps/ntfy/
    └── deployment.yaml                 notification server, cache storage, service and ingress
└── apps/navidrome/
    ├── deployment.yaml                 music server, storage, service and ingress
    └── backup.yaml                     SQLite backup PVC and CronJob
```

The root application references the upstream Nextcloud Helm chart and the
app-specific `apps/nextcloud/values.yaml` through Argo CD multi-source support.
This requires Argo CD 2.6 or later. The release is pinned to chart version
`9.2.5`. Updating that version is an intentional maintenance change: read the
chart release notes and upgrade Nextcloud by no more than one major version at a
time.

## Ingress forwarded headers

K3s manages the Traefik Helm chart. The `traefik-config` application supplies
a `HelmChartConfig` that trusts forwarded headers on Traefik's HTTP `web` entry
point only from the TLS-terminating gateway at `192.168.10.1`. The gateway must
set `X-Forwarded-Proto: https` for HTTPS requests. This preserves the original
scheme for ingress workloads without enabling insecure forwarded-header trust.

Changing this configuration rolls out Traefik and briefly interrupts ingress
traffic.

Traefik also permits `ExternalName` Ingress backends. This allows an Ingress
in an application namespace to reach the KEDA HTTP interceptor in the `keda`
namespace. Only Stirling PDF uses this mechanism currently.

## KEDA components

| Component | Purpose | Storage |
| --- | --- | --- |
| KEDA | Creates autoscaling resources and supplies external metrics to Kubernetes HPA | None |
| KEDA HTTP Add-on | Intercepts HTTP traffic, reports demand, and holds cold-start requests | None |

KEDA core and its HTTP Add-on run in the `keda` namespace. The HTTP interceptor
keeps one replica running for the initial proof-of-concept. Stirling PDF's
Ingress targets an `ExternalName` bridge to that interceptor; the interceptor
then forwards matching requests to Stirling's ordinary Service. KEDA scales
the Stirling PDF Deployment to zero after 30 minutes with no HTTP demand and
scales it to at most one replica. A first request after scale-down may wait for
the application to start; the interceptor's readiness timeout is seven minutes.
The KEDA Application uses server-side apply so its large ScaledJob CRD can be
created without exceeding Kubernetes' client-side apply annotation limit.

## Authentik components

| Component | Purpose | Storage |
| --- | --- | --- |
| Authentik server and worker | Identity provider at `https://authentik.dejima.men`; direct LAN alias `http://authentik.n100.lan` | Stateless |
| PostgreSQL | Authentik's transactional database | K3s `local-path` PVC on `n100` |
| Backup CronJob | Daily compressed PostgreSQL dump | NFS backup PVC |

Authentik is rendered from the official Helm chart pinned to `2026.8.3`. Its
server and worker run without Kubernetes API credentials; enable a dedicated
service account only when managed Kubernetes outposts are deliberately
configured. PostgreSQL stays on `n100` for database performance, and the daily
backup is retained for 14 days under the dedicated `nfs-client-authentik`
StorageClass:

```text
/Pi-NAS/authentik/
└── authentik-backups/  # daily PostgreSQL dumps
```

## Nextcloud components

| Component | Purpose | Storage |
| --- | --- | --- |
| Nextcloud | HTTPS through the gateway at `https://nextcloud.dejima.men`; direct LAN alias `http://nextcloud.n100.lan` | local config PVC; NFS data PVC |
| MariaDB | Nextcloud's transactional database | K3s `local-path` PVC |
| Redis | Cache and file locking | Ephemeral; no PVC |
| CronJob | Runs `cron.php` every five minutes | Uses Nextcloud PVCs |
| Backup CronJob | Daily compressed MariaDB dump | NFS backup PVC |

MariaDB intentionally uses `local-path`; its live database files never use the
NAS. The Nextcloud stack is pinned to `n100`, keeping MariaDB and all other
storage-related workloads off `p51`'s SD card. A local-path database is tied to
its node, so it is not high availability. Its backup is what makes node
recovery practical.

## NAS layout

The `nfs-client-nextcloud` StorageClass provisions paths below the existing NFS
export `192.168.10.100:/Pi-NAS`:

```text
/Pi-NAS/nextcloud/
├── data/     # user files and versions
└── backups/  # daily MariaDB dumps
```

Nextcloud application files and configuration use a `local-path` PVC on `n100`:
the Nextcloud image changes file ownership during initialization, which an NFS
root-squash export rejects. Only the Nextcloud-specific StorageClass uses this
NAS layout. The existing `nfs-client` StorageClass remains unchanged for all
other applications.

## Mealie components

| Component | Purpose | Storage |
| --- | --- | --- |
| Mealie | HTTPS through the gateway at `https://mealie.dejima.men`; direct LAN alias `http://mealie.n100.lan` | NFS application-data PVC |
| PostgreSQL | Mealie's transactional database | K3s `local-path` PVC |
| Backup CronJob | Daily compressed PostgreSQL dump | NFS backup PVC |

PostgreSQL is pinned to `n100` because it uses `local-path`; its live data is
not stored on the NAS, and the daily database dump is the recovery path. The
Mealie application and its backup job use NFS and may run on any node. The
application prefers a node that does not already run Mealie or Linkwarden. The
application data and database backups use the dedicated
`nfs-client-mealie` StorageClass:

```text
/Pi-NAS/mealie/
├── mealie-data/       # recipe images and Mealie-managed files
└── mealie-backups/    # daily PostgreSQL dumps
```

Mealie has no upstream Helm chart. The deployment is rendered from the pinned
`rtomik/mealie` Helm chart, with the official `ghcr.io/mealie-recipes/mealie`
image pinned in `apps/mealie/values.yaml`. PostgreSQL is a separate pinned
Bitnami Helm source within the same Argo CD Application.

## Vaultwarden components

| Component | Purpose | Storage |
| --- | --- | --- |
| Vaultwarden | Bitwarden-compatible password manager at `https://vaultwarden.dejima.men` | K3s `local-path` data PVC |
| Backup CronJob | Daily SQLite-consistent full-data archive | NFS backup PVC |

Vaultwarden is pinned to `n100`. Its live SQLite database stays on the node's
local disk rather than on NFS. At 03:00 UTC, the backup job uses Vaultwarden's
built-in database backup command and archives that snapshot together with the
rest of `/data`. Backups use the dedicated `nfs-client-vaultwarden`
StorageClass and are retained for 14 days:

```text
/Pi-NAS/vaultwarden/
└── vaultwarden-backups/  # daily full-data archives
```

The gateway terminates TLS before forwarding traffic to Traefik. HTTPS is
required because the Vaultwarden web vault relies on browser cryptography APIs
that are unavailable in an insecure HTTP context.

## IT-Tools components

| Component | Purpose | Storage |
| --- | --- | --- |
| IT-Tools | Browser-based utilities at `https://it-tools.dejima.men`; direct LAN alias `http://it-tools.n100.lan` | None |

IT-Tools is a stateless application pinned to `n100`. Its preferences and
favorites remain in the browser, so the deployment does not require a PVC or a
backup job. The container image is pinned to the upstream stable release rather
than the moving `latest` tag.

## Netdata components

| Component | Purpose | Storage |
| --- | --- | --- |
| Parent | HTTPS through the gateway at `https://netdata.dejima.men`; direct LAN alias `http://netdata.n100.lan` | K3s `local-path` database and state PVCs |
| Child DaemonSet | Host and container metrics collector on every cluster node | Per-node host path for stable identity |
| Kubernetes-state collector | Kubernetes object-state metrics | K3s `local-path` state PVC |

The official Netdata chart is pinned to version `3.7.174`. The parent and
Kubernetes-state pods are pinned to `n100`; child collectors run on every node
and stream their metrics to the parent. Live metric storage remains on
`n100`'s local disk for query performance. It is operational monitoring data,
so it is not included in the NAS backup scheme.

The dashboard is deliberately exposed only on the LAN because Netdata does not
have an authentication middleware configured in this cluster. Cloud claiming
and anonymous telemetry are disabled. The optional service-discovery sidecar is
also disabled so Netdata can use the restricted read-only RBAC in
`apps/netdata/resources/rbac.yaml`, which cannot read Kubernetes Secrets.

Netdata's child collectors require host PID, IPC and network access, host
filesystem mounts, and elevated capabilities to observe each node. These are
expected permissions for the official chart but make Netdata a
security-sensitive cluster component.

## Linkwarden components

| Component | Purpose | Storage |
| --- | --- | --- |
| Linkwarden | Collaborative bookmark manager at `https://linkwarden.dejima.men` | NFS archive PVC |
| PostgreSQL | Linkwarden's transactional database | K3s `local-path` PVC |
| Meilisearch | Full-text search index | K3s `local-path` PVC |
| Backup CronJob | Daily compressed PostgreSQL dump | NFS backup PVC |

PostgreSQL and Meilisearch are pinned to `n100` because they use `local-path`.
The NFS-backed Linkwarden application and backup job may run on any node; the
application prefers a node that does not already run Mealie or Linkwarden.
Link archives and database dumps use the dedicated
`nfs-client-linkwarden` StorageClass, which stores them below the NAS path:

```text
/Pi-NAS/linkwarden/
├── linkwarden-data/     # archived pages and uploads
└── linkwarden-backups/  # daily PostgreSQL dumps
```

PostgreSQL and Meilisearch data remain on `n100`'s local disk for database
and index performance. The `linkwarden-postgresql-backup` CronJob runs daily
at 03:30 UTC, retains 14 days of dumps, and is the recovery path for the
transactional database. The archive PVC must be restored alongside a matching
database dump for a complete recovery.

## Jellyfin components

| Component | Purpose | Storage |
| --- | --- | --- |
| Jellyfin | Media server at `https://jellyfin.dejima.men`; LAN alias `http://jellyfin.n100.lan` | local configuration and cache PVCs; read-only NFS media PVC |
| Backup CronJob | Daily SQLite-consistent configuration backup | NFS backup PVC |

Jellyfin is pinned to `n100`. Its configuration database and cache remain on
the node's local storage for SQLite and transcoding performance. Media is
provided through a dedicated NAS directory and mounted read-only at `/media`,
so the service cannot modify the library:

```text
/Pi-NAS/jellyfin/
├── jellyfin-media/    # media library; add files through the NAS
└── jellyfin-backups/  # daily configuration/database backups
```

The deployment intentionally does not mount GPU devices or enable hardware
transcoding. Direct play works normally; enable hardware acceleration later
only with a suitable Kubernetes device plugin and reviewed device permissions.

## Forgejo components

| Component | Purpose | Storage |
| --- | --- | --- |
| Forgejo | Git forge at `https://forgejo.dejima.men` | K3s `local-path` repository-data PVC |
| PostgreSQL | Transactional database | K3s `local-path` PVC |
| Backup CronJob | PostgreSQL dump plus Forgejo data archive | NFS backup PVC |

Forgejo and PostgreSQL are pinned to `n100`. Live repository data and database
files remain on local storage for Git and PostgreSQL performance. The
`forgejo-backups` PVC uses `nfs-client-forgejo` and provisions under
`/Pi-NAS/forgejo/forgejo-backups`. The service is exposed only through the
TLS-terminating gateway. Initial deployment provides HTTPS Git operations;
Forgejo SSH and Actions are intentionally disabled pending a separate TCP
ingress and runner security design.

## Paperless-ngx components

| Component | Purpose | Storage |
| --- | --- | --- |
| Paperless-ngx | Document management at `https://paperless.dejima.men` | local index/data PVC; NFS document and workflow PVCs |
| PostgreSQL | Transactional database | K3s `local-path` PVC |
| Valkey | Task queue and application cache | K3s `local-path` PVC |
| Backup jobs | PostgreSQL dump and portable document export | NFS backup/export PVCs |

The complete stack is pinned to `n100`. PostgreSQL, Valkey, and Paperless's
rebuildable index/classifier data use node-local storage; documents and the
consume, export, and database-backup areas use `nfs-client-paperless`:

```text
/Pi-NAS/paperless/
├── paperless-media/     # originals, archived documents and thumbnails
├── paperless-consume/   # network document intake
├── paperless-export/    # portable document export
└── paperless-backups/   # daily PostgreSQL dumps
```

The consume directory uses polling because native filesystem notifications are
not reliable on NFS. The public URL is only exposed through the TLS-terminating
gateway; Paperless is configured to trust the forwarded HTTPS scheme.

## Stirling PDF components

| Component | Purpose | Storage |
| --- | --- | --- |
| Stirling PDF | PDF editing and conversion at `https://stirling-pdf.dejima.men`; direct LAN alias `http://stirling-pdf.n100.lan` | K3s `local-path` configuration PVC |

Stirling PDF is pinned to `n100`. Its configuration, including settings saved
from the web UI, persists on `local-path`; uploaded documents, temporary work
files, and logs are deliberately ephemeral. The application does not enable
Stirling's optional account system, so gateway access must be limited to trusted
users. The gateway terminates TLS and the application trusts its forwarded
headers for the public HTTPS route.

## n8n components

| Component | Purpose | Storage |
| --- | --- | --- |
| n8n | Workflow automation at `https://n8n.dejima.men`; LAN alias `http://n8n.n100.lan` | K3s `local-path` data PVC on `n100` |

n8n runs as one replica on `n100` because its SQLite database, workflow data,
credential encryption key, and execution history share a node-local PVC. The
gateway terminates TLS; n8n is configured with the public HTTPS URL and one
trusted proxy hop so editor links and webhook callbacks use the correct URL.
Back up the complete `n8n-data` PVC before a node migration or a destructive
recreation: its generated encryption key is needed to decrypt saved
credentials.

## ntfy components

| Component | Purpose | Storage |
| --- | --- | --- |
| ntfy | Publish/subscribe notifications at `https://ntfy.dejima.men`; LAN alias `http://ntfy.n100.lan` | K3s `local-path` cache PVC on `n100` |

ntfy runs as one replica on `n100`. Its local SQLite cache retains notifications
for 12 hours, allowing clients to receive recent messages after reconnecting;
notifications are otherwise intentionally ephemeral and are not backed up. The
gateway terminates TLS, and ntfy is configured with the public HTTPS URL and
for forwarded headers from Traefik. Anonymous topic access is enabled, so the
gateway must limit access to trusted users before sensitive notification topics
are used.

## Navidrome components

| Component | Purpose | Storage |
| --- | --- | --- |
| Navidrome | Music server at `https://navidrome.dejima.men`; LAN alias `http://navidrome.n100.lan` | local database/cache PVC; read-only NFS music PVC |
| Backup CronJob | Daily SQLite database backup | NFS backup PVC |

Navidrome runs on `n100` because its SQLite database and cache use local-path
storage. Its music library is mounted read-only from the dedicated
`nfs-client-navidrome` StorageClass, which provisions these NAS directories:

```text
/Pi-NAS/navidrome/
├── navidrome-music/    # add music through the NAS
└── navidrome-backups/  # daily SQLite database backups
```

The `navidrome-database-backup` CronJob runs daily at 04:45 UTC and retains 14
SQLite-consistent database backups. It preserves Navidrome accounts, playlists,
ratings, and listening state; the music files are not copied because they are
already on the NAS. The gateway terminates TLS, and Navidrome is configured
with the public HTTPS URL for browser and client links.

## Secrets

Sealed Secrets is deployed in `kube-system`. It decrypts a committed
`SealedSecret` into the `nextcloud-credentials` Secret in the `nextcloud`
namespace. The Helm chart reads that Secret for Nextcloud, MariaDB, and Redis
passwords. The encryption key remains in the cluster; therefore a sealed
credential file is safe to store in this repository but cannot be reused on a
different cluster.

The `nextcloud-username` key is the initial administrator account. The separate
`db-username` key must be `nextcloud`, matching the MariaDB user configured by
the Helm values.

Use the instructions in [apps/nextcloud/README.md](../apps/nextcloud/README.md)
to create the encrypted file. Rotate passwords with the service's own tooling
and update the sealed Secret in the same maintenance window; changing only the
Secret does not change credentials already stored in MariaDB or Nextcloud.

Mealie uses a distinct SealedSecret named `mealie-postgresql-credentials` in
the `mealie` namespace. Its `username` is `mealie`; the `password` key is used
by both Mealie and PostgreSQL, while `postgres-password` is reserved for the
PostgreSQL administrator. Generate it with the instructions in
[apps/mealie/README.md](../apps/mealie/README.md). Rotating either database
password requires changing the password in PostgreSQL as well as updating the
SealedSecret.

Forgejo uses separate SealedSecrets for the `forgejo-admin-credentials` and
`forgejo-postgresql-credentials` Secrets in the `forgejo` namespace. The
committed secrets contain generated values encrypted for this cluster. Retrieve
the initial administrator password or reseal replacement credentials with the
commands in [apps/forgejo/README.md](../apps/forgejo/README.md).

Paperless uses `paperless-credentials` in the `paperless` namespace for its
database roles, Django secret key, and initial administrator account. The
committed SealedSecret contains generated values encrypted for this cluster.
Retrieve the initial administrator password or reseal replacement credentials
with the commands in
[apps/paperless/README.md](../apps/paperless/README.md).

## Backups and recovery

The `nextcloud-db-backup` CronJob runs daily at 02:30 UTC. It runs
`mariadb-dump --single-transaction --default-character-set=utf8mb4`, compresses
the result, and retains 14 daily dumps in `/Pi-NAS/nextcloud/backups`.

For a complete Nextcloud recovery, retain all of the following:

1. a MariaDB dump;
2. the NAS `config` directory, including custom apps;
3. the NAS `data` directory.

Before a planned consistent filesystem backup, enable Nextcloud maintenance
mode, copy `config` and `data`, dump MariaDB, and then disable maintenance mode.
Test restores periodically. Backups on this same NAS do not protect against NAS
failure; replicate them off the NAS or use NAS snapshots plus an offsite copy.

## Mealie backups and recovery

The `mealie-postgresql-backup` CronJob runs daily at 02:45 UTC. It writes a
gzip-compressed plain SQL dump and retains 14 daily dumps in
`/Pi-NAS/mealie/mealie-backups`. A complete Mealie recovery requires both a
database dump and the `/Pi-NAS/mealie/mealie-data` directory. Restore the
database with `gunzip -c <dump> | psql` against a stopped or maintenance-mode
Mealie deployment, then restore the application-data directory.

## Vaultwarden backups and recovery

The `vaultwarden-backup` CronJob creates
`vaultwarden-<UTC timestamp>.tar.gz` each day and retains 14 archives. Each
archive excludes the live SQLite/WAL files and includes a consistent
`db_<timestamp>.sqlite3` snapshot plus attachments, sends, configuration and
RSA keys from the data directory.

To recover, stop Vaultwarden, extract an archive into its data PVC, rename the
included `db_<timestamp>.sqlite3` file to `db.sqlite3`, and make sure no stale
`db.sqlite3-wal` or `db.sqlite3-shm` files remain before starting Vaultwarden.

## Jellyfin backups and recovery

The `jellyfin-config-backup` CronJob runs daily at 04:15 UTC. It uses SQLite's
online backup command for `jellyfin.db`, archives the remaining configuration,
and retains 14 backups in `/Pi-NAS/jellyfin/jellyfin-backups`. To recover,
stop Jellyfin, restore `jellyfin.db` into the configuration PVC's `data`
directory, extract `config.tar.gz` over the configuration PVC, then start the
deployment. Media is not duplicated by this job because the source library is
already on the NAS; protect it with NAS snapshots and an offsite copy.

## Navidrome backups and recovery

The `navidrome-database-backup` CronJob runs daily at 04:45 UTC and retains 14
SQLite-consistent backups in `/Pi-NAS/navidrome/navidrome-backups`. To recover,
stop Navidrome, replace `navidrome.db` on the `navidrome-data` PVC with a
selected backup, remove stale `navidrome.db-wal` and `navidrome.db-shm` files,
then start the deployment. Music remains on the NAS and is deliberately not
duplicated by this job.

## Forgejo backups and recovery

The `forgejo-backup` CronJob runs daily at 04:30 UTC. It creates a PostgreSQL
dump, archives it with the Forgejo data directory, and retains 14 archives in
`/Pi-NAS/forgejo/forgejo-backups`. To recover, stop Forgejo, restore the
database dump to PostgreSQL, extract the data directory to the `forgejo-data`
PVC, then start Forgejo. Use NAS snapshots and an offsite copy as protection
against NAS failure.

## Paperless-ngx backups and recovery

The `paperless-postgresql-backup` CronJob runs daily at 03:15 UTC, writes a
compressed SQL dump, and retains 14 daily dumps. At 03:45 UTC,
`paperless-document-export` updates Paperless's portable export with database
metadata, documents, and thumbnails.

For recovery, stop Paperless ingestion, restore the latest portable export with
Paperless's `document_importer`, and start the deployment again. The SQL dumps
provide a second database-specific recovery path. Protect against NAS failure
with NAS snapshots and an offsite copy; the export and SQL dumps share the same
NAS as the live documents.
