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
