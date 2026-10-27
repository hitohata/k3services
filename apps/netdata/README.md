# Netdata

Netdata is deployed from the official Helm chart configured by `values.yaml`.
The parent dashboard is available only on the LAN at
`http://netdata.n100.lan`.

The Agent image is explicitly pinned to `v2.12.2` through the shared
`image.tag` value, covering the parent, every child collector, and the
Kubernetes-state collector. This overrides the pinned chart's `v2.11.1`
default and includes the security fixes in
[the v2.12.2 release](https://github.com/netdata/netdata/releases/tag/v2.12.2).
Updating this value restarts those workloads and briefly interrupts monitoring;
the existing metrics and state volumes are retained.

The chart runs a child collector on every node. Those pods intentionally use
host PID, IPC and networking, mount host paths, and request `SYS_PTRACE` and
`SYS_ADMIN`, as required for host and container monitoring. Review upstream
chart changes carefully before upgrading.

The parent and Kubernetes-state collector run on `n100` and use `local-path`
PVCs. Their data is operational metrics and is not backed up. Per-node child
identity is retained under `/var/lib/netdata-k8s-child` on each node.

The upstream service-discovery sidecar is disabled. The custom RBAC in
`resources/rbac.yaml` permits read-only access to cluster workload and node
metadata but deliberately excludes Secrets and ConfigMaps.

Netdata Cloud claiming is disabled. If it is enabled later, put the claim token
in a SealedSecret and reference it with `parent.envFrom`/`child.envFrom`; never
commit the token in `values.yaml`.
