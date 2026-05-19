#!/usr/bin/env bash
# Deploy vLLM into your group's namespace.
#
# The cluster admin has pre-installed KEDA + Grafana + GKE Managed
# Prometheus cluster-wide, plus the vllm-stack CRDs (LoraAdapter). You
# only deploy the vLLM engine + router and the per-namespace
# autoscaling/alerts/PDB artifacts — hence `--skip-crds` below, since
# participants don't have cluster-scoped permissions.
#
# Required:
#   MY_NAMESPACE   your assigned group namespace (e.g. group-alpha)

set -euo pipefail
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
REPO_ROOT="$(cd "$SCRIPT_DIR/.." && pwd)"

: "${MY_NAMESPACE:?set MY_NAMESPACE to your assigned group namespace}"

echo "== Deploying vLLM into namespace: $MY_NAMESPACE =="

helm repo add vllm https://vllm-project.github.io/production-stack >/dev/null 2>&1 || true
helm repo update vllm >/dev/null

helm upgrade --install vllm vllm/vllm-stack \
  --namespace "$MY_NAMESPACE" \
  --skip-crds \
  -f "$REPO_ROOT/helm/values-workshop.yaml" \
  --wait --timeout 15m

echo
echo "== KEDA ScaledObject (autoscaling on queue depth) =="
kubectl -n "$MY_NAMESPACE" apply -f "$REPO_ROOT/helm/keda-scaled-object.yaml"

echo
echo "== GMP Rules (alerts on queue depth + engine readiness) =="
kubectl -n "$MY_NAMESPACE" apply -f "$REPO_ROOT/helm/gmp-rules.yaml"

echo
echo "== PodDisruptionBudget (engine stays up during voluntary disruptions) =="
kubectl -n "$MY_NAMESPACE" apply -f "$REPO_ROOT/helm/pdb.yaml"

echo
echo "== Resources in $MY_NAMESPACE =="
kubectl -n "$MY_NAMESPACE" get pods,svc,scaledobject,rules.monitoring.googleapis.com,pdb 2>&1 | head -20

echo
echo "Next steps:"
echo "  MY_NAMESPACE=$MY_NAMESPACE ./scripts/02-port-forward.sh   # open router + Grafana"
echo "  MY_NAMESPACE=$MY_NAMESPACE ./scripts/03-smoke-test.sh     # verify it serves requests"
