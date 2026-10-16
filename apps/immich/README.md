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

The official Immich Helm chart (pinned to `0.13.4`) deploys the server and
machine-learning workloads. The server and machine-learning images are pinned
to Immich `v3.2.0`. PostgreSQL, the cache, and both Immich workloads are pinned
to `n100`.
PostgreSQL uses `local-path`; its live data must not be placed on NFS. The
Immich media directory remains NFS-backed so it stays exactly where the NixOS
service wrote it. The model cache is also local to `n100`.

The machine-learning worker remains running so face detection and other model
requests do not wait for a scale-up cold start. KEDA keeps its minimum at one
replica, and the model cache remains on the local PVC.
