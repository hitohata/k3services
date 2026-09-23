# KEDA

KEDA provides event-driven scaling for selected workloads. It is installed in
the `keda` namespace from the pinned `kedacore/keda` Helm chart. The pinned
KEDA HTTP Add-on is installed alongside it and supplies the interceptor,
scaler, and operator needed to scale HTTP workloads from zero.

The KEDA Argo CD Application uses server-side apply because the chart's
`ScaledJob` CRD is too large for Kubernetes' client-side apply annotation.
Keep that sync option when updating the chart; without it, Argo CD cannot
create the CRD and the KEDA operator exits while starting its ScaledJob
controller.

The HTTP interceptor has one always-running replica for this initial
proof-of-concept. It accepts requests while a workload is stopped, asks KEDA
to start it, and forwards the held request once the workload is ready. Its
seven-minute readiness timeout accommodates Stirling PDF's six-minute startup
probe allowance.

Stirling PDF is currently the only scaled workload. Its KEDA resources live
with that application, and it has a 30-minute idle cooldown and a maximum of
one replica. The one-replica limit is required because its configuration PVC
is `ReadWriteOnce`.

Do not remove the KEDA or HTTP Add-on Argo CD Applications before removing all
`ScaledObject` and `InterceptorRoute` resources that depend on their CRDs.
