# Stirling PDF

Stirling PDF is a self-hosted PDF editor available at
`https://stirling-pdf.dejima.men` through the TLS-terminating gateway and at
`http://stirling-pdf.n100.lan` on the LAN. It uses local accounts so that saved
documents can be kept and shared between users.

The application runs on `n100`. Its configuration, user database, and settings
changed from the web UI are stored on the `stirling-pdf-config` `local-path`
PVC. Saved documents use the separate 20 Gi `stirling-pdf-storage`
`nfs-client-stirling-pdf` PVC backed by the NAS at
`/Pi-NAS/stirling-pdf/stirling-pdf-storage`. Saved documents are retained
across pod recreation; the cluster does not make an additional backup of this
PVC. Files uploaded only for a PDF operation and container logs remain
ephemeral.

Saved files and direct user-to-user sharing are enabled. Sign in, save a
document from **My Files**, then share it with the other user's account. This
is distinct from an ordinary editor upload, which stays in the browser session.

The application image is pinned to Stirling PDF 3.0.0. It has a 100 MiB upload
limit and uses the `en-CA` locale by default. Change those settings in
`deployment.yaml` when needed; review the upstream release notes before updating
the image version.

KEDA scales Stirling PDF to zero after 30 minutes without HTTP requests and
starts it again when a request arrives. The first request after an idle period
waits for the pod to start, which can take up to the configured seven-minute
interceptor readiness timeout. The deployment is intentionally limited to one
replica because its local configuration PVC is `ReadWriteOnce`.
