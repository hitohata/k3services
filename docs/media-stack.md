# Kubernetes media suite

Jellyfin is joined by Sonarr, Radarr, Bazarr, and Jellyseerr's maintained
successor Seerr. All five are bundled in the Kustomize package
`apps/jellyfin`, managed by the existing `jellyfin` Argo CD Application
in `root-app/apps.yaml`. They run in the existing `jellyfin` namespace and use Kubernetes Services
for communication. No Docker Compose network, host ports, or Docker daemon is
required.

| Service | Responsibility |
| --- | --- |
| Jellyfin | Playback, library browsing, posters and metadata |
| Sonarr | TV/anime import, organization, and renaming |
| Radarr | Movie import, organization, and renaming |
| Bazarr | Subtitle search and download |
| Jellyseerr / Seerr | User requests sent to Sonarr/Radarr |

The package provides one sync and health overview for the suite while retaining
separate Deployments and configuration PVCs. Updating one image rolls only its
Deployment. Render the entire package with `kubectl kustomize apps/jellyfin`.
Jellyfin's own manifests are in `apps/jellyfin/server/`; its companions are in
the adjacent `sonarr/`, `radarr/`, `bazarr/`, and `jellyseerr/` directories.

## Storage and permissions

The existing `jellyfin-media` PVC remains owned by the Jellyfin Application.
Every service mounts it once at `/media`; Sonarr, Radarr, and Bazarr can write,
while Jellyfin and Seerr mount it read-only. On the NAS:

```text
/Pi-NAS/jellyfin/jellyfin-media/
├── staging/
├── movies/
└── tv/
```

The writer Deployments initialize missing directories using UID/GID 1000.
Ensure the NAS permits that user/group to create and modify files in this
directory. Existing library content is not moved or renamed automatically.
The init containers fail with a permission message if required paths are not
writable; fix access on the NAS rather than disabling NFS root squash or
recursively changing ownership blindly.

Use the same UID/GID for downloaders and group-writable files/directories.
All library and staging directories must share one filesystem with hardlink
support. Do not introduce separate PVCs, subPath mounts, NAS exports, or ZFS
datasets beneath those paths. A shared mount cannot make hardlinks cross
filesystem boundaries.

All five applications keep live databases on `local-path` on `n100`. Each
companion has its own 5 Gi config PVC and a single Recreate replica. Jellyfin's
existing image, media/config/cache claims, and backup job are preserved.

## Endpoints and first-run setup

| Application | Browser address | Internal URL in the jellyfin namespace |
| --- | --- | --- |
| Jellyfin | `https://jellyfin.dejima.men` | `http://jellyfin:8096` |
| Sonarr | `http://sonarr.n100.lan` | `http://sonarr:8989` |
| Radarr | `http://radarr.n100.lan` | `http://radarr:7878` |
| Bazarr | `http://bazarr.n100.lan` | `http://bazarr:6767` |
| Jellyseerr / Seerr | `https://jellyseerr.dejima.men` | `http://jellyseerr:5055` |

From another namespace use, for example, `sonarr.jellyfin.svc.cluster.local`.
Service ports stay internal; Traefik exposes the named hosts. Add LAN DNS
records to the existing Traefik endpoint and configure the gateway DNS/TLS
route for `jellyseerr.dejima.men`. Arr administration has no public-domain
Ingress rule. LAN hostnames alone do not enforce network isolation; keep them
off the public gateway and enable authentication in every application.

Complete the first-run wizards and store API keys in the applications. No
plaintext credentials or generated sealed secrets are included in Git.
Manifest deployment does not configure naming rules or integration API keys;
save the settings below in each web UI, where they persist on the config PVCs.

## Sonarr naming

Under Settings → Media Management, show advanced settings, enable Rename
Episodes and Use Hardlinks instead of Copy, and add `/media/tv` as the root
folder. Enable season folders when adding series.

| Setting | Value |
| --- | --- |
| Anime Episode Format | `{Series TitleYear} - S{season:00}E{episode:00} - {absolute:000} - {Episode Title} [{Quality Full}]` |
| Standard Episode Format | `{Series TitleYear} - S{season:00}E{episode:00} - {Episode Title} [{Quality Full}]` |
| Series Folder Format | `{Series TitleYear} [tvdbid-{TvdbId}]` |
| Season Folder Format | `Season {season:00}` |

Sonarr uses zero-pattern padding (`00` and `000`), not `02`/`03`.
These values give the requested `S01E02 - 003` and `Season 01` output.
Select Anime as the series type for anime and Standard for ordinary TV.
Absolute numbers depend on upstream metadata. Review matching and episode
ordering, particularly for anime and specials.

