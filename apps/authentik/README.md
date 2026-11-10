# Authentik

Authentik is deployed with the official Helm chart and a separately managed
PostgreSQL database. It is available at `https://authentik.dejima.men` through
the TLS-terminating gateway and at `http://authentik.n100.lan` on the LAN.

The supplemental `resources/public-ingress.yaml` route takes precedence over
the chart's route for `authentik.dejima.men` and sets `X-Forwarded-Proto: https`.
This domain must be accessed through the HTTPS gateway, which redirects public
HTTP requests to HTTPS. The override prevents HTTP API URLs and browser mixed
content errors when the gateway's forwarded scheme is lost before reaching
Authentik. The chart continues to handle the LAN HTTP alias independently.
It does not change Traefik's global proxy trust or restart application pods.

Before the first sync, create the encrypted credentials from the example. Use
distinct random values and keep `AUTHENTIK_SECRET_KEY` unchanged after the
initial deployment:

```sh
cp apps/authentik/secrets/credentials.secret.example /secure/path/authentik-credentials.secret.yaml
# Replace every placeholder. Do not commit this plaintext file.
kubeseal \
  --controller-name sealed-secrets-controller \
  --controller-namespace kube-system \
  --format yaml \
  < /secure/path/authentik-credentials.secret.yaml \
  > apps/authentik/secrets/credentials.sealed-secret.yaml
```

Commit only the generated `credentials.sealed-secret.yaml`. Authentik presents
the first-run setup for the `akadmin` account at the public URL. PostgreSQL uses
`local-path` on `n100`; a daily compressed database dump is retained for 14
days on the NAS.
