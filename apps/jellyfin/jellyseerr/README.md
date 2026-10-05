# Jellyseerr / Seerr

Deployed through the shared [media package](../README.md) and the
existing `jellyfin` Argo CD Application.

The request portal runs the pinned Seerr image, the maintained successor to
Jellyseerr and Overseerr, under the `jellyseerr` Deployment/Service name.
It is available at `https://jellyseerr.dejima.men` through the TLS-terminating
gateway and at `http://jellyseerr.n100.lan` on the LAN. Provision DNS and the
gateway route before using the public address.

The single replica runs as UID/GID 1000 on `n100`, uses Recreate updates, and
stores its configuration/SQLite database in the 5 Gi `jellyseerr-config`
`local-path` PVC at `/app/config`. This image uses Kubernetes
`runAsUser`/`runAsGroup`, not PUID/PGID environment variables. It mounts the
existing `jellyfin-media` claim read-only at `/media` for consistent paths,
although the portal works through APIs and does not need file access.

In the first-run wizard, connect Jellyfin at `http://jellyfin:8096`, Sonarr at
`http://sonarr:8989`, and Radarr at `http://radarr:7878`. Use the appropriate
API keys, select quality profiles and root folders, and review request/approval
permissions. Use `https://jellyfin.dejima.men` as the external Jellyfin URL.
See [the media setup guide](../../../docs/media-stack.md).

The existing Jellyfin backup does not cover Seerr. Back up the entire config
PVC while this Deployment is stopped in an operator-managed maintenance window;
Argo CD self-heal must also be accounted for when temporarily stopping it.
Restore the full directory with UID/GID 1000 and the same pinned image before
restarting. Keep an off-node copy.

Upstream: [Seerr deployment documentation](https://docs.seerr.dev/getting-started/docker/)
and [the Seerr announcement](https://docs.seerr.dev/blog/seerr-release/).
