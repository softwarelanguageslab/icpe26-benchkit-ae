#!/usr/bin/env python3
# Copyright (C) 2024 Vrije Universiteit Brussel. All rights reserved.
# SPDX-License-Identifier: MIT
"""
Listing 7: benchkit campaign for LevelDB with different scheduling policies.

Paper reference:
    Section 4.2 (Studying Thread-Placement Impact), Listing 7.

What this script does:
    Demonstrates how to compose scheduling policies with benchmarks using
    pre/post run hooks. Before each run, the schedkit daemon
    is started with the policy drawn from the parameter space; after each
    run it is stopped. Six policies are compared: Normal (default Linux),
    FAR, CLOSE, AsymSched, SAM, and SAS.

Hardware used in the paper:
    Platform B - NUMA server (2x Kunpeng 920-4826, 96 cores, aarch64).
    Works on any Linux machine; on non-NUMA machines the NUMA-aware
    policies may not show meaningful differences.

Expected execution time:
    ~15 minutes (6 schedulers x 7 thread counts x 3 runs x 10 s ~= 1260 s).

Prerequisites:
    - System packages: build-essential, cmake, libsnappy-dev
    - Python environment set up (see README)
    - schedkit is built automatically

How to run:
    cd examples/
    python listing7_leveldb_schedulers.py

Output:
    - CSV results and a line-plot (PNG/PDF) in ~/.benchkit/results/
    - Line plot shows throughput vs. thread count, one line per scheduler
"""

from benchkit import CampaignCartesianProduct
from benchkit.benches.leveldb import LevelDBBench

from lib import PRETTY_SCHEDULERS, SCHEDULERS, get_platform, get_scheduler


def main() -> None:
    platform = get_platform()
    schedkit = get_scheduler(platform=platform)

    campaign = CampaignCartesianProduct(
        name="listing7_leveldb_schedulers",
        benchmark=LevelDBBench(),
        pre_run_hooks=[schedkit.start_sched_hook],
        post_run_hooks=[schedkit.end_sched_hook],
        variables={
            "nb_threads": [1, 2, 4, 8, 16, 24, 32],
            "bench_name": ["readrandom"],
            "scheduler": SCHEDULERS,
        },
        pretty={
            "scheduler": PRETTY_SCHEDULERS,
        },
        nb_runs=3,
        duration_s=10,
        platform=platform,
    )

    campaign.run()

    campaign.generate_graph(
        plot_name="lineplot",
        x="nb_threads",
        y="throughput",
        hue="scheduler",
        title="LevelDB readrandom - throughput by scheduler",
    )


if __name__ == "__main__":
    main()
