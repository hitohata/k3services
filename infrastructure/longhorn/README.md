# Replicated SSD storage pilot

Longhorn chart **1.13.0** is prepared as the `longhorn` Argo CD Application.
It uses the V1 engine with one replica on each of **n100 and p41**. Both the
installation and the separate `longhorn-pilot` Application require manual
sync. Nothing in this package migrates existing application claims.

The companion **`longhorn-admission`** Application pins Kyverno chart **3.10.0**
(engine **v1.20.0**) for NixOS host-tool discovery. It also requires manual
sync and must be healthy before Longhorn is installed. Only its admission
controller runs: two replicas on distinct SSD hosts, requesting 128 MiB RAM
and 100m CPU each; background, cleanup and reporting controllers are disabled.

Read-only inspection on **2026-11-15** confirmed both node labels, loaded
`iscsi_tcp`, active K3s/iscsid, and open-iscsi 2.1.13. p41's exact
`/var/lib/longhorn` bind resolves to `/dev/sda[/longhorn]` with about 104 GiB
free; n100's directory is on its SSD with about 317 GiB free. p51 still reports
DiskPressure, so an actual n100-outage test remains blocked. Longhorn and
the admission engine are not installed yet.

## Host handoff to .dot-nix

Complete and verify these host prerequisites before the installation sequence:

1. On **n100 and p41**, enable compatible open-iscsi, active `iscsid`, required
   kernel modules, and validated NixOS host-tool discovery for Longhorn CSI and
   dynamic instance-manager pods. Check the pinned release's requirements;
   installing host packages alone does not validate `nsenter` execution.
2. On **p41**, bind mount `/mnt/ssd/longhorn` at **`/var/lib/longhorn`**. Its
   source must be on ext4 SSD UUID `a027e4b8-2f05-44b2-bdce-5c9528334a7c`.
   Order mounts before K3s and prevent SD-card fallback on failure. This is a
   separate sibling of the existing `/mnt/ssd/k3s-storage` source.
3. On **n100**, ensure `/var/lib/longhorn` exists on its SSD. Do not relocate
   existing local-path application data or etcd as part of this preparation.
4. Persist Kubernetes label **`storage.dejima.men/longhorn=true`** on **only
   n100 and p41**, for example through their K3s `--node-label` configuration.
   Do not label p51 for this pilot. This label selects managers, CSI components,
   and the pilot consumer; without it, installation deliberately cannot run.
5. Repair p51's DiskPressure and verify the surviving control-plane nodes can
   remain healthy before attempting an n100-outage test. NFS-dependent
   application migration additionally requires repairing p41's NFS mounts.

Confirm the actual mount and UUID on p41, not just directory existence:

```bash
findmnt /mnt/ssd
findmnt /var/lib/longhorn
df -hT /var/lib/longhorn
systemctl is-active iscsid
kubectl get nodes -L storage.dejima.men/longhorn
```

Do not synchronize Longhorn until the host project reports its compatibility
and mount checks complete. If NixOS integration requires additional Kubernetes
configuration, incorporate and render that configuration first; this package
does not assume that a generic PATH override fixes all dynamic components.

## Configuration and ownership

### NixOS Pod admission

The current K3s API does not expose native MutatingAdmissionPolicy. Instead,
`longhorn-admission` uses Kyverno's **NamespacedMutatingPolicy**, scoped to
`longhorn-system` Pod CREATE requests, including dynamically generated
instance-manager, engine-image and CSI Pods. The webhook namespace selector
also restricts calls to that namespace. It does not mutate controllers,
existing Pods, or other application namespaces, and excludes Kyverno itself.

For all containers and init containers it preserves other environment values
and envFrom sources, keeps the existing literal PATH (or the exact reviewed
image default), and appends `/run/current-system/sw/bin` once. The 13 chart
image defaults and ARM64/AMD64 variants were checked directly from their OCI
image configurations; both architectures use the same default PATH. New image
references without a reviewed default, and indirect PATH values supplied by
valueFrom, fail closed rather than silently receiving a guessed environment.
Review and update the image inventory in the policy during upgrades.

Kyverno is a new admission dependency for Longhorn Pod creation. A missing
webhook blocks new Longhorn Pods, while the namespace selector leaves other
applications outside this webhook's scope. Preserve at least one working
admission replica during maintenance; do not uninstall it while Longhorn needs
to recreate Pods. Its CRDs are annotated against pruning, and TLS secrets are
generated at runtime rather than committed. Runtime namespace and iSCSI/CSI
checks on both hosts remain necessary after offline mutation tests pass.

### Storage

- Existing default StorageClass and all existing PVCs remain unchanged.
- `longhorn-ssd-ha` is non-default, uses V1, two replicas on distinct nodes,
  delayed binding, explicit node/disk tags, and `Retain` reclaim policy.
- `resources/nodes.yaml` owns only the two explicitly configured SSD nodes.
  Its disk paths are `/var/lib/longhorn`; p41's path must be SSD-backed by the
  host bind mount. Reserved disk capacity is 64 GiB on n100 and 32 GiB on p41.
- Automatic default-disk creation is limited to specially labeled nodes;
  this package sets no such labels. Do not set
  `node.longhorn.io/create-default-disk` on other nodes. Explicit node/disk
  selectors also prevent the pilot class from using untagged disks.
- New degraded volumes are disabled; a new claim must obtain two replicas.
  Existing volumes may operate on one surviving copy during an outage.
- V2 is disabled. Instance-manager CPU reservations use upstream V1 defaults;
  actual storage CPU/memory overhead must be measured before expanding scope.
- Two global-manager replicas require different hosts; CSI controller
  components use two replicas. The optional UI has one replica and is exposed
  only as ClusterIP. No Ingress or NodePort is created.
