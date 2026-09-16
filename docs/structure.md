# System structure

## GitOps layout

`root-app/apps.yaml` is the Argo CD app-of-apps entry point. It defines each
Argo CD `Application`, which in turn deploys an application or infrastructure
component from this repository or an external Helm chart.

```text
root-app/apps.yaml
├── infrastructure/nfs-provisioner     NFS dynamic provisioning
├── sealed-secrets Helm chart           encrypted-secret controller
└── apps/nextcloud/
    ├── values.yaml                     Nextcloud Helm configuration
    └── secrets/                        encrypted Nextcloud credentials
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
| Nextcloud | Web application at `http://nextcloud.n100.lan` | NFS config and data PVCs |
| MariaDB | Nextcloud's transactional database | K3s `local-path` PVC |
| Redis | Cache and file locking | Ephemeral; no PVC |
| CronJob | Runs `cron.php` every five minutes | Uses Nextcloud PVCs |
| Backup CronJob | Daily compressed MariaDB dump | NFS backup PVC |

MariaDB intentionally uses `local-path`; its live database files never use the
NAS. A local-path database is tied to the node that owns its volume, so it is
not high availability. Its backup is what makes node recovery practical.

## NAS layout

The `nfs-client-nextcloud` StorageClass provisions paths below the existing NFS
export `192.168.10.100:/Pi-NAS`:

```text
/Pi-NAS/nextcloud/
├── config/   # Nextcloud installation, configuration, and custom apps
├── data/     # user files and versions
└── backups/  # daily MariaDB dumps
```

Only the Nextcloud-specific StorageClass uses this layout. The existing
`nfs-client` StorageClass remains unchanged for all other applications.

## Secrets

Sealed Secrets is deployed in `kube-system`. It decrypts a committed
`SealedSecret` into the `nextcloud-credentials` Secret in the `nextcloud`
namespace. The Helm chart reads that Secret for Nextcloud, MariaDB, and Redis
passwords. The encryption key remains in the cluster; therefore a sealed
credential file is safe to store in this repository but cannot be reused on a
different cluster.

Use the instructions in [apps/nextcloud/README.md](../apps/nextcloud/README.md)
to create the encrypted file. Rotate passwords with the service's own tooling
and update the sealed Secret in the same maintenance window; changing only the
Secret does not change credentials already stored in MariaDB or Nextcloud.

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
