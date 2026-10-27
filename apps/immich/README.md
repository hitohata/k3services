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
to Immich `v3.3.5`. Kubernetes can schedule the server and ML worker on any
eligible cluster node. PostgreSQL remains on `n100` because its `local-path`
storage is node-local. The Immich media directory remains NFS-backed so it
stays exactly where the NixOS service wrote it.

The machine-learning worker remains running so face detection and other model
requests do not wait for a scale-up cold start. KEDA keeps its minimum at one
replica. The model cache uses pod-local ephemeral storage, so model files are
downloaded again if the pod is replaced. The cache contains no user photos or
recognition results.

## Future work

- Once shared persistent storage is introduced, move the machine-learning
  model cache to a shared PV so model files survive pod replacement and can be
  reused across workers.