- The configured node-down policy allows automatic recovery of Deployment and
  StatefulSet pods. It is validated with disposable data before real workloads.
  A network partition is not equivalent to a confirmed powered-off writer;
  evaluate isolation and storage fencing before claiming partition safety.
- No Longhorn backup target or recurring backup is configured yet. The pilot
  marker is disposable. Independent backups are required before real data is
  migrated; snapshots and replicas are not independent backups.

All three Applications omit automated sync and deletion finalizers. Storage node,
class, and pilot claim manifests carry `Prune=false`. Upstream chart CRDs are
chart-managed and are **not individually annotated** by this repository: never
manually prune or uninstall the Longhorn Application as a cleanup shortcut.
Version upgrades, resource removal, and uninstall require an inventory of all
volumes and backups. Server-side apply handles the chart's large CRDs without
client-side last-applied annotations.

## Activation and storage checks

These are operator steps after host preparation and explicit authorization for
cluster changes; they have not been executed by preparing these files.

1. Publish the reviewed Git changes so Argo CD can read them. Manually sync
   **longhorn-admission**, without pruning. Verify both admission replicas and
   that `longhorn-nixos-path` is Ready. Confirm the generated mutating webhook
   matches only `longhorn-system`. Then manually sync **longhorn**, without
   pruning. Inspect actual manager, CSI, instance-manager and init-container
   PATH values and host-namespace tool execution on both nodes. Verify both
   managers and both global managers
   run on the intended nodes; check CSI readiness and both disk conditions.
   The Node and StorageClass manifests are sync wave 1, after chart resources.
2. Manually sync **longhorn-pilot**. This creates a separate namespace, a 1 GiB
   claim and a single Deployment that prefers n100 but permits p41. The Pod
   intentionally remains **unready** until the marker is initialized. Do not
   wait for the Application to become Healthy before performing step 3.
3. Verify the PVC is Bound and Longhorn shows **two healthy replicas on
   different nodes**. Then initialize the marker once:

   ```bash
   kubectl -n longhorn-pilot exec deployment/longhorn-storage-pilot -- \
     sh -ec 'test ! -e /data/marker; printf "%s\n" k3services-longhorn-pilot-v1 > /data/marker; sync'
   kubectl -n longhorn-pilot get pods -o wide
   ```

   Readiness now checks the marker value. The container never creates it on
   startup: a lost or empty replacement volume must remain unready.
4. Check the bound volume and replicas, and record the current placement:

   ```bash
   kubectl -n longhorn-pilot get pvc longhorn-storage-pilot -o wide
   kubectl -n longhorn-system get nodes.longhorn.io
   kubectl -n longhorn-system get volumes.longhorn.io
   kubectl -n longhorn-system get replicas.longhorn.io -o wide
   ```

5. With approval for an actual outage, stop the current workload node using a
   separately reviewed host procedure. Confirm a healthy etcd majority remains
   and observe automatic restart on the other eligible node. Record detection
   and recovery times, readiness, marker contents, and volume health. A drain
   alone does not test ungraceful node loss. Do not delete the claim or
   reinitialize a missing marker to make the test pass.
6. Recover the node and verify replica rebuild, two healthy copies, CPU/memory
   overhead, and storage latency. With only two data nodes, there is one copy
   during the outage and no third SSD destination for rebuilding redundancy.

The pilot has no Service or Ingress. It tests storage recovery, not end-to-end
public access. A subsequent application pilot must verify gateway routing,
CoreDNS, Traefik, compatibility, backups, and available memory after failure.

For temporary administration access:

```bash
kubectl -n longhorn-system port-forward service/longhorn-frontend 8080:80
```

Then open `http://127.0.0.1:8080`. Homepage links to this guide rather than
exposing an unauthenticated storage administration endpoint.

## Validation

Preparation checks passed on 2026-11-14: Helm lint and rendering for Kubernetes
1.35.8; 35 standard resources against Kubernetes 1.35 schemas; both custom Node
objects against the chart's Node CRD schema; and all 28 CRD objects against the
live cluster's apiextensions OpenAPI schema. YAML parsing and `git diff --check`
also passed. These checks made no cluster changes.

The 2026-11-15 admission addition passed Helm lint/rendering, validation of
23 standard Kubernetes resources, all 22 Kyverno CRD objects against the
cluster's apiextensions OpenAPI schema, and the namespaced policy against the
pinned Kyverno CRD schema. All five offline policy regression tests passed
using the checksum-verified v1.20.0 CLI. No admission resources were installed.

Use the pinned chart with Helm and the repository values:

```bash
helm lint longhorn-1.13.0.tgz -f infrastructure/longhorn/values.yaml --kube-version 1.35.8
helm template longhorn longhorn-1.13.0.tgz --namespace longhorn-system \
  --kube-version 1.35.8 -f infrastructure/longhorn/values.yaml > /tmp/longhorn-rendered.yaml
```

Download the archive using the URL from the
[official chart index](https://charts.longhorn.io/index.yaml). Validate rendered
Kubernetes resources and the custom Node manifests against the CRD schemas.
Local rendering cannot establish host readiness, runtime consumption, automatic
recovery, or database portability. See the
[HA assessment](../../docs/storage-ha-plan.md) for remaining limitations.

Offline admission regression tests use the same pinned Kyverno CLI:

```bash
KYVERNO_CLI=/path/to/kyverno-v1.20.0 python3 infrastructure/longhorn/tests/test_nixos_path.py
```

They exercise dynamic Pod/init-container mutation, preservation of existing
environment and envFrom configuration, idempotency, absent init containers,
namespace isolation, unreviewed-image rejection and indirect-PATH rejection.
