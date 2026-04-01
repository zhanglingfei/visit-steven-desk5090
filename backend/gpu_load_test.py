#!/usr/bin/env python3
"""Simple GPU load test script that runs for 20 seconds."""

import torch
import time

def gpu_load_test(duration_secs=20):
    """Run a GPU-intensive computation for the specified duration."""

    if not torch.cuda.is_available():
        print("CUDA not available. Running on CPU instead.")
        device = torch.device("cpu")
    else:
        device = torch.device("cuda")
        print(f"GPU: {torch.cuda.get_device_name(0)}")
        print(f"Duration: {duration_secs} seconds")

    # Large matrices for computation
    size = 5000
    a = torch.randn(size, size, device=device)
    b = torch.randn(size, size, device=device)

    print(f"Running matrix multiplications on {device}...")
    start_time = time.time()
    iterations = 0

    while time.time() - start_time < duration_secs:
        # Matrix multiplication is GPU-intensive
        c = torch.matmul(a, b)
        # Synchronize to ensure GPU is actually doing work
        if device.type == "cuda":
            torch.cuda.synchronize()
        iterations += 1

    elapsed = time.time() - start_time
    print(f"\nCompleted {iterations} iterations in {elapsed:.2f} seconds")
    print(f"Average: {iterations / elapsed:.1f} iterations/sec")

    if device.type == "cuda":
        print(f"Peak memory allocated: {torch.cuda.max_memory_allocated() / 1e9:.2f} GB")

if __name__ == "__main__":
    gpu_load_test(20)
