# Immich

Immich is prepared for a one-time migration from the live NixOS service. It
will be available at `https://immich.dejima.men` through the TLS-terminating
gateway and directly on the LAN at `http://immich.n100.lan` after cutover.

The application mounts the existing NAS directories directly:

```text
/Pi-NAS/immich/
├── storage/    # existing Immich upload, thumbnail, profile, and video data
└── db_backup/  # NixOS PostgreSQL dumps
```

The official Immich Helm chart (pinned to `0.12.0`) deploys the server and
machine-learning workloads. PostgreSQL, the cache, and both Immich workloads
are pinned to `n100`.
PostgreSQL uses `local-path`; its live data must not be placed on NFS. The
Immich media directory remains NFS-backed so it stays exactly where the NixOS
service wrote it. The model cache is also local to `n100`.

## Migration

The NixOS service must be stopped before starting this application. The
database, Valkey, static claims, and Ingress may sync, but the server and
machine-learning deployments are intentionally at zero replicas until the
restore has completed. The pinned `v3.0.0` server supports restoring the v2
database and runs its schema migrations on first startup. Do not subsequently
downgrade it: Immich does not support downgrades.

1. Copy this template to a secure location, set a new alphanumeric password,
   and create `immich-credentials` as a SealedSecret in the `immich`
   namespace. This is a new destination PostgreSQL password; the NixOS
   password is neither needed nor recoverable from PostgreSQL.

   ```sh
   cp apps/immich/secrets/credentials.secret.example /secure/path/immich-credentials.secret.yaml
   kubeseal \
     --controller-name sealed-secrets-controller \
     --controller-namespace kube-system \
     --format yaml \
     < /secure/path/immich-credentials.secret.yaml \
     > apps/immich/secrets/credentials.sealed-secret.yaml
   ```

2. Let Argo CD create and make ready `immich-postgresql` while both Immich
   deployments remain at zero. Verify the extension versions before the
   cutover:

   ```sh
   kubectl -n immich exec statefulset/immich-postgresql -- \
     psql --username=postgres --dbname=immich \
     --command='SELECT extname, extversion FROM pg_extension WHERE extname IN ('\''vector'\'', '\''vchord'\'');'
   ```

3. Schedule a maintenance window. Stop NixOS Immich so no uploads or jobs can
   change the media while the final database dump is taken. On NixOS, create a
   final, clean logical dump in the already-mounted backup directory:

   ```sh
   sudo -u postgres pg_dump --clean --if-exists --no-owner --format=plain immich \
     | gzip > /mnt/pi_nas/immich/db_backup/immich-final.sql.gz
   ```

4. Restore that archive before the Kubernetes Immich server ever runs. Supply
   the destination password only from a secure terminal; it is intentionally
   not stored in Git. On its first startup, Immich v3 applies the required v2
   to v3 database migrations.

   ```sh
   gunzip --stdout /path/to/immich-final.sql.gz \
     | sed "s/SELECT pg_catalog.set_config('search_path', '', false);/SELECT pg_catalog.set_config('search_path', 'public, pg_catalog', true);/g" \
     | kubectl -n immich exec -i statefulset/immich-postgresql -- \
         psql --username=postgres --dbname=immich --single-transaction --set ON_ERROR_STOP=on
   ```

   Copy the final dump from the NAS backup claim to a secure local path before
   this command if needed. Do not run it against a PostgreSQL data directory
   that has already been used by Immich.

5. Change `server.controllers.main.replicas` to `1` in `values.yaml`, commit,
   and let Argo CD sync. KEDA starts the machine-learning deployment on its
   first request and returns it to zero replicas after ten minutes without a
   request. Confirm the server passes its startup probe, log in at the original
   URL, and check the System Integrity screen before allowing clients to resume
   uploads.

6. Keep NixOS Immich stopped for a rollback window. Once the Kubernetes
   library, recent uploads, and background jobs are verified, remove the NixOS
   service in a separate change. Do not remove either NAS directory: the
   Kubernetes application retains and actively uses both paths.

Immich's own database backups are stored beneath the upload location. Keep
those together with the media directory; a database dump without the matching
asset files cannot restore the library.

The first machine-learning request after an idle period is a cold start. The
KEDA HTTP interceptor holds the request while it starts the worker; model files
remain in the local cache PVC, but loading them can still take time. The
cooldown is `600` seconds. Change `cooldownPeriod` in `deployment.yaml` only
if this startup delay proves acceptable for a shorter idle interval.
