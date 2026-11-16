# longhorn-admission

The admission companion provides namespace-scoped NixOS host-tool PATH injection for Longhorn Pods.

Deployment manifests and the activation procedure are maintained in
[the infrastructure guide](../../infrastructure/longhorn/README.md).
The Argo CD Application uses manual synchronization; existing application
volumes are not migrated by installing this component.
