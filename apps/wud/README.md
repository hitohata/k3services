# What's Up Docker? (WUD)

WUD monitors the cluster's deployed container images and reports available
updates at `https://wud.dejima.men` through the TLS-terminating gateway and at
`http://wud.n100.lan` on the LAN. It does not update Kubernetes workloads;
apply reviewed version changes through this GitOps repository.

The Kubernetes watcher discovers Deployments, StatefulSets, DaemonSets, and
CronJobs in every namespace once per hour. Its `wud-reader` ClusterRole is
read-only and grants only the workload, Pod, and Node access required for
discovery and image architecture detection.

WUD's SQLite database, discovered-image state, and UI configuration are stored
on the `wud-store` `local-path` PVC on `n100`. This operational state is not a
backup source. The deployment is intentionally pinned to WUD 9.1.0; review
upstream release notes before changing the image version.

WUD requires an administrator account. Before syncing the application, create
the encrypted credentials:

```sh
cp apps/wud/secrets/credentials.secret.example /secure/path/wud-credentials.secret.yaml
# Generate a password, then replace the placeholder in the plaintext file.
openssl rand -base64 32
# Edit /secure/path/wud-credentials.secret.yaml. Do not commit it.
kubeseal \
  --controller-name sealed-secrets-controller \
  --controller-namespace kube-system \
  --format yaml \
  < /secure/path/wud-credentials.secret.yaml \
  > apps/wud/secrets/credentials.sealed-secret.yaml
```

Commit only `credentials.sealed-secret.yaml`; it is encrypted for this cluster.
The plaintext input file must remain outside this repository. The username may
remain `admin`, or be changed before sealing. The configured administrator
credentials are reapplied on each WUD start, so rotate them by updating the
sealed Secret.
