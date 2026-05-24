# AIOps Lab: Phase 1 Setup & Deployment Guide

## Prerequisites

Ensure you have:
- Docker running (or a container runtime accessible to Kubernetes)
- kubectl configured and pointing to a valid cluster
- Kubernetes cluster with at least 1 CPU and 512Mi free memory
- metrics-server installed (optional but recommended for Phase 2)

---

## Step 1: Start Docker (if not running)

### macOS (Docker Desktop)

```bash
# If Docker isn't running, start it:
open -a Docker

# Or via Homebrew:
brew services start colima  # if using Colima instead of Docker Desktop

# Verify Docker is running:
docker ps
```

### Linux

```bash
sudo systemctl start docker
docker ps  # Verify
```

---

## Step 2: Build the Image

From the AIOps directory:

```bash
cd /Users/smritisrivastava/Desktop/AIOps

# Build the image
docker build -t oom-leak-demo:latest .

# Verify the image exists
docker images | grep oom-leak-demo
```

**Expected output:**
```
REPOSITORY       TAG       IMAGE ID      CREATED        SIZE
oom-leak-demo    latest    abc1234567    X seconds ago   ~200MB
```

---

## Step 3: Verify Kubernetes Context

```bash
# Check current cluster
kubectl config current-context

# Verify cluster is accessible
kubectl get nodes

# Check if there's a default namespace
kubectl get namespace
```

---

## Step 4: Make Image Accessible to Kubernetes

### Option A: Load Image into Minikube/Kind (Local)

If you're using **Minikube**:
```bash
eval $(minikube docker-env)
docker build -t oom-leak-demo:latest .
```

If you're using **Kind**:
```bash
kind load docker-image oom-leak-demo:latest --name <cluster-name>
```

### Option B: Push to Registry (GCR, DockerHub, etc.)

```bash
# Tag for registry
docker tag oom-leak-demo:latest <registry>/<project>/oom-leak-demo:latest

# Login and push
docker login
docker push <registry>/<project>/oom-leak-demo:latest

# Update deployment YAML to use the pushed image:
# image: <registry>/<project>/oom-leak-demo:latest
```

### Option C: Use HostPath Mount (Development Only)

If your cluster runs on the same machine, you can use `imagePullPolicy: IfNotPresent` in the Deployment (already set in our manifest).

---

## Step 5: Deploy to Kubernetes

```bash
# Apply the deployment
kubectl apply -f k8s/deployment-oom-test.yaml

# Verify it was created
kubectl get deployment oom-leak-demo
kubectl get pods -l app=oom-leak-demo
```

---

## Step 6: Watch Phase 1 Unfold

### Terminal 1: Watch Pod State in Real Time

```bash
kubectl get pods -w
```

Expected progression:
```
NAME                              READY   STATUS              RESTARTS   AGE
oom-leak-demo-abc123def          0/1     Pending             0          2s
oom-leak-demo-abc123def          0/1     ContainerCreating   0          3s
oom-leak-demo-abc123def          1/1     Running             0          5s
oom-leak-demo-abc123def          0/1     OOMKilled           0          30s
oom-leak-demo-abc123def          0/1     CrashLoopBackOff    1          35s
oom-leak-demo-abc123def          1/1     Running             1          50s  (restart after backoff)
oom-leak-demo-abc123def          0/1     OOMKilled           1          75s  (hits OOM again)
...
```

### Terminal 2: Watch Memory Climb (if metrics-server available)

```bash
# Check if metrics-server is available
kubectl get deployment -n kube-system metrics-server

# If available, monitor memory:
watch -n 1 'kubectl top pod -l app=oom-leak-demo --containers'

# Or just run once:
kubectl top pod <POD_NAME> --containers
```

### Terminal 3: Describe Pod and Follow Events

```bash
kubectl describe pod -l app=oom-leak-demo --watch

# Or for a specific pod once you know the name:
kubectl describe pod <POD_NAME>
```

### Terminal 4: Tail the Logs

```bash
kubectl logs -l app=oom-leak-demo --follow

# Or view logs from the previous (terminated) container:
kubectl logs <POD_NAME> --previous
```

---

## Step 7: Verify Against Predictions

Once you see the failure pattern, check [PHASE1-PREDICTIONS.md](PHASE1-PREDICTIONS.md):

- [ ] Pod transitions to CrashLoopBackOff within 30 seconds?
- [ ] Restart count increments (1, 2, 3...)?
- [ ] OOM is visible in `kubectl describe pod` under "Last State → Reason: OOMKilled"?
- [ ] Logs show memory allocation climbing?
- [ ] Exit code is 137?

If all checkmarks pass, move to Phase 2 (Investigation).

---

## Step 8: Stop the Lab (Clean Up)

Once you've observed enough:

```bash
# Delete the deployment (stops pod creation)
kubectl delete deployment oom-leak-demo

# Or just delete the pods (Deployment will recreate them)
kubectl delete pods -l app=oom-leak-demo
```

---

## Troubleshooting

### "ImagePullBackOff" Error

The image isn't accessible to the cluster. Solutions:
1. If using Minikube: Make sure you ran `eval $(minikube docker-env)` before building
2. If using Kind: Use `kind load docker-image` to load the image
3. If using a remote cluster: Push to a registry and update the Deployment's `image` field

### "No resources found" After apply

```bash
kubectl apply -f k8s/deployment-oom-test.yaml

# Check for errors:
kubectl get events --sort-by='.lastTimestamp'
```

### metrics-server Not Available

Skip `kubectl top pod` monitoring. You'll still see logs and describe output, which is sufficient.

---

## Next: Phase 2 Investigation

Once Phase 1 is complete and the failure pattern is confirmed, follow [PHASE2-INVESTIGATION.md](PHASE2-INVESTIGATION.md) to diagnose the issue methodically.
