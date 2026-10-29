# Nextcloud secrets

The Nextcloud Helm release is declared in `root-app/apps.yaml`. This directory
is a separate Argo CD source for the encrypted credentials it consumes.

After the Sealed Secrets controller is healthy, copy the example to a secure
local location, replace every placeholder with a unique generated password, and
seal it for this cluster:

```sh
cp apps/nextcloud/secrets/credentials.secret.example /secure/path/credentials.secret.yaml
# Edit /secure/path/credentials.secret.yaml. Do not commit it.
kubeseal \
  --controller-name sealed-secrets-controller \
  --controller-namespace kube-system \
  --format yaml \
  < /secure/path/credentials.secret.yaml \
  > apps/nextcloud/secrets/credentials.sealed-secret.yaml
```

Commit only the resulting `credentials.sealed-secret.yaml`; do not commit the
plaintext input file. The sealed file is cluster-specific. It must contain a
Secret named `nextcloud-credentials` in the `nextcloud` namespace.

See [the system structure guide](../../docs/structure.md) for the deployed
components, storage layout, backup policy, upgrades, and recovery process.

## Database backup client

The `nextcloud-db-backup` CronJob pins its `mariadb-dump` client to
`mariadb:12.3.3` (LTS). The live MariaDB server remains pinned to `12.0.2`;
changing a backup client does not upgrade the database. The job uses Bash
`pipefail` so dump errors fail the job, writes to a `.partial` file, and only
publishes a `.sql.gz` backup and prunes old dumps after successful compression.
Use a recent MariaDB client for restores because dumps include a sandbox-mode
command that older clients and the MySQL client may reject. After syncing,
check the next scheduled backup and test a restore against MariaDB 12.0.2.
