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
if kubectl -n monitoring get svc grafana >/dev/null 2>&1; then
  echo "  ✓ Grafana service is up in the monitoring namespace"
else
  echo "  ⚠ Grafana service not found — observability scenarios won't work"
fi
if kubectl -n monitoring get svc gmp-frontend >/dev/null 2>&1; then
  echo "  ✓ GMP query frontend is up"
else
  echo "  ⚠ GMP frontend not found — KEDA scaling and Grafana queries won't work"
fi
if kubectl get crd scaledobjects.keda.sh >/dev/null 2>&1; then
  echo "  ✓ KEDA CRDs are installed"
else
  echo "  ⚠ KEDA CRDs missing — Scenario 2 autoscaling won't work"
fi

echo
echo "== GPU capacity =="
# On GKE Autopilot, GPU nodes are created on-demand when a Pod requests
# them. Before anyone has deployed vLLM, no GPU nodes exist — that's
# expected, not an error. Check the ComputeClass instead, which tells
# us the cluster *can* provision an L4 on demand.
if kubectl get computeclass.cloud.google.com vllm-gpu-l4-spot >/dev/null 2>&1; then
  echo "  ✓ vllm-gpu-l4-spot ComputeClass is installed"
else
  echo "  ⚠ vllm-gpu-l4-spot ComputeClass missing — vLLM pods will stay Pending"
fi

echo
if (( fail )); then
  echo "Some checks failed. Fix the items above before continuing."
  exit 1
fi
echo "All checks passed. Run ./scripts/01-deploy.sh next."
