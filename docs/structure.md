# System structure

## GitOps layout

`root-app/apps.yaml` is the Argo CD app-of-apps entry point. It defines each
Argo CD `Application`, which in turn deploys an application or infrastructure
component from this repository or an external Helm chart.

```text
root-app/apps.yaml
├── infrastructure/nfs-provisioner     NFS dynamic provisioning
├── sealed-secrets Helm chart           encrypted-secret controller
├── apps/nextcloud/
│   ├── values.yaml                     Nextcloud Helm configuration
│   └── secrets/                        encrypted Nextcloud credentials
└── apps/mealie/
    ├── values.yaml                     Mealie Helm configuration
    ├── postgresql-values.yaml          Mealie PostgreSQL Helm configuration
    ├── resources/                      backup PVC and CronJob
    └── secrets/                        encrypted PostgreSQL credentials
```

The root application references the upstream Nextcloud Helm chart and the
app-specific `apps/nextcloud/values.yaml` through Argo CD multi-source support.
This requires Argo CD 2.6 or later. The release is pinned to chart version
`9.2.5`. Updating that version is an intentional maintenance change: read the
chart release notes and upgrade Nextcloud by no more than one major version at a
time.

## Nextcloud components

| Component | Purpose | Storage |
| --- | --- | --- |
| Nextcloud | Web application at `http://nextcloud.n100.lan` | local config PVC; NFS data PVC |
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
| Mealie | Recipe, meal-planning, and shopping-list web application at `http://mealie.n100.lan` | NFS application-data PVC |
| PostgreSQL | Mealie's transactional database | K3s `local-path` PVC |
| Backup CronJob | Daily compressed PostgreSQL dump | NFS backup PVC |

The Mealie application and PostgreSQL are both pinned to `n100`. PostgreSQL is
deliberately not stored on the NAS; its live data is tied to `n100`, and the
daily database dump is the recovery path. The Mealie application data and the
database backups use the dedicated `nfs-client-mealie` StorageClass:

```text
/Pi-NAS/mealie/
├── mealie-data/       # recipe images and Mealie-managed files
└── mealie-backups/    # daily PostgreSQL dumps
```

Mealie has no upstream Helm chart. The deployment is rendered from the pinned
`rtomik/mealie` Helm chart, with the official `ghcr.io/mealie-recipes/mealie`
image pinned in `apps/mealie/values.yaml`. PostgreSQL is a separate pinned
Bitnami Helm source within the same Argo CD Application.

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
