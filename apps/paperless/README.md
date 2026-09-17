# Paperless-ngx

Paperless-ngx is deployed from the manifests and PostgreSQL Helm values in this
directory. Paperless, PostgreSQL, and Valkey are pinned to `n100`. The web
application is available through the TLS-terminating gateway at
`https://paperless.dejima.men`.

The committed SealedSecret creates the initial `admin` account. After the first
successful sync, retrieve its generated password with:

```sh
kubectl -n paperless get secret paperless-credentials \
  -o jsonpath='{.data.admin-password}' | base64 -d; echo
```

To replace the generated credentials, copy `credentials.secret.example` to a
secure path, edit it, and seal it for this cluster:

```sh
cp apps/paperless/secrets/credentials.secret.example /secure/path/paperless-credentials.secret.yaml
kubeseal \
  --controller-name sealed-secrets-controller \
  --controller-namespace kube-system \
  --format yaml \
  < /secure/path/paperless-credentials.secret.yaml \
  > apps/paperless/secrets/credentials.sealed-secret.yaml
```

Never commit the plaintext Secret. Changing database credentials in the
SealedSecret alone does not rotate credentials already stored in PostgreSQL.

Documents and the consume/export directories live on the NAS. PostgreSQL,
Valkey, and Paperless's search/index data use `local-path` storage. Two daily
jobs create a compressed PostgreSQL dump and update Paperless's portable
document export. See [the system structure guide](../../docs/structure.md) for
storage, recovery, and operational details.
