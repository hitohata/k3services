# Vaultwarden

Vaultwarden is deployed from the manifests in this directory and is pinned to
`n100`. The gateway must route `vaultwarden.dejima.men` to Traefik and terminate
TLS; the web vault and current Bitwarden clients require HTTPS.

The live data PVC uses `local-path` because it contains SQLite files. A daily
job creates a consistent database snapshot, archives the full data directory to
the NAS, and retains 14 backups.

## First account

Signup is enabled initially so the first account can be registered. Register it
immediately after the first successful sync, then change `SIGNUPS_ALLOWED` to
`"false"` in `deployment.yaml` and commit the change. Leaving public signup
enabled is not recommended.

The admin page is disabled because no `ADMIN_TOKEN` is configured. If it is
needed later, store an Argon2 PHC string in a SealedSecret and expose it through
the `ADMIN_TOKEN` environment variable; never commit the plaintext token.

See [the system structure guide](../../docs/structure.md) for backup and
recovery details.
