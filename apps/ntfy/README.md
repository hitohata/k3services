# ntfy

ntfy is a self-hosted publish/subscribe notification service. It is available
through the TLS-terminating gateway at `https://ntfy.dejima.men` and directly
on the LAN at `http://ntfy.n100.lan`.

The service runs as a single replica on `n100`. Its SQLite cache database is
stored on the `ntfy-cache` `local-path` PVC, which retains messages for 12
hours so clients can receive recent notifications after reconnecting. The cache
is operational state rather than a backup source; notifications are ephemeral.

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

## Longhorn migration in progress

This first stage deliberately sets replicas to zero so the SQLite cache can
be copied consistently. The source `ntfy-cache` claim stays declared and is
protected with `Prune=false`. The separate `ntfy-cache-ha` claim uses the
non-default two-replica Longhorn class; do not switch the Deployment or start
it until the stopped cache has been backed up independently and restored.
Rollback at this stage is to restore replicas to one with the original claim.
The application image and external routes are unchanged.

The independent `ntfy-backups` NFS claim uses `nfs-client-ntfy`, provisioning
`/Pi-NAS/ntfy/ntfy-backups`. Migration archives are retained there; no automated
retention/deletion is configured during the first migration stage.
