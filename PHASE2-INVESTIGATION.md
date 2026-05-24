# Phase 2: OOM Diagnosis — Investigation Playbook

**Phase 2 Goal:** Act like a detective. Before fixing anything, run diagnostic commands in sequence and log exactly what each one tells you. Build the investigation playbook your AIOps system will later automate.

---

## Investigation Sequence

### Stage 1: Identify the Failure Pattern

#### Command 1: Watch Pod State in Real Time
```bash
kubectl get pods -w
```

**What to log:**
- Timestamp when state changes to CrashLoopBackOff
- Restart count progression (1, 2, 3...)
- Age of the pod between restarts
- Whether the pod stays in CrashLoopBackOff or briefly returns to Running

**What this tells you:**
- Confirms repeated failure (not a one-off crash)
- Shows restart backoff is working
- Confirms pod isn't stuck in an infinite create loop

**Detective question:** Is this a pattern (repeats regularly) or a one-time crash?

---

#### Command 2: Get Detailed Pod Description
```bash
kubectl describe pod <POD_NAME>
```

**What to log (copy the entire output):**
- Pod metadata (Name, Namespace, Age)
- Current state (Status: CrashLoopBackOff)
- Restart count and last restart timestamp
- Container state: `Last State` section
  - `Reason: OOMKilled` (THE GOLD SIGNAL)
  - `Exit Code: 137` (signal SIGKILL)
  - `Finished: <timestamp>`
- Current state: `State` section
- `Events` section (scroll to end for most recent):
  - Pulls, Starts, and most importantly: termination events
  - Look for: "Memory limit exceeded" or "OOMKilled" in event messages

**What this tells you:**
- Definitive proof this is an OOM, not a config error or code bug
- Shows container lifecycle: created → running → killed → restarting
- Event log is the official Kubernetes record of what happened

**Detective question:** Does `Reason: OOMKilled` appear? If yes, your diagnosis is confirmed. If no, investigate further (might be a different failure mode).

---

#### Command 3: Retrieve the Dead Container's Logs
```bash
kubectl logs <POD_NAME> --previous
```

**What to log:**
- Full output (all lines showing memory allocation progression)
- Last line before termination (shows how much memory was allocated)
- Look for the app's stdout/stderr (our memory_leak.py script prints iterations)

**What this tells you:**
- Application-level view of what was happening before death
- Shows memory growth trajectory from the app's perspective
- Confirms the leak is intentional (allocation line shows it climbing)

**Detective question:** Does the log show continuous allocation, or does it stop abruptly? Continuous = OOM killed the app mid-allocate. Abrupt silence = app crashed or process exited.

---

### Stage 2: Real-Time Memory Monitoring

#### Command 4: Watch Memory Usage in Real Time (if metrics-server available)
```bash
# First, check if metrics-server exists:
kubectl get deployment -n kube-system metrics-server

# If present, watch memory climb:
kubectl top pod <POD_NAME> --containers
```

**What to log:**
- Current memory usage (MB/MiB)
- Memory limit (should show 256Mi)
- Timestamp when memory reaches 80% of limit (~200Mi)
- Timestamp when memory hits 95%+ of limit
- Final memory reading before OOMKilled

**What this tells you:**
- Real-time confirmation of memory pressure
- Shows whether app is linear or bursty in allocation
- Can calculate rate of growth (MB/second)

**Detective question:** Is memory climbing linearly or in bursts? Is there any plateau near the limit, or does it hit instantly?

---

### Stage 3: Analyze the Evidence

#### Summary Table: Fill This In

| Metric | Value | Source | Interpretation |
|--------|-------|--------|---|
| Pod Status | | `kubectl get pods` | |
| Restart Count | | `kubectl describe pod` | |
| Last State Reason | | `kubectl describe pod` | |
| Exit Code | | `kubectl describe pod` | |
| Memory Used at Death | | `kubectl top` or logs | |
| Memory Limit | | `kubectl describe pod` | |
| Time to OOMKill | | Logs timestamp range | |
| Allocation Rate | | (Memory / Time) | |

**Diagnostic Decision Tree:**

