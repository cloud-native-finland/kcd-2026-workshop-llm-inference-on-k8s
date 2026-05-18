#!/usr/bin/env bash
# Open the port-forwards you need during the workshop. The router is in
# YOUR namespace; Grafana and the GMP query frontend are cluster-wide
# (in `monitoring`).
#
#   localhost:30080 → vLLM router (OpenAI-compatible API) — YOUR namespace
#   localhost:3000  → Grafana                              (admin / prom-operator)
#   localhost:9090  → GMP query frontend                   (Prometheus API on GMP)
#
# Ctrl-C to stop.

set -euo pipefail

: "${MY_NAMESPACE:?set MY_NAMESPACE to your assigned group namespace}"

cleanup() {
  jobs -p | xargs -r kill 2>/dev/null || true
}
trap cleanup EXIT INT TERM

echo "== Port-forwarding (Ctrl-C to stop) =="
kubectl -n "$MY_NAMESPACE" port-forward svc/vllm-router-service 30080:80 >/tmp/pf-router.log 2>&1 &
kubectl -n monitoring port-forward svc/grafana 3000:80 >/tmp/pf-grafana.log 2>&1 &
kubectl -n monitoring port-forward svc/gmp-frontend 9090:9090 >/tmp/pf-gmp.log 2>&1 &

sleep 2
echo
echo "  Router (OpenAI API):  http://localhost:30080   (namespace: $MY_NAMESPACE)"
echo "  Grafana:              http://localhost:3000   (admin / prom-operator)"
echo "  GMP frontend:         http://localhost:9090   (Prometheus API)"
echo
echo "Logs: /tmp/pf-router.log /tmp/pf-grafana.log /tmp/pf-gmp.log"
wait
