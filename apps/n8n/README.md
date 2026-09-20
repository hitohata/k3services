# n8n

n8n is deployed as a single persistent workflow-automation instance. It is
available through the TLS-terminating gateway at
`https://n8n.dejima.men` and directly on the LAN at `http://n8n.n100.lan`.

The n8n data directory is stored on a `local-path` PVC pinned to `n100`. It
contains workflows, credentials, the SQLite database, and n8n's generated
encryption key. Keep this PVC together with a backup before moving or
recreating the workload; losing it makes saved credentials unreadable.

The public URL is configured explicitly for editor links and webhooks. The
gateway terminates TLS and n8n trusts one forwarded-proxy hop, so webhook URLs
continue to use HTTPS even though Traefik connects to the pod over HTTP.
