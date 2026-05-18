# Grafana dashboards

We don't ship custom dashboards in this repo. The chart's
`grafanaDashboards.enabled: true` flag (set in
[`../helm/values-workshop.yaml`](../helm/values-workshop.yaml)) deploys three
ConfigMaps with the label `grafana_dashboard: "1"`:

- **vLLM** — TTFT, throughput, queue depth, KV cache usage, prefix-cache hits
- **vLLM model metrics** — per-model latency / throughput
- **LMCache** — KV cache offloading (idle in this workshop since we disabled
  LMCache)

`kube-prometheus-stack`'s Grafana runs a sidecar that watches for ConfigMaps
with that label and imports them on creation. So after running
`scripts/01-install-stack.sh` they appear in Grafana under
**Dashboards → vLLM Production Stack** within a minute.

If you want to export one to JSON for your own use:

```bash
kubectl -n monitoring get cm -l grafana_dashboard=1 -o yaml > dashboards.yaml
```

Upstream sources:
<https://github.com/vllm-project/production-stack/tree/main/helm/dashboards>
