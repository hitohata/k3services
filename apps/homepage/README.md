# Homepage

Homepage provides the service dashboard at `https://homepage.dejima.men` and
`http://homepage.n100.lan`. Its configuration is stored in `settings.yaml`,
`services.yaml`, and `bookmarks.yaml` and is mounted into the pinned Homepage
container image.

The Productivity group includes Firefly III for personal finance and recurring
transactions at `https://firefly-iii.dejima.men`.

The Administration group links to the Longhorn replicated-storage guide.
Longhorn's management UI remains internal and is accessed with a local
port-forward; the dashboard does not expose a storage administration endpoint.

The Media group includes Jellyfin, Sonarr, Radarr, Bazarr, and Jellyseerr/Seerr.
The Arr administration links use LAN hostnames; see
[the media setup guide](../../docs/media-stack.md).
