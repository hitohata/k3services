# Bazarr

CPU reservation is 50m with a two-core limit. This keeps the media suite
schedulable on `n100` while allowing bursts during imports and scans.

Deployed through the shared [media package](../README.md) and the
existing `jellyfin` Argo CD Application.

Bazarr fetches subtitles and is available at `http://bazarr.n100.lan`. It runs
in the `jellyfin` namespace, sharing the existing `jellyfin-media` PVC at
`/media` read-write so subtitles can be saved beside movies and episodes.

The single replica uses Recreate updates on `n100`. Configuration and SQLite
use the 5 Gi `bazarr-config` PVC on `local-path`. The pinned LinuxServer image
initializes as root and runs Bazarr with PUID/PGID 1000,
`TZ=America/Vancouver`, and `UMASK=002`. A non-root init container creates
missing media directories without changing NAS ownership. Probes use TCP so
enabling authentication does not cause probe failures.

Enable authentication, connect `sonarr:8989` and `radarr:7878` using their
API keys, configure subtitle providers and languages, and assign language
profiles. No path mappings are needed. See
[the media setup guide](../../../docs/media-stack.md).

Configure Bazarr's scheduled backups and download/copy them off-node; the
Jellyfin backup job does not include this PVC. Restore through Bazarr's backup
interface using the same image version and paths.
