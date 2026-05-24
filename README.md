# AIOps

AIOps project repository for automation and operations workflows. This lab focuses on building deterministic failure scenarios in Kubernetes and developing diagnostic playbooks for automated remediation.

## Phase 1: OOM Failure Lab

**Goal:** Deploy a Kubernetes pod that intentionally leaks memory and observe it hitting OOMKilled. Predict behavior before observing reality.

**Files:**
- [PHASE1-PREDICTIONS.md](PHASE1-PREDICTIONS.md) — Predictions of pod state transitions before deployment
- [DEPLOYMENT-GUIDE.md](DEPLOYMENT-GUIDE.md) — Step-by-step setup and deployment instructions
- [src/memory_leak.py](src/memory_leak.py) — The intentional memory leak application
- [Dockerfile](Dockerfile) — Container image definition
- [k8s/deployment-oom-test.yaml](k8s/deployment-oom-test.yaml) — Kubernetes Deployment manifest

**Quick Start:**
```bash
# 1. Build the Docker image
docker build -t oom-leak-demo:latest .

# 2. Deploy to Kubernetes
kubectl apply -f k8s/deployment-oom-test.yaml

# 3. Watch the failure
kubectl get pods -w
```

See [DEPLOYMENT-GUIDE.md](DEPLOYMENT-GUIDE.md) for detailed setup and troubleshooting.

---

## Phase 2: Manual Investigation

**Goal:** Act like a detective. Run diagnostic commands in sequence and build a playbook for what to check when an OOM failure occurs.

**Files:**
- [PHASE2-INVESTIGATION.md](PHASE2-INVESTIGATION.md) — Diagnostic commands and investigation sequence

**Key Commands:**
```bash
# Watch pod state transitions
kubectl get pods -w

# Get detailed pod info and last state reason
kubectl describe pod <pod-name>

# See logs from the dead container
kubectl logs <pod-name> --previous

# Monitor memory in real time (if metrics-server available)
kubectl top pod <pod-name> --containers
```

---

## Project Structure

```
├── src/                          # Source code
│   └── memory_leak.py           # Intentional memory leak app
├── k8s/                         # Kubernetes manifests
│   └── deployment-oom-test.yaml # OOM failure test deployment
├── Dockerfile                   # Container image definition
├── PHASE1-PREDICTIONS.md        # Phase 1: Predictions before deployment
├── PHASE2-INVESTIGATION.md      # Phase 2: Investigation playbook
├── DEPLOYMENT-GUIDE.md          # Setup and deployment instructions
├── README.md                    # This file
└── .gitignore                   # Git ignore rules
```

## Requirements

- Docker (for building images)
- Kubernetes cluster (Minikube, Kind, GKE, etc.)
- kubectl configured for your cluster
- metrics-server (optional, for real-time memory monitoring)

## Contributing

Investigation findings and remediation improvements are tracked in the phase documentation files.

## License

MIT
