# Mealie

Mealie is deployed by the Helm sources declared in `root-app/apps.yaml`.
Application settings are in `values.yaml`; PostgreSQL settings are in
`postgresql-values.yaml`. Both the application and its PostgreSQL database are
pinned to `n100`.

Before syncing the application, create the encrypted database credentials:

```sh
cp apps/mealie/secrets/credentials.secret.example /secure/path/mealie-credentials.secret.yaml
# Edit /secure/path/mealie-credentials.secret.yaml. Do not commit it.
kubeseal \
  --controller-name sealed-secrets-controller \
  --controller-namespace kube-system \
  --format yaml \
  < /secure/path/mealie-credentials.secret.yaml \
  > apps/mealie/secrets/credentials.sealed-secret.yaml
```

Commit only `credentials.sealed-secret.yaml`; it is encrypted for this cluster.
The plaintext input file must remain outside this repository. The generated
Secret must be named `mealie-postgresql-credentials` in the `mealie` namespace.

See [the system structure guide](../../docs/structure.md) for storage,
database backup, recovery, and upgrade details.
