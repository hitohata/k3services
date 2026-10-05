# Sonarr

CPU reservation is 50m with a two-core limit. This keeps the media suite
schedulable on `n100` while allowing bursts during imports and scans.

Sonarr manages TV and anime at `http://sonarr.n100.lan`. The shared
[media package](../README.md) deploys it into the `jellyfin`
namespace to share the existing `jellyfin-media`
PVC at `/media`. The root folder is `/media/tv`; intake is `/media/staging`.

The single replica uses Recreate updates and is pinned to `n100`. Its 5 Gi
`sonarr-config` PVC uses `local-path` for the SQLite database. The pinned
LinuxServer image initializes as root and runs Sonarr with PUID/PGID 1000,
`TZ=America/Vancouver`, and `UMASK=002`. A non-root init container creates
missing media directories without changing NAS ownership.

Complete authentication setup and configure naming, indexers, download clients,
and quality profiles using [the media setup guide](../../../docs/media-stack.md).
Configure scheduled backups under Settings → General and download/copy backups
off-node; the Jellyfin backup job does not include this PVC. Restore through
Sonarr's System → Backup with the same image version and media paths.
