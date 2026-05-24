#!/usr/bin/env python3
"""
Memory leak simulator for Kubernetes OOM learning lab.

This script intentionally allocates memory in a loop to trigger OOMKilled.
The goal is to observe Kubernetes behavior during pod termination and restart.

Configuration:
  - ALLOCATION_SIZE: bytes per iteration (default: 5MB)
  - SLEEP_TIME: seconds between allocations (default: 0.5s)
  - This results in ~10MB/second allocation, hitting 256Mi limit in ~25-30 seconds
"""

import time
import sys

ALLOCATION_SIZE = 5 * 1024 * 1024  # 5MB per iteration
SLEEP_TIME = 0.5  # seconds between allocations

def main():
    print(f"[memory_leak] Starting memory leak simulation", flush=True)
    print(f"[memory_leak] Allocation size: {ALLOCATION_SIZE / 1024 / 1024:.1f}MB per iteration", flush=True)
    print(f"[memory_leak] Sleep time: {SLEEP_TIME}s between allocations", flush=True)
    print(f"[memory_leak] Expected OOMKill in ~25-30 seconds with 256Mi limit", flush=True)
    print(f"[memory_leak] Allocation will grow unbounded — this is intentional", flush=True)
    print("", flush=True)
    
    memory_pool = []
    iteration = 0
    
    try:
        while True:
            iteration += 1
            # Allocate a chunk of memory
            chunk = bytearray(ALLOCATION_SIZE)
            memory_pool.append(chunk)
            
            total_mb = (iteration * ALLOCATION_SIZE) / 1024 / 1024
            print(f"[memory_leak] Iteration {iteration:4d} | Total allocated: {total_mb:7.1f}MB", flush=True)
            
            time.sleep(SLEEP_TIME)
    except MemoryError as e:
        print(f"[memory_leak] MemoryError caught: {e}", flush=True)
        sys.exit(1)
    except KeyboardInterrupt:
        print(f"[memory_leak] Interrupted by user", flush=True)
        sys.exit(0)

if __name__ == "__main__":
    main()
