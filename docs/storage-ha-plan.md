# Replicated storage and automatic application recovery

Status: Longhorn, admission, and the 1 GiB pilot deployed, 2026-11-18.
See [the Longhorn package](../infrastructure/longhorn/README.md) for the pinned
chart values, SSD-node definitions, StorageClass, disposable test, host handoff,
and activation procedure. On 2026-11-19 ntfy's stopped cache was backed up to
NAS and independently restored with SQLite integrity/checksum verification.
A new 2 GiB Longhorn claim was populated, but another p41 USB SSD failure
occurred before ntfy started. The cutover was rolled back to its original
n100/local-path configuration. Both claims and the verified archive remain.
No application migration has been accepted.

The SSD disappeared again despite a port change and reboot. p41 K3s stopped
with the mount dependency, leaving the storage pilot degraded on n100. Repair
and observe USB storage before retrying. Actual node-outage and ingress recovery
remain untested; p51 DiskPressure also prevents an n100-outage acceptance test.

## Objective

Reduce n100's normal workload while allowing selected applications to restart
automatically on a surviving node after n100 fails. A local-path move alone
does not meet this objective. The earlier p41-only storage preparation is on
hold as an application migration strategy; it remains useful only for data
that deliberately does not need automatic failover.

Automatic restart includes an interruption for failure detection, safe volume
reattachment, and application recovery. No recovery-time or zero-data-loss
guarantee has been established. Replication does not replace independent backups.

## Storage pilot

Evaluate **Longhorn V1**, with one data replica on n100's SSD and one on p41's
SSD. Do not place data replicas on p51's SD card. p51 remains an existing K3s
control-plane/etcd member; it is not a third copy of application data.

The candidate version researched is Longhorn `1.13.0`, the upstream latest
release at assessment time. It requires Kubernetes >= 1.34; the observed
cluster is K3s 1.35. The prepared package pins that chart and its image versions.
Its Applications remain manual-sync only after the initial deployment.

The deployed pilot follows these design requirements:

- Keep the current default StorageClass; create a separate, non-default class
  for replicated volumes, with `Retain` reclaim policy and two replicas.
- Require replica separation across different nodes. Disable creation with
  degraded availability so a new volume cannot silently start with one copy.
- Explicitly select SSD directories on n100 and p41; disable automatic data
  disk creation on other nodes. Use a separate directory such as
  `/mnt/ssd/longhorn` on p41, bind-mounted at `/var/lib/longhorn`, not an existing
  application's local-path directory.
- Enable only the V1 data engine for this evaluation. V2 has additional CPU,
  huge-page, and disk requirements unsuitable for the current p41 headroom.
- Keep installation under manual Argo CD sync until host prerequisites and
  pilot checks pass. Do not allow pruning storage CRDs or uninstalling the
  storage system to become an accidental data-deletion path.
- Configure and test node-down workload recovery. Longhorn's default
  `do-nothing` pod-deletion policy is insufficient for unattended recovery of
  stuck Deployment/StatefulSet pods. Evaluate the explicit policy appropriate
  for the pilot; do not blindly force-delete pods on a partitioned but still
  writing host. Verify isolation of the previous writer before reattachment.

## Hardware and capacity findings

| Node | Findings | Role in the proposal |
| --- | --- | --- |
| n100 | AMD64, about 16 GB RAM, 477 GiB SSD; root filesystem about 127 GiB used and 317 GiB free | Application compute and one storage replica |
| p41 | ARM64, about 4 GB RAM, 112 GiB SSD with about 104 GiB free at the earlier inspection; node memory usage around 2 GiB | Second storage replica and a limited set of application workloads |
| p51 | ARM64, about 8 GB RAM; SD card has 8.7 GiB free, current DiskPressure and pod evictions | Existing control-plane quorum member; not a data-replica destination |

Current local-path claims request **374 GiB** in total. Their requests are not
actual use, but they cannot all be carried unchanged as conservatively
allocated replicated volumes on p41's 112 GiB SSD. Longhorn snapshots,
rebuilding, and free-space reservations also need capacity. Re-measure each
source directory and choose destination sizes deliberately; start with a
small disposable volume, not a blanket storage-class replacement.

Kubelet summary metrics for these existing local volumes reported usage of
the shared backing filesystem, not per-directory application usage. Do not
sum those metrics or present them as per-PVC sizes. Use per-directory `du -sk` measurements on the actual mounted application
data paths, as in the candidate measurements below.

Longhorn's V1 minimum recommended hardware is three nodes with four vCPUs and
4 GiB RAM per node. This proposal has only two SSD data nodes and p41 already
hosts workloads; it is a constrained pilot, not an assertion that the full
current cluster meets those recommendations. Measure added storage overhead,
latency, and replica-rebuild load before choosing more applications.

Even without storage overhead, p41 cannot be assumed to take over n100's entire
observed 9–10 GiB node memory footprint. Define which applications remain
available after failure and reserve resources for them. Supporting every
application may require additional hardware or a smaller surviving workload.

## Application selection and n100 load

For reducing normal n100 load, Netdata's parent and Kubernetes-state collector
are better candidates than ntfy alone:

