# ntfy

ntfy is a self-hosted publish/subscribe notification service. It is available
through the TLS-terminating gateway at `https://ntfy.dejima.men` and directly
on the LAN at `http://ntfy.n100.lan`.

The service runs as a single replica on n100 using its original `ntfy-cache`
local-path claim. The attempted Longhorn/p41 cutover was rolled back after
the USB SSD disappeared again before ntfy started. Both claims remain declared
and protected from pruning. The original PV reclaim policy was separately
changed to Retain. Do not delete either claim during investigation.
The cache retains messages for 12 hours; backups do not extend live retention.

ntfy is configured to run behind Traefik and advertises the HTTPS public URL in
links and subscription metadata. The current configuration allows anonymous
topic access. Restrict the TLS gateway to trusted users before using topic
names for sensitive notifications, or add ntfy authentication as a separately
managed credential change.

The image is pinned to ntfy 2.34.0. Review the
[upstream release notes](https://docs.ntfy.sh/releases/) before updating it.
The upgrade from 2.14.0 migrates the SQLite cache automatically. Copy the cache
while the service is stopped before upgrading if its retained messages matter;
restore that copy with the old image for rollback to 2.14.0. After syncing,
verify publishing, subscriptions, and replay of cached messages. Reconnects
using `since=<message ID>` may replay messages from the same second; custom
subscribers should deduplicate by message ID. Cache replays are now size- and
bandwidth-limited, so unusually large polls may return HTTP 429.

## Migration and recovery

On 2026-11-19 the server was stopped through GitOps before archiving the
complete cache directory to the independent NAS claim. The archive was restored
on a separate host, SQLite `integrity_check` returned `ok`, and the restored
cache matched the source byte for byte. The verified NAS archive was then
restored onto the new Longhorn volume before attempting to start ntfy. The p41 USB SSD then failed again with UAS
recovery and I/O errors, stopping K3s. The ntfy container never started on p41;
the Deployment was returned to n100 and its unchanged original cache. The
Longhorn claim and NAS archive are retained. Image 2.34.0 is
unchanged and its registry manifest supports AMD64 and ARM64.

- Original cache SHA256: `de046477270c252a400c6031ad5082a027ad6bc870f99f505bf589dc4d0ee8f4`
- Pre-migration archive: `/Pi-NAS/ntfy/ntfy-backups/pre-longhorn-20261119.tar.gz`
- Archive SHA256: `090b96316d46d43a3d91f25a25e684548850c3332771207b0d0c4499a539a363`

The `ntfy-backups` NFS PVC uses retained `nfs-client-ntfy` storage. A daily
SQLite online backup runs at 05:30 UTC and keeps 14 days of timestamped cache
archives. The fixed pre-migration archive is excluded from automatic retention.
The CronJob is currently **suspended** because the active application was
rolled back to local-path while its backup template references `ntfy-cache-ha`.
Do not resume it until the cache claim and application placement agree.
The job uses required Pod affinity to the running ntfy Pod, allowing it to
mount the same RWO volume on the current application node, including after
reattachment. If ntfy is absent, the job stays Pending rather than binding to
an arbitrary host. It never attaches the database to two nodes concurrently.
Snapshots and SSD replication are not substitutes for this NAS backup. Protect
the NAS with independent snapshots/offsite backups as appropriate.

For restore, first commit replicas zero and suspend the backup CronJob. Wait
for ntfy and any active backup job to stop. With the cache volume mounted only
by a recovery Pod, restore a selected archive into an empty directory, check
SQLite integrity, and replace the full cache directory including any SQLite
sidecar files as a coordinated stopped operation. Never restore over a live
SQLite database. Start ntfy and verify health, publishing, subscriptions and
cached replay before resuming backups.

For rollback, stop ntfy and backup jobs through GitOps, preserve a fresh archive
of the Longhorn cache, and decide which state to restore. Switching directly
to `ntfy-cache` recovers only pre-migration state and loses messages accepted
since cutover. To preserve current messages, copy a stopped, checked snapshot
back to the old claim first. Restore the n100 nodeSelector and old claimName,
then start one replica. Keep both claims until rollback is no longer needed.

Controlled cross-node reattachment passed for the disposable storage pilot.
An actual n100 outage, ingress recovery and fencing have not been accepted.
The earlier USB disappearance on p41 recovered after a port change and reboot;
its root cause is unconfirmed. Observe USB/I/O errors and replica health before
expanding to another application. This small migration is not expected to
significantly reduce n100 load.
