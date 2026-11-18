#!/usr/bin/env bash
# Requires authorization to change the live cluster. No pruning is requested.
set -euo pipefail

application=${1:-}
case "$application" in
  longhorn-admission|longhorn|longhorn-pilot) ;;
  *) echo "Usage: bash $0 {longhorn-admission|longhorn|longhorn-pilot}" >&2; exit 2 ;;
esac

application_file=$(mktemp)
patch_file=$(mktemp)
trap 'rm -f "$application_file" "$patch_file"' EXIT

kubectl get application "$application" -n argocd -o json > "$application_file"
if ! yq -e '.operation == null' "$application_file" >/dev/null; then
  echo "$application already has a pending operation; leave it unchanged." >&2
  exit 1
fi
if [[ "$application" != longhorn-pilot ]]; then
  yq -e '(.spec.syncPolicy.syncOptions // []) | index("ServerSideApply=true") != null' \
    "$application_file" >/dev/null
fi

yq -c '[
  {op:"test",path:"/metadata/resourceVersion",value:.metadata.resourceVersion},
  {op:"add",path:"/operation",value:{
    initiatedBy:{username:"kubectl"},
    sync:{prune:false,syncOptions:(.spec.syncPolicy.syncOptions // [])}
  }}
]' "$application_file" > "$patch_file"
kubectl patch application "$application" -n argocd --type=json --patch-file "$patch_file"
