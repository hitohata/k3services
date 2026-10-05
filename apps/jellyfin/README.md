# Jellyfin

The existing `jellyfin` Argo CD Application deploys this Kustomize package,
including Jellyfin and its four companion services, into the `jellyfin`
namespace.

```text
apps/jellyfin/
├── README.md
├── kustomization.yaml
├── server/       # Jellyfin deployment, storage, ingress, and backup
├── sonarr/       # TV/anime organization
├── radarr/       # Movie organization
├── bazarr/       # Subtitle fetching
└── jellyseerr/   # Seerr request portal
```

Render the whole suite with `kubectl kustomize apps/jellyfin`. Each service
remains a separate Deployment with its own configuration PVC and Service;
one Argo CD sync manages the package, and changing one Deployment rolls only
that service. These are companion services, not containers sharing a Pod.
Do not deploy the child directories as additional Argo CD Applications.

The Application name, resource names, and existing PVC identities are
preserved. Jellyfin's own manifests are in `server/`; companion manifests and
their service-specific READMEs are in the adjacent directories.

Jellyfin runs on `n100` and is available through the TLS-terminating gateway at
`https://jellyfin.dejima.men` and directly on the LAN at
`http://jellyfin.n100.lan`. Complete the first-run administrator setup in the
web interface.

The `jellyfin-media` PVC is read-only inside the pod. It creates the NAS path
`/Pi-NAS/jellyfin/jellyfin-media`; add media to that directory through the NAS,
then create Jellyfin libraries using paths below `/media`.

Sonarr, Radarr, and Bazarr share this claim read-write in the `jellyfin`
namespace. They organize movies at `/media/movies` and shows at `/media/tv`,
with intake at `/media/staging`. Configure the corresponding Jellyfin Movies
and Shows libraries, excluding staging. Existing files are not moved
automatically. See [the media stack guide](../../docs/media-stack.md) for
naming, permissions, metadata, and the Jellyseerr/Seerr request portal.

Jellyfin configuration and cache use `local-path` on `n100` for SQLite and
transcoding performance. `jellyfin-config-backup` runs daily at 04:15 UTC. It
uses SQLite's online backup command for `jellyfin.db` and archives the remaining
configuration files, retaining 14 days of backups on the NAS.

Hardware transcoding is intentionally not enabled: the deployment does not
grant access to host GPU devices. Enable it only after installing an appropriate
Kubernetes device plugin and confirming the required device permissions.
