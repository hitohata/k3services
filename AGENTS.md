# k3services

## Purpose

This repository is the GitOps source for a self-hosted K3s cluster. Argo CD
continuously synchronizes the repository, so a merged change can affect the
live cluster.

## Fast orientation

- Start with `README.md` and `docs/structure.md` for system-wide architecture.
- `root-app/apps.yaml` is the Argo CD app-of-apps entry point. It defines the
  deployed applications, sources, chart versions, namespaces, sync waves, and
  automated sync policy.
- `apps/<service>/` contains the service's Helm values and/or Kubernetes
  manifests. Read that service's `README.md` before changing it.
- `infrastructure/` holds cluster-wide components, currently NFS dynamic
  provisioning.

Do not scan every service by default. Read only the files relevant to the
requested service, plus the fast-orientation files when repository-wide context
is needed.

## Deployment and safety

- Argo CD applications generally have automated prune and self-heal enabled.
  Treat manifest removal or a rename as a potential live-resource deletion.
- Do not run `kubectl apply`, Argo CD sync commands, or change live-cluster
  state unless the user explicitly asks.
- Preserve intentionally non-pruning resources, especially `argocd-crds`.
- Keep chart and image versions pinned. Treat chart upgrades as deliberate
  maintenance work and review the affected service documentation first.

## Secrets and storage

- Commit only encrypted `*.sealed-secret.yaml` files and `*.secret.example`
  templates. Never commit plaintext credentials or replace encrypted values
  with plaintext Kubernetes Secrets.
- Do not generate or modify `*.sealed-secret.yaml` files. When credentials are
  needed, create or update only the `*.secret.example` template; the user is
  responsible for creating the sealed secret with their own values.
- Live databases and latency-sensitive application state intentionally use
  `local-path` storage on `n100`; do not casually migrate them to NFS.
- NFS-backed data and backup PVCs use service-specific `nfs-client-*`
  StorageClasses. Consult `docs/structure.md` before changing storage or backup
  behavior.

## Change hygiene

- Match the existing YAML style and keep changes scoped to the requested
  application.
- Every application must have an `apps/<service>/README.md`. Add or update it
  whenever creating or materially changing that application.
- When adding an application, also update the Homepage configuration in
  `apps/homepage/` so it is listed in the service dashboard.
- Update `docs/structure.md` when changing system architecture, storage,
  backup, exposure, or other operational behavior.
- Validate YAML and rendered manifests with the repository's available tools;
  report any validation that cannot be run locally.
