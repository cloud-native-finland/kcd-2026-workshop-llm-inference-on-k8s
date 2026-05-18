#!/usr/bin/env bash
# Sanity-check the attendee's laptop and cluster access before the workshop.
set -euo pipefail

fail=0
need() {
  local cmd="$1" hint="$2"
  if command -v "$cmd" >/dev/null 2>&1; then
    printf "  ✓ %-10s %s\n" "$cmd" "$($cmd --version 2>&1 | head -1 || true)"
  else
    printf "  ✗ %-10s MISSING — %s\n" "$cmd" "$hint"
    fail=1
  fi
}

echo "== Tools =="
need kubectl  "https://kubernetes.io/docs/tasks/tools/"
need helm     "https://helm.sh/docs/intro/install/"
need python3  "your distro's python3 package"
need curl     "your distro's curl package"
need jq       "your distro's jq package"

echo
echo "== Cluster reachability =="
if kubectl cluster-info >/dev/null 2>&1; then
  echo "  ✓ kubectl can reach the cluster"
  kubectl get nodes
else
  echo "  ✗ kubectl cannot reach the cluster — check your kubeconfig"
  fail=1
fi

echo
echo "== Your namespace =="
if [[ -z "${MY_NAMESPACE:-}" ]]; then
  echo "  ✗ MY_NAMESPACE is not set. Run:  export MY_NAMESPACE=group-XX"
  fail=1
else
  if kubectl -n "$MY_NAMESPACE" auth can-i create deployments >/dev/null 2>&1; then
    echo "  ✓ you can create Deployments in $MY_NAMESPACE"
  else
    echo "  ✗ you cannot create Deployments in $MY_NAMESPACE — wrong namespace?"
    fail=1
  fi
fi

echo
echo "== Cluster-wide infra =="
if kubectl -n monitoring get svc kube-prom-stack-grafana >/dev/null 2>&1; then
  echo "  ✓ Grafana service is up in the monitoring namespace"
else
  echo "  ⚠ Grafana service not found — observability scenarios won't work"
fi
if kubectl get crd scaledobjects.keda.sh >/dev/null 2>&1; then
  echo "  ✓ KEDA CRDs are installed"
else
  echo "  ⚠ KEDA CRDs missing — Scenario 2 autoscaling won't work"
fi

echo
echo "== GPU capacity =="
gpu_count=$(kubectl get nodes -o jsonpath='{range .items[*]}{.status.allocatable.nvidia\.com/gpu}{"\n"}{end}' 2>/dev/null | awk '{ s+=$1 } END { print s+0 }')
if [[ "$gpu_count" -gt 0 ]]; then
  echo "  ✓ ${gpu_count} GPU(s) available in cluster"
else
  echo "  ✗ no nvidia.com/gpu reported by any node — vLLM will stay Pending"
  fail=1
fi

echo
if (( fail )); then
  echo "Some checks failed. Fix the items above before continuing."
  exit 1
fi
echo "All checks passed. Run ./scripts/01-deploy.sh next."
