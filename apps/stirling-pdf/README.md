# Stirling PDF

Stirling PDF is a self-hosted PDF editor available at
`https://stirling-pdf.dejima.men` through the TLS-terminating gateway and at
`http://stirling-pdf.n100.lan` on the LAN. It is intentionally deployed without
Stirling's optional account system, so restrict gateway access to trusted users.

The application runs on `n100`. Its configuration, including settings changed
from the web UI, is stored on the `stirling-pdf-config` `local-path` PVC. Files
uploaded for PDF operations and container logs are ephemeral and are removed
when the pod is recreated.

The application image is pinned to Stirling PDF 2.14.3. It has a 100 MiB upload
limit and uses the `en-CA` locale by default. Change those settings in
`deployment.yaml` when needed; review the upstream release notes before updating
the image version.

KEDA scales Stirling PDF to zero after 30 minutes without HTTP requests and
starts it again when a request arrives. The first request after an idle period
waits for the pod to start, which can take up to the configured seven-minute
interceptor readiness timeout. The deployment is intentionally limited to one
replica because its configuration PVC is `ReadWriteOnce`.
