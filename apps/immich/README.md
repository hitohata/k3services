# Immich

Immich is prepared for a one-time migration from the live NixOS service. It
will be available at `https://immich.dejima.men` through the TLS-terminating
gateway and directly on the LAN at `http://immich.n100.lan` after cutover.

The application mounts the existing NAS directories directly:

```text
/Pi-NAS/immich/
├── storage/    # existing Immich upload, thumbnail, profile, and video data
└── db_backup/  # NixOS PostgreSQL dumps
```

The official Immich Helm chart (pinned to `0.13.1`) deploys the server and
machine-learning workloads. PostgreSQL, the cache, and both Immich workloads
are pinned to `n100`.
PostgreSQL uses `local-path`; its live data must not be placed on NFS. The
Immich media directory remains NFS-backed so it stays exactly where the NixOS
service wrote it. The model cache is also local to `n100`.

The first machine-learning request after an idle period is a cold start. The
KEDA HTTP interceptor holds the request while it starts the worker; model files
remain in the local cache PVC, but loading them can still take time. The
cooldown is `600` seconds. Change `cooldownPeriod` in `deployment.yaml` only
if this startup delay proves acceptable for a shorter idle interval.
