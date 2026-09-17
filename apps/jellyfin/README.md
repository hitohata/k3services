# Jellyfin

Jellyfin runs on `n100` and is available through the TLS-terminating gateway at
`https://jellyfin.dejima.men` and directly on the LAN at
`http://jellyfin.n100.lan`. Complete the first-run administrator setup in the
web interface.

The `jellyfin-media` PVC is read-only inside the pod. It creates the NAS path
`/Pi-NAS/jellyfin/jellyfin-media`; add media to that directory through the NAS,
then create Jellyfin libraries using paths below `/media`.

Jellyfin configuration and cache use `local-path` on `n100` for SQLite and
transcoding performance. `jellyfin-config-backup` runs daily at 04:15 UTC. It
uses SQLite's online backup command for `jellyfin.db` and archives the remaining
configuration files, retaining 14 days of backups on the NAS.

Hardware transcoding is intentionally not enabled: the deployment does not
grant access to host GPU devices. Enable it only after installing an appropriate
Kubernetes device plugin and confirming the required device permissions.
