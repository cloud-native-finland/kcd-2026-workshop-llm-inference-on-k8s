# 6 — What's next

You've now seen the same engine under three completely different loads,
with the system itself telling you which knob matters for each. Same vLLM,
same Kubernetes, same Grafana — three very different operational stories.

## Beyond the Helm chart

The Production Stack is a great default, but it's one point in a much
larger design space. Worth knowing about:

### llm-d

[llm-d](https://llm-d.ai/) is a CNCF Sandbox project building a *platform*
for inference. The interesting ideas:

- **Disaggregated prefill/decode**: prefill is compute-bound, decode is
  memory-bound. Run them on different replica pools — bigger TP for
  prefill, smaller replicas for decode — and route between them.
- **Gateway API Inference Extension** (GA Feb 2026): standardises how
  inference traffic is described to a Gateway, the way the Gateway API
  did for HTTP. The router stops being a custom thing your serving stack
  ships, and starts being a property of the platform.
- **LeaderWorkerSet** for multi-node model parallelism — needed when the
  model is bigger than a single node's GPUs (Llama-3.1-405B, DeepSeek-V3,
  etc.).

When to reach for it: large-scale production, multi-node model parallelism,
or platforms where multiple teams share infrastructure and you want the
router to be the platform's responsibility, not the team's.

### KubeAI

[KubeAI](https://github.com/kubeai-project/kubeai) is an operator that
treats models as Kubernetes resources. You apply a `Model` CR; KubeAI
manages the backend (vLLM, llama.cpp, OpenAI passthrough…). Useful when
the inference engine isn't fixed — you want the same control plane for
vLLM, Ollama, and a managed API behind the same OpenAI endpoint.

### Where the ecosystem is heading

The big convergence story is **Gateway API for inference**. Today, every
serving stack ships its own router. Tomorrow, the router is the cluster's
Gateway, with inference-specific extensions standardised by SIG-Network.
That has knock-on effects:

- Routing logic (prefix-aware, KV-aware, model-aware) becomes a property
  of the Gateway, reusable across engines.
- The OpenAI API surface becomes the de-facto wire protocol for inference
  inside the cluster.
- Multi-tenant inference (model-as-a-service inside an org) becomes
  tractable without bespoke proxies.

## Things to try after the workshop

- Swap the model. Edit `helm/values-workshop.yaml`, change `modelURL` to
  e.g. `Qwen/Qwen2.5-1.5B-Instruct`, re-upload it to the GCS model bucket,
  `helm upgrade`. Watch the pod restart and a bigger model load.
- Turn `routingLogic` to `roundrobin` and re-run Scenario 1. You should
  see the prefix cache hit rate collapse — a great negative result.
- Set the KEDA `threshold` to `1` and re-run Scenario 2. KEDA becomes
  twitchier. Read the HPA describe output and see how it reasons.
- Export the bundled Grafana dashboard JSON from your namespace
  (`kubectl -n $MY_NAMESPACE get cm -l grafana_dashboard=1 -o yaml`),
  tweak a panel, re-apply. The sidecar reloads it within a minute.
- Try `kubectl -n $MY_NAMESPACE drain` against the GPU node and watch the
  PDB block the eviction. Scale the engine to 2 replicas first if you
  want it to succeed.

## Reading list

- [vLLM Production Stack — tutorials](https://github.com/vllm-project/production-stack/tree/main/tutorials)
- [vLLM docs — paged attention](https://docs.vllm.ai/en/latest/dev/kernel/paged_attention.html)
- [KEDA — autoscaling for K8s](https://keda.sh/)
- [llm-d](https://llm-d.ai/)
- [Gateway API Inference Extension](https://github.com/kubernetes-sigs/gateway-api-inference-extension)
- [KubeAI](https://github.com/kubeai-project/kubeai)

## Cleanup

Tear your slice down (keeps the shared cluster intact):

```bash
./scripts/99-teardown.sh
```

The cluster admin handles cluster teardown — out of your namespace's
reach.
