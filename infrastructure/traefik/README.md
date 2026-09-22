# Traefik forwarded headers

K3s deploys Traefik as its packaged Helm chart in the `kube-system` namespace.
This `HelmChartConfig` limits trust of forwarded request headers on Traefik's
HTTP `web` entry point to the TLS-terminating gateway at `192.168.10.1`.

The gateway must set `X-Forwarded-Proto: https` for HTTPS requests. Traefik
then preserves that trusted header when forwarding to cluster services, so
applications such as Authentik generate HTTPS URLs and secure cookies.

The setting deliberately does not enable Traefik's insecure forwarded-header
mode. Updating this configuration makes the K3s Helm controller roll out
Traefik, briefly interrupting ingress traffic.

Traefik permits `ExternalName` Services for Kubernetes Ingress backends. This
is required by the Stirling PDF KEDA proof-of-concept: its Ingress uses a
same-namespace `ExternalName` Service to reach KEDA's interceptor in the
`keda` namespace. Review any future ExternalName-backed Ingress as a
cross-namespace or external routing change.
