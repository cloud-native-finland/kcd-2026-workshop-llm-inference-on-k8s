#!/usr/bin/env bash
# Tear down your group's vLLM deployment. Leaves the cluster and the
# shared infra (kube-prom-stack, KEDA) alone — the cluster admin will
# clean those up after the workshop.
set -euo pipefail
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
REPO_ROOT="$(cd "$SCRIPT_DIR/.." && pwd)"

: "${MY_NAMESPACE:?set MY_NAMESPACE to your assigned group namespace}"

kubectl -n "$MY_NAMESPACE" delete -f "$REPO_ROOT/helm/keda-scaled-object.yaml" --ignore-not-found
helm uninstall vllm -n "$MY_NAMESPACE" --ignore-not-found
kubectl -n "$MY_NAMESPACE" get pvc -o name 2>/dev/null | grep vllm | xargs -r kubectl -n "$MY_NAMESPACE" delete

echo
echo "Cleaned up vLLM in $MY_NAMESPACE."
