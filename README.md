# k3services

## NAS dynamic storage

The `nfs-provisioner` infrastructure application runs the NFS subdirectory
provisioner in the `nfs-provisioner` namespace. It uses the NFS export
`198.168.10.100:/Pi-NAS` and provides the `nfs-client` StorageClass.

Each PVC using that StorageClass receives its own directory on the NAS. For
example, an application can request storage with:

```yaml
apiVersion: v1
kind: PersistentVolumeClaim
metadata:
  name: my-app-data
spec:
  accessModes:
    - ReadWriteMany
  storageClassName: nfs-client
  resources:
    requests:
      storage: 10Gi
```

The StorageClass is not the cluster default. Existing workloads therefore keep
their current storage behavior unless they explicitly request `nfs-client`.
Persistent volumes use `Retain`, so deleting a PVC does not delete its NAS data.
