# 1 — Deploy your vLLM stack

The cluster admin has already done the cluster-wide work for you:

- GKE cluster with mgmt + GPU node pools
- NVIDIA GPU driver
- kube-prometheus-stack (Prometheus + Grafana) in `monitoring`
- KEDA controller in `keda`
- Your group namespace + RBAC

You only deploy the vLLM Helm chart into your namespace.

## Set your namespace

You were assigned a namespace at the start of the workshop (e.g. `group-alpha`).
Export it once per terminal:

```bash
export MY_NAMESPACE=group-XX     # replace XX
```

Every script in this repo reads `MY_NAMESPACE`.

## Run the deploy

```bash
./scripts/01-deploy.sh
```

That script does just two things — read it before you run it, it's short:

1. `helm install vllm vllm/vllm-stack -n $MY_NAMESPACE -f helm/values-workshop.yaml`
2. `kubectl -n $MY_NAMESPACE apply -f helm/keda-scaled-object.yaml`

The slow part is the engine pod pulling the vLLM image (~12 GB) and
downloading the model weights. Give it a few minutes.

## Verify

```bash
kubectl -n $MY_NAMESPACE get pods
```

You should see two pods Ready:

```
vllm-deployment-router-xxxxx              1/1   Running
vllm-qwen05b-deployment-vllm-xxxxx        1/1   Running
```

Sanity-check that the engine actually got the GPU:

```bash
kubectl -n $MY_NAMESPACE get pod -l model=qwen05b \
  -o jsonpath='{.items[0].spec.containers[0].resources}' | jq
```

`"nvidia.com/gpu": "1"` should appear in both `requests` and `limits`.

Tail the engine logs while it's loading — a great way to see what vLLM is
doing at startup:

```bash
kubectl -n $MY_NAMESPACE logs -l model=qwen05b -f --tail=200
```

You're looking for:
- `Loading model weights took …` — model is in GPU memory
- `Available KV cache memory: …` — PagedAttention has carved the rest of the
  GPU into KV blocks
- `Started server process` — the OpenAI-compatible API is up

## Open the port-forwards

Leave this running in a separate terminal:

```bash
./scripts/02-port-forward.sh
```

- `localhost:30080` → your router (OpenAI-compatible API)
- `localhost:3000`  → Grafana (admin / prom-operator)
- `localhost:9090`  → Prometheus

## Smoke-test

```bash
./scripts/03-smoke-test.sh
```

If you get a model list, a completion, and a chat response back — congrats,
your slice of the workshop cluster is fully live.

Next: [02 — Observability](02-observability.md)