| Workload | Observed memory | Observed CPU | Persistent data |
| --- | --- | --- | --- |
| Netdata parent | 554 MiB | 63m | 2,265,668 KiB (about 2.16 GiB) database and 40 KiB state |
| Netdata Kubernetes-state | 155 MiB | 33m | 52 KiB state |
| n8n | 410 MiB | 6m | About 6.6 MiB at the earlier measurement |
| WUD | 154 MiB | 6m | About 4.5 MiB at the earlier measurement |
| ntfy | 22 MiB | 2m | 68 KiB at the earlier measurement |

These are snapshots, not peaks. Netdata's same pinned `v2.12.2` image already
runs as a child on ARM64 p41. Its parent and state collector do not need NFS.
The n100 child remains on n100 to collect host metrics. Netdata history has
different recovery value from application business data; do not spend all
available replica capacity on monitoring history before protecting important
application state.

First validate storage with disposable data, then use a small application such
as ntfy for the end-to-end migration/recovery exercise. That proves the mechanism
with a small footprint; it is not claimed to significantly reduce n100 load.
After measuring infrastructure overhead, choose Netdata components and/or n8n
to reduce normal load while respecting failure-time memory reservations.

## Additional prerequisites

### Host work in .dot-nix

The SSD mount work underway remains useful but is not sufficient for Longhorn:

1. On nodes consuming V1 volumes, configure supported open-iscsi, active
   `iscsid`, and required kernel modules such as `iscsi_tcp`. The read-only n100
   inspection found no `iscsiadm` in the SSH environment and inactive `iscsid`.
2. Keep p41's Longhorn directory on its UUID-mounted SSD, with startup and
   failure dependencies that prevent fallback writes to the SD card. Do not
   replace existing local-path mounts or move etcd as part of this work.
3. Verify NixOS host-tool lookup from Longhorn's actual execution namespaces.
   The upstream NixOS issue documents PATH/nsenter difficulties; installing
   packages on the host alone is not proof that dynamic instance-manager and
   CSI pods can use them. Select and validate a supported integration before
   drafting deployable manifests. Avoid adopting an old issue workaround
   without testing it against the pinned version.
4. Fix and verify the existing p41 NFS mounting problem for applications and
   backup paths that depend on the NAS. RWO block-volume pilot checks can be
   kept separate from NFS, but NAS-dependent applications cannot.

Longhorn's published preflight tool creates checker resources in Kubernetes;
running it is a cluster mutation, not part of this read-only assessment.

### Database compatibility

Replicated blocks do not make an existing database's on-disk format portable
between AMD64 and ARM64. PostgreSQL documents a same-hardware-architecture
requirement for physical standby/log shipping. Do not promise automatic
cross-architecture recovery of the existing PostgreSQL PVCs from image
multi-architecture support alone. Review each database/extension's guarantees
and validate its recovery path; an additional AMD64 recovery node may be
needed for a supported design. A one-time logical dump/restore is not an
automatic ongoing cross-architecture failover solution.

SQLite-based pilot applications are simpler candidates, but still require
testing the exact image and application state on both nodes.

### Scheduling, cluster services, and ingress

Each protected application must allow execution on at least two eligible,
compatible nodes. Its current `nodeSelector: n100` must be replaced with a
policy permitting failover while preferring the normal node. Update local-data
backup-job placement together with the application, including concurrent
volume-access constraints. Do not hard-code all backups to n100.

All three nodes currently participate in etcd. A healthy surviving majority is
required; p51's DiskPressure therefore deserves repair even if it stores no
application replicas. The observed Traefik Service advertises all three node
IPs with `externalTrafficPolicy: Cluster`, but gateway upstream selection is
not established by that fact. Verify the gateway can reach a surviving ingress
node without relying exclusively on `192.168.10.10`. CoreDNS and Traefik were
single-pod workloads on n100 during inspection; plan and test their survival
or rescheduling as well.

## Acceptance and migration sequence

1. Complete host prerequisites and disk-pressure repair, choose exact pilot
   resource budgets, and review the manually synchronized installation.
2. Provision a disposable volume with two healthy copies on separate SSDs.
   Test writes, checksums, restarts, and switching the consumer between nodes.
3. With explicit authorization for downtime, test a true single-node outage,
   automatic workload restart, ingress reachability, and committed-data
   consistency. Measure recovery time. Separately evaluate network partition
   behavior and protection against two writers.
4. Recover the node, verify replica rebuilding and capacity headroom, then
   verify a backup restore independent of the replicas. Two SSD copies provide
   only one remaining copy during a failure; no third SSD is available to
   rebuild redundancy until a node is repaired or another disk node is added.
5. Migrate one selected application with newly named claims, a consistent copy,
   rollback information, and old claims retained. Preserve off-node backups.
6. Expand only to applications that meet compatibility, capacity, and failover
   resource requirements. Record the exact protected scope and limitations.

## Sources

- [Longhorn v1.13.0 release and Kubernetes requirement](https://github.com/longhorn/longhorn/releases/tag/v1.13.0)
- [Hardware, scheduling, and operational recommendations](https://longhorn.io/docs/1.13.0/best-practices/)
- [V1 installation prerequisites](https://longhorn.io/docs/1.13.0/deploy/install/)
- [Node-down recovery behavior](https://longhorn.io/docs/1.13.0/high-availability/node-failure/)
- [NixOS integration issue](https://github.com/longhorn/longhorn/issues/2166)
- [PostgreSQL physical standby architecture requirements](https://www.postgresql.org/docs/current/warm-standby.html)
