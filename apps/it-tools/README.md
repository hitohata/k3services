# IT-Tools

IT-Tools provides browser-based developer and administration utilities at
`https://it-tools.dejima.men` and directly on the LAN at
`http://it-tools.n100.lan`. It is stateless, pinned to `n100`, and does not
require persistent storage or backups.

Its container image is pinned to a stable upstream release. The CPU request is
5m because observed idle use is approximately 1m; its memory request and limit
remain 32 Mi and 128 Mi respectively.
