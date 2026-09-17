# Linkwarden

Linkwarden, PostgreSQL, and Meilisearch are deployed from this directory.
PostgreSQL and Meilisearch remain pinned to `n100` because they use
`local-path`; the NFS-backed Linkwarden web application is schedulable on any
node and prefers a node that does not already run Mealie or Linkwarden. The web
application is available through the TLS-terminating gateway at
`https://linkwarden.dejima.men`.

Before the first sync, copy the credential template to a secure path,
replace every placeholder, and seal it for this cluster. Repeat this process
when rotating credentials:

```sh
cp apps/linkwarden/secrets/credentials.secret.example /secure/path/linkwarden-credentials.secret.yaml
kubeseal \
  --controller-name sealed-secrets-controller \
  --controller-namespace kube-system \
  --format yaml \
  < /secure/path/linkwarden-credentials.secret.yaml \
  > apps/linkwarden/secrets/credentials.sealed-secret.yaml
```

Generate each password with the following command, then paste it directly into
the secure plaintext Secret. It uses the system entropy source and emits only
URL-safe characters, which is required for `db-password` because the
deployment embeds it in Linkwarden's PostgreSQL connection URL:

```sh
head -c 48 /dev/urandom | base64 | tr '+/' '-_' | tr -d '=\n'; echo
```

Use a distinct generated value for `db-password`, `postgres-password`,
`nextauth-secret`, and `meili-master-key`. Commit only
`credentials.sealed-secret.yaml`; never commit the plaintext Secret.
Changing database credentials in the SealedSecret alone does not rotate
credentials already stored in PostgreSQL.

Link archives are kept on the NAS; PostgreSQL and Meilisearch indices use
`local-path` storage on `n100`. A daily compressed PostgreSQL dump is retained
for 14 days on the NAS.
