# Radarr

Radarr manages movies at `http://radarr.n100.lan`. The shared
[media package](../README.md) deploys it into the `jellyfin`
namespace and mounts the existing `jellyfin-media`
PVC at `/media`. The root folder is `/media/movies`; intake is `/media/staging`.

The single replica uses Recreate updates on `n100`, with a 5 Gi
`radarr-config` PVC on `local-path` for SQLite. The pinned LinuxServer image
initializes as root and runs Radarr with PUID/PGID 1000,
`TZ=America/Vancouver`, and `UMASK=002`. A non-root init container creates
missing media directories without changing NAS ownership.

Complete authentication setup and configure naming, indexers, download clients,
and quality profiles using [the media setup guide](../../../docs/media-stack.md).
Configure scheduled backups under Settings → General and download/copy backups
off-node; the Jellyfin backup job does not include this PVC. Restore through
Radarr's System → Backup with the same image version and media paths.
