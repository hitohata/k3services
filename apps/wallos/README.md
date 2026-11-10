# Wallos retirement

Firefly III replaces Wallos with a fresh installation. Existing Wallos data is
intentionally discarded; no migration, final backup, or rollback copy is made.

The existing `wallos` Argo CD Application stays in place to reconcile cleanup.
Its automated prune removes the old Deployment, Service, Ingress, backup
CronJob, and the `wallos-db`, `wallos-logos`, and `wallos-backups` PVCs.
`allowEmpty: true` permits removing all ordinary resources. Removing the
Application itself would orphan resources because it has no deletion finalizer.

The database and logos use local-path volumes on `n100`; their existing PV
reclaim policies determine file deletion (normally Delete for local-path).
The backup PV uses Retain, so PVC removal alone does not erase NAS archives.
The PostSync `wallos-backups-cleanup` hook mounts only
`192.168.10.100:/Pi-NAS/wallos/wallos-backups` and deletes all contents after
pruning completes. UID/GID 82 matches the former backup job. The NAS must allow
that account to traverse and delete those files. A failed hook remains visible
for investigation; successful hook Jobs delete themselves. A later sync may
repeat this idempotent cleanup. The mount directory and released retained PV
metadata may remain, but successful cleanup leaves no backup files.

The `nfs-client-wallos` StorageClass is also removed. Other service data and NAS
paths are unchanged. Cleanup does not wait for Firefly III to become healthy;
prepare its SealedSecret, DNS, and gateway route before cutover. See
[the Firefly III guide](../firefly-iii/README.md).

These are GitOps changes only. Actual resource and data deletion happens when
Argo CD synchronizes them; no live-cluster operations were performed here.
