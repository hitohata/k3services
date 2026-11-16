# longhorn-pilot

The disposable pilot validates retained-volume attachment and marker survival before real application migration.

Deployment manifests and the activation procedure are maintained in
[the infrastructure guide](../../infrastructure/longhorn/README.md).
The Argo CD Application uses manual synchronization; existing application
volumes are not migrated by installing this component.
