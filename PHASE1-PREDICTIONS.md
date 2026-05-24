# Phase 1: OOM Failure — Prediction Notes

**Date:** 24 May 2026  
**Lab Goal:** Deploy a Kubernetes pod intentionally designed to hit OOMKilled within 60–120 seconds, then predict and observe its behavior before moving to diagnostic Phase 2.

---

## Application Design

**Memory Leak Script:** `src/memory_leak.py`
- Allocates 5MB per iteration
- Sleeps 0.5s between iterations
- Effective allocation rate: ~10MB/s
- No error handling — will keep allocating until kernel kills it

**Container Memory Limit:** 256Mi
- With 10MB/s allocation, should hit limit in ~25-30 seconds
- Request: 128Mi (half the limit, to pass initial scheduling)

**Deployment Type:** Kubernetes Deployment (not bare Pod)
- `replicas: 1`
- `restartPolicy: Always` (default)
- No liveness/readiness probes (intentional)

---

## Prediction: Pod State Timeline

### What I expect to see (write down BEFORE observing):

```
T+0s:   Pod created, state = Pending
T+1-3s: Pod scheduled, pulled image, state = ContainerCreating
T+3-5s: Container started, app begins allocating memory
        State = Running, Restarts = 0

T+5-30s: Memory allocation climbing
         APP OUTPUT: "Iteration 1 | Total allocated: 5.0MB"
         APP OUTPUT: "Iteration 2 | Total allocated: 10.0MB"
         ... continues ...
         APP OUTPUT: "Iteration 25 | Total allocated: 125.0MB"

T+25-30s: Memory pressure hits 256Mi limit
          Kernel (cgroup OOM killer) terminates container
          Pod state transitions: Running → (brief pause)

T+30-35s: Pod enters CrashLoopBackOff cycle
          Reason: OOMKilled
          Last Exit Code: 137 (killed by signal 9)
          Restart count increments: Restarts = 1, 2, 3, ...

T+35+:   Deployment's RestartPolicy respects backoff
         Expected restart delays: 0s, 1s, 2s, 4s, 8s, 16s, 30s...
         (Kubernetes default exponential backoff, capped at 5 min)
```

### Observable State Transitions

| Time Window | State | Key Indicators | What It Means |
|-------------|-------|---|---|
| T+0-2s | Pending | Image pull in progress | Scheduler has assigned the pod |
| T+2-5s | ContainerCreating | Layer downloads, OCI spec setup | Image is being loaded into container runtime |
| T+5-30s | Running | `kubectl top pod` shows RAM climbing | App is healthy and executing; memory allocation in progress |
| T+25-30s | Running → OOMKilled | Kernel OOM signal sent to PID 1 | Cgroup memory.max exceeded, process killed with SIGKILL |
| T+30-35s | CrashLoopBackOff | Pod Restarts increments | Deployment detects failure, waits backoff interval, recreates pod |
| T+35+ | CrashLoopBackOff | State repeats | Pattern persists every 5-30s until manually stopped |

---

## Critical Signals to Identify in Phase 2

When investigating, I will look for these exact diagnostic markers:

1. **Pod status:** `Status: CrashLoopBackOff` → confirms repeated failure
2. **Restart count:** `Restarts: 5+` after a few minutes → confirms pattern
3. **Last state reason:** `Reason: OOMKilled` (NOT `Crash`, `Error`, or `Unknown`)
4. **Exit code:** `137` (signal 9 = SIGKILL from cgroup OOM)
5. **Event log:** "OOMKilled — memory limit exceeded"
6. **Previous logs:** `kubectl logs --previous` shows final memory value before termination

**The Single Definitive Signal:** Exit code 137 + Reason: OOMKilled in `kubectl describe pod` output. This combination proves "the kernel killed this, not the app crashing."

---

## Tuning Parameters (if prediction doesn't match reality)

If the pod dies **too fast** (in seconds):
- Increase container memory limit to 512Mi
- Reduce allocation rate to 2–3MB per iteration

If the pod doesn't die **within 30s**:
- Reduce sleep time to 0.2s
- Increase allocation per iteration to 10MB

If the pod **restarts immediately** (no backoff visible):
- Check if probes are restarting it faster than we expect
- Adjust `restartPolicy` or check kubelet logs

---

## Next Steps

1. **Build the Docker image:**
   ```bash
   docker build -t oom-leak-demo:latest .
   ```

2. **Apply the Deployment:**
   ```bash
   kubectl apply -f k8s/deployment-oom-test.yaml
   ```

3. **Watch the failure in real time:**
   ```bash
   kubectl get pods -w
   ```

4. **In another terminal, monitor detailed events:**
   ```bash
   kubectl describe pod <pod-name> --watch
   ```

5. **Once failure is confirmed, move to Phase 2 (investigation).**

---

## Confidence Level

**High confidence** this will work as predicted because:
- Memory allocation is deterministic (10MB/s is linear and predictable)
- Kubernetes OOM handling is well-defined (signal 137, cgroup-based)
- 256Mi limit is strict and enforced by the kernel, not the container runtime
- CrashLoopBackOff is the default behavior for pods that fail repeatedly

The main variable: whether the restart backoff is visible or if the Deployment recreates pods too fast. Expected to see backoff clearly starting at iteration 2–3.
