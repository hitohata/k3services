# Navidrome

Navidrome is a self-hosted music server available through the TLS-terminating
gateway at `https://navidrome.dejima.men` and directly on the LAN at
`http://navidrome.n100.lan`. Complete the first-run administrator setup in the
web interface.

The service runs on `n100`. Its SQLite database, user accounts, playlists,
ratings, and cache are stored on the `navidrome-data` `local-path` PVC. The
`navidrome-music` PVC mounts `/Pi-NAS/navidrome/navidrome-music` read-only at
`/music`; add music to that NAS directory, then let Navidrome scan it.

`navidrome-database-backup` creates a SQLite-consistent database backup daily
at 04:45 UTC and retains 14 backups in
`/Pi-NAS/navidrome/navidrome-backups`. To restore, stop Navidrome, replace
`/data/navidrome.db` with a selected backup, remove any stale SQLite WAL and
SHM files, then start the deployment. The music library is not duplicated by
the backup job because it already resides on the NAS.

The image is pinned to Navidrome 0.64.1. It receives the public HTTPS URL so
clients and links use the gateway address. Anonymous insights collection is
disabled. Review upstream release notes before updating it.
