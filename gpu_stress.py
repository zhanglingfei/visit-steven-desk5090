#!/usr/bin/env python3
"""Simple GPU stress test using PyTorch"""

import torch
import time

def stress_gpu(duration_seconds=120):
    print(f"Starting GPU stress test for {duration_seconds} seconds...")
    print(f"PyTorch version: {torch.__version__}")
    print(f"CUDA available: {torch.cuda.is_available()}")

    if not torch.cuda.is_available():
        print("CUDA not available! Falling back to CPU...")
        device = torch.device("cpu")
    else:
        device = torch.device("cuda")
        print(f"Using GPU: {torch.cuda.get_device_name(0)}")
        print(f"GPU Memory: {torch.cuda.get_device_properties(0).total_memory / 1e9:.2f} GB")

    # Large matrices for high GPU utilization
    size = 10000 if device.type == "cuda" else 5000

    print(f"\nRunning matrix operations on {device}...")
    start_time = time.time()

    while time.time() - start_time < duration_seconds:
        # Create large random matrices
        a = torch.randn(size, size, device=device)
        b = torch.randn(size, size, device=device)

        # Matrix multiplication (computationally intensive)
        c = torch.matmul(a, b)

        # Additional operations to increase utilization
        d = torch.sin(c) + torch.cos(c)
        e = torch.exp(d / 1000)  # Scale to avoid overflow

        # Force synchronization to ensure GPU is actually working
        if device.type == "cuda":
            torch.cuda.synchronize()

        elapsed = time.time() - start_time
        print(f"Elapsed: {elapsed:.1f}s / {duration_seconds}s", end="\r")

    print(f"\n\nCompleted! Total time: {time.time() - start_time:.1f} seconds")

if __name__ == "__main__":
    stress_gpu(120)