```
Is Exit Code = 137 AND Reason = OOMKilled?
├─ YES → This is definitely an OOM failure
│   └─ Is the allocation in logs continuous and unbounded?
│       ├─ YES → Memory leak confirmed
│       │   └─ Auto-remediation is risky (raising limit won't fix a leak)
│       │   └─ Recommendation: Page human or rate-limit future fixes
│       │
│       └─ NO → Transient memory spike
│           └─ Auto-remediation (raise limit) may be appropriate
│           └─ Recommendation: Review app startup, can add cleanup
│
└─ NO → Not an OOM
    └─ Exit Code ≠ 137 → Check exit code reason
    └─ Reason ≠ OOMKilled → Check crash logs with kubectl logs --previous
    └─ App error detected → Different failure mode, return to develop
```

---

## Manual Remediation Tests

### Test A: Raise the Memory Limit (Does Fixing the Symptom Work?)

**Hypothesis:** If we increase the memory limit, the pod will survive longer but eventually still OOMKill (because the app leaks forever).

```bash
# Edit the deployment to increase memory limit to 1Gi:
kubectl set resources deployment oom-leak-demo --limits=memory=1Gi

# Watch what happens:
kubectl get pods -w

# After failure:
kubectl logs <POD_NAME> --previous | tail -20
```

**What to observe:**
- Does the pod stay Running longer? (If so, how much longer?)
- Does it eventually still OOMKill? (Confirms it's a leak, not a threshold issue)
- Is the final allocation value higher?

**Detective insight:** If raising the limit just delays death, you have a leak. The fix isn't "raise limits," it's "fix the app or alert on human review."

---

### Test B: Restart the Pod (Time-Buy vs. Fix)

```bash
# Delete the pod to force restart:
kubectl delete pod <POD_NAME>

# Watch the new instance:
kubectl get pods -w

# Check if it survives or repeats:
kubectl describe pod <POD_NAME> | grep -A 5 "Last State"
```

**What to observe:**
- New pod starts fresh (Restarts counter resets or increments?)
- Does it immediately start accumulating again?
- Time until next OOMKill (should be similar to first failure if deterministic)

**Detective insight:** Restart is just a time-buy. It doesn't fix the underlying leak; it just resets the memory counter.

---

### Test C: Review If This Should Be Auto-Fixed or Escalated

**Decision Checklist:**

```
☐ Is the failure deterministic? (Same app, same time to OOMKill?)
☐ Is it a real leak? (Memory climbing without bound in app logs?)
☐ Can the limit be raised safely? (Will it just delay failure?)
☐ Is the app code fixable by a human? (Check src/memory_leak.py)

Action:
├─ If all ☑, this is a learning lab — DON'T auto-fix
├─ If real leak, auto-remediation should not raise limits forever
│   └─ Instead: Log incident, page human, stop restarting pod
│
└─ If transient spike, raising limit might be appropriate
    └─ But add monitoring to detect repeated spikes
```

---

## Questions to Answer After Investigation

1. **What single data point proves this is an OOM?**
   - Answer: Exit Code 137 + Reason: OOMKilled

2. **How can you distinguish OOM from other crashes?**
   - Answer: Check `Reason` field in `kubectl describe pod`. Only OOM will show `OOMKilled`.

3. **What would a human need to know to fix this?**
   - Answer: App logs showing allocation + Exit Code 137 + Memory limit in manifest

4. **Would raising the memory limit fix this?**
   - Answer: No. The app leaks memory forever. Raising the limit just delays failure.

5. **What should an automated system do in this case?**
   - Answer: Alert/page a human instead of auto-escalating the limit. The fix is to stop allocating memory in the app (or restart as a manual intervention).

---

## Transition to Automated Diagnosis

Once you've answered these questions by hand, you'll build an automated detector that:

1. Watches for Exit Code 137 + Reason: OOMKilled
2. Retrieves previous logs to check for unbounded allocation
3. Calculates allocation rate and time to OOMKill
4. Decides: Is this a leak (escalate) or a spike (can raise limit)?
5. Takes remediation action accordingly

This Phase 2 playbook becomes the spec for your AIOps automation in later phases.