## Radarr naming

Under Settings → Media Management, enable Rename Movies and Use Hardlinks
instead of Copy. Add `/media/movies` as the root folder.

| Setting | Value |
| --- | --- |
| Standard Movie Format | `{Movie TitleYear} [{Quality Full}]` |
| Movie Folder Format | `{Movie TitleYear} [tmdbid-{TmdbId}]` |

## Jellyfin, subtitles, and requests

In Jellyfin, create Movies at `/media/movies` and Shows at `/media/tv`.
Exclude staging. Enable the desired metadata providers and language; install
and configure the TVDB provider if needed for Sonarr's IDs and episode ordering.
Keep write-to-media NFO/artwork options disabled because Jellyfin mounts media
read-only. Schedule library scans for NAS files where change notifications may
not propagate. Names and IDs improve matching but cannot guarantee correct
results for every provider disagreement.

In Bazarr, connect Sonarr at host `sonarr`, port `8989`, and Radarr at host
`radarr`, port `7878`, with their API keys from Settings → General.
Leave path mappings empty. Configure subtitle providers and language profiles
and assign profiles to series/movies to enable searches.

In Seerr's setup wizard, select Jellyfin and use the internal URLs above.
Set Jellyfin's external URL to `https://jellyfin.dejima.men`. Add Sonarr and
Radarr with API keys, choose default servers and quality profiles, and select
`/media/tv` and `/media/movies` respectively. Configure request approval and
user permissions before sharing the portal.

## Intake and automation

A downloader and indexers are not included in this five-service suite.
Configure them in Sonarr/Radarr and enable Completed Download Handling for
automatic imports. A future Kubernetes downloader should run in `jellyfin`,
mount the existing `jellyfin-media` PVC once at `/media`, and report completed
paths under `/media/staging`. For external downloaders, use the same exported
filesystem and reported paths. Do not create a second dynamically provisioned
media claim: it would point to different data.

Files placed arbitrarily in staging are not automatically watched/imported.
Use Manual/Interactive Import for rips and initial files, or integrate a
supported downloader. Use Library Import for existing organized content,
then review a rename before applying it. Torrent imports can hardlink while
retaining the source for seeding; other imports can move files atomically.

## Operations and recovery

The single `jellyfin` Application manages the shared PVC and all five
Deployments. Pods wait for their claims to bind; no additional Application
ordering is needed. The Application name, namespace, resource names, and
existing PVC identities are preserved.

The separate companion Applications from the initial draft have been removed
from `root-app/apps.yaml`. No live sync was performed during this work.
If that earlier draft was deployed separately, orphan its companion resources
when removing those Applications before adopting them into `jellyfin`; do not
cascade-delete their workloads or PVCs. Do not manage the same resources through
both the package and standalone Applications.

Startup probes allow up to ten minutes, readiness probes gate Service traffic,
and liveness probes restart stalled containers. Bazarr uses TCP probes because
web authentication can protect or redirect its UI. Resource requests reserve
1.5 Gi total memory for the four companions in addition to Jellyfin; ensure
`n100` has spare capacity. LinuxServer containers initialize as root and drop
the application to UID/GID 1000. Seerr runs entirely as UID/GID 1000.

The existing daily Jellyfin backup covers only Jellyfin. Enable the native
scheduled backups in Sonarr, Radarr, and Bazarr and keep off-node copies.
For Seerr, take a stopped, full-config backup during a planned maintenance
window, accounting for Argo CD self-heal before scaling down. A live file copy
of SQLite databases is not a consistent backup. Restore using the same pinned
image and original paths, preserving ownership. Protect media separately with
NAS snapshots and an offsite copy. This change does not add companion backup
CronJobs.

Review release notes and take configuration backups before changing pinned
image versions. After sync, verify directory permissions, finish application
setup, import a sample file, check that hardlinked source/destination files
have the same inode, and confirm Jellyfin metadata and Bazarr subtitles.
No live-cluster mutations are required for local manifest validation.

## References

- [Servarr Docker/storage guide](https://wiki.servarr.com/docker-guide)
- [Sonarr settings](https://wiki.servarr.com/sonarr/settings)
- [Radarr settings](https://wiki.servarr.com/radarr/settings)
- [LinuxServer user IDs](https://docs.linuxserver.io/general/understanding-puid-and-pgid/)
- [Seerr deployment](https://docs.seerr.dev/getting-started/docker/)
