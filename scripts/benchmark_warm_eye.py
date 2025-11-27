#!/usr/bin/env python3
"""Benchmark: Cold vs Warm EYE Reasoner Performance.

Compares latency between:
- Cold: Fresh subprocess each reasoning call
- Warm: Pre-warmed process pool with cached rules

Usage:
    python scripts/benchmark_warm_eye.py

Example Output:
    ╔══════════════════════════════════════════════════════╗
    ║       EYE Reasoner Performance Benchmark             ║
    ╠══════════════════════════════════════════════════════╣
    ║ Cold Start:    82.3ms avg (10 iterations)            ║
    ║ Warm Start:    14.7ms avg (10 iterations)            ║
    ║ Speedup:       5.6x                                  ║
    ╚══════════════════════════════════════════════════════╝
"""

from __future__ import annotations

import subprocess
import tempfile
import time
import os
import sys
from dataclasses import dataclass
from shutil import which
from statistics import mean, stdev

# Add src to path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "src"))


@dataclass
class BenchmarkResult:
    """Results from benchmark run."""
    name: str
    times_ms: list[float]

    @property
    def avg_ms(self) -> float:
        return mean(self.times_ms)

    @property
    def std_ms(self) -> float:
        return stdev(self.times_ms) if len(self.times_ms) > 1 else 0.0

    @property
    def min_ms(self) -> float:
        return min(self.times_ms)

    @property
    def max_ms(self) -> float:
        return max(self.times_ms)


SAMPLE_RULES = """
@prefix kgc: <https://kgc.org/ns/> .
@prefix yawl: <http://www.yawlfoundation.org/yawlschema#> .

# WCP-1 Sequence
{
    ?task kgc:status "Completed" .
    ?task yawl:flowsInto ?flow .
    ?flow yawl:nextElementRef ?next .
    ?next kgc:status "Pending" .
}
=>
{
    ?next kgc:status "Active" .
} .
"""

SAMPLE_STATE = """
@prefix kgc: <https://kgc.org/ns/> .
@prefix yawl: <http://www.yawlfoundation.org/yawlschema#> .

<urn:task:A> a yawl:Task ;
    kgc:status "Completed" ;
    yawl:flowsInto <urn:flow:1> .

<urn:flow:1> yawl:nextElementRef <urn:task:B> .

<urn:task:B> a yawl:Task ;
    kgc:status "Pending" .
"""


def benchmark_cold(iterations: int = 10) -> BenchmarkResult:
    """Benchmark cold subprocess invocations."""
    times = []

    for i in range(iterations):
        # Write temp files each time (simulates cold start)
        state_fd, state_path = tempfile.mkstemp(suffix=".ttl", text=True)
        rules_fd, rules_path = tempfile.mkstemp(suffix=".n3", text=True)

        try:
            with os.fdopen(state_fd, "w") as f:
                f.write(SAMPLE_STATE)
            with os.fdopen(rules_fd, "w") as f:
                f.write(SAMPLE_RULES)

            start = time.perf_counter()
            subprocess.run(
                ["eye", "--nope", "--pass", "--quiet", state_path, rules_path],
                capture_output=True,
                text=True,
                timeout=30,
            )
            duration_ms = (time.perf_counter() - start) * 1000
            times.append(duration_ms)

        finally:
            os.unlink(state_path)
            os.unlink(rules_path)

    return BenchmarkResult(name="Cold Start", times_ms=times)


def benchmark_warm(iterations: int = 10) -> BenchmarkResult:
    """Benchmark warm reasoner with cached rules."""
    from kgcl.hybrid.warm_eye_reasoner import WarmEYEReasoner, WarmEYEConfig

    config = WarmEYEConfig(pool_size=2, auto_warm=False)
    reasoner = WarmEYEReasoner(config, rules=SAMPLE_RULES)

    try:
        # Warm up (not counted in benchmark)
        reasoner.warm_up()

        # Warm iterations
        times = []
        for i in range(iterations):
            result = reasoner.reason(SAMPLE_STATE)
            times.append(result.duration_ms)

        return BenchmarkResult(name="Warm Start", times_ms=times)

    finally:
        reasoner.shutdown()


def print_results(cold: BenchmarkResult, warm: BenchmarkResult) -> None:
    """Print formatted benchmark results."""
    speedup = cold.avg_ms / warm.avg_ms if warm.avg_ms > 0 else 0

    print()
    print("╔" + "═" * 58 + "╗")
    print("║" + "       EYE Reasoner Performance Benchmark".center(58) + "║")
    print("╠" + "═" * 58 + "╣")
    print("║" + f" Cold Start:  {cold.avg_ms:6.1f}ms avg ± {cold.std_ms:5.1f}ms ({len(cold.times_ms)} iterations)".ljust(58) + "║")
    print("║" + f"              min={cold.min_ms:.1f}ms, max={cold.max_ms:.1f}ms".ljust(58) + "║")
    print("║" + " ".ljust(58) + "║")
    print("║" + f" Warm Start:  {warm.avg_ms:6.1f}ms avg ± {warm.std_ms:5.1f}ms ({len(warm.times_ms)} iterations)".ljust(58) + "║")
    print("║" + f"              min={warm.min_ms:.1f}ms, max={warm.max_ms:.1f}ms".ljust(58) + "║")
    print("║" + " ".ljust(58) + "║")
    print("║" + f" 🚀 Speedup:  {speedup:.1f}x faster with warm reasoner".ljust(58) + "║")
    print("║" + f" 💾 Savings:  {cold.avg_ms - warm.avg_ms:.1f}ms per reasoning call".ljust(58) + "║")
    print("╚" + "═" * 58 + "╝")
    print()


def main() -> None:
    """Run benchmark."""
    if not which("eye"):
        print("ERROR: EYE reasoner not found. Install from https://github.com/eyereasoner/eye")
        sys.exit(1)

    print("Running EYE Reasoner Performance Benchmark...")
    print()

    iterations = 10

    print(f"[1/2] Benchmarking cold start ({iterations} iterations)...")
    cold = benchmark_cold(iterations)

    print(f"[2/2] Benchmarking warm start ({iterations} iterations)...")
    warm = benchmark_warm(iterations)

    print_results(cold, warm)


if __name__ == "__main__":
    main()
