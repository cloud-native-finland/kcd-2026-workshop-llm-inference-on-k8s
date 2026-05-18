# Grafana dashboards

We don't ship custom dashboards in this repo. The chart's
`grafanaDashboards.enabled: true` flag (set in
[`../helm/values-workshop.yaml`](../helm/values-workshop.yaml)) deploys two
ConfigMaps with the label `grafana_dashboard: "1"` **into your group's
namespace**:

- **vLLM** — TTFT, throughput, queue depth, KV cache usage, prefix-cache hits
- **LMCache** — KV cache offloading (idle in this workshop since we disabled
  LMCache)

The cluster's Grafana (in the `monitoring` namespace) runs a sidecar
configured by the workshop infra repo to search **all** namespaces for
ConfigMaps with that label and import them on the fly. So after running
`scripts/01-deploy.sh` they appear in Grafana under
**Dashboards → General** within a minute.

If you want to export one to JSON for your own use:

```bash
kubectl -n "$MY_NAMESPACE" get cm -l grafana_dashboard=1 -o yaml > dashboards.yaml
```

Upstream sources:
<https://github.com/vllm-project/production-stack/tree/main/helm/dashboards>
