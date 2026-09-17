# Forgejo

Forgejo is deployed with the official Helm chart, external PostgreSQL, and a
rootless Forgejo image pinned to the 15.0 LTS line. The service is available at
`https://forgejo.dejima.men` through the TLS-terminating gateway.

The committed SealedSecret creates the initial `forgejo-admin` account. After
the first successful sync, retrieve the generated password with:

```sh
kubectl -n forgejo get secret forgejo-admin-credentials \
  -o jsonpath='{.data.password}' | base64 -d; echo
```

Forgejo initially supports HTTPS Git access only. SSH cloning and Forgejo
Actions are disabled until their required TCP ingress and runner security model
are deliberately configured.

Repository data and PostgreSQL use `local-path` on `n100`. A daily backup job
writes a compressed PostgreSQL dump together with Forgejo data to the NAS and
retains 14 archives. See [the system structure guide](../../docs/structure.md)
for storage and recovery details.

To replace generated credentials, copy the corresponding `*.secret.example`
file to a secure path, edit it, and seal it for this cluster with `kubeseal`:

```sh
kubeseal \
  --controller-name sealed-secrets-controller \
  --controller-namespace kube-system \
  --format yaml \
  < /secure/path/forgejo-admin.secret.yaml \
  > apps/forgejo/secrets/admin.sealed-secret.yaml
```

Never commit the plaintext Secret. Changing database credentials in the
SealedSecret alone does not rotate credentials already stored in PostgreSQL.
