#!/usr/bin/env python3
# Copyright (C) 2024 Vrije Universiteit Brussel. All rights reserved.
# SPDX-License-Identifier: MIT
"""
Listing 8: benchkit campaign with perf stat integration.

Paper reference:
    Section 4.3 (Using perf for Profiling and Run-Time Statistics), Listing 8.

What this script does:
    Demonstrates how to combine scheduling policies with hardware performance
    counter collection using the PerfStatWrap command wrapper. The wrapper
    automatically prepends `perf stat` to the benchmark invocation and a
    post-run hook parses the output file to inject metrics (context-switches,
    cpu-migrations, page-faults, cache-misses) into the campaign results.

    The campaign runs LevelDB readrandom at 24 threads under all six
    scheduling policies, collecting both throughput and perf-stat metrics.

Hardware used in the paper:
    Platform B - NUMA server (2x Kunpeng 920-4826, 96 cores, aarch64).
    Works on any Linux machine with perf access.

Expected execution time:
    ~10 minutes (6 schedulers x 1 thread count x 3 runs x 30 s = 540 s).

Prerequisites:
    - System packages: build-essential, cmake, libsnappy-dev, linux-tools-*
    - Perf access: sudo sysctl -w kernel.perf_event_paranoid=-1
    - Python environment set up (see README)

How to run:
    cd examples/
    python listing8_leveldb_perfstat.py

Output:
    - CSV results and bar-plots (PNG/PDF) in ~/.benchkit/results/
    - Separate bar plots for throughput, cache-misses, context-switches
"""

# Note: Requires perf access. See README if you get permission errors.

from benchkit import CampaignCartesianProduct
from benchkit.benches.leveldb import LevelDBBench
from benchkit.commandwrappers.perf import PerfStatWrap, enable_non_sudo_perf

from lib import PRETTY_SCHEDULERS, SCHEDULERS, get_platform, get_scheduler


def main() -> None:
    platform = get_platform()

    # Enable perf without sudo (best-effort)
    enable_non_sudo_perf(comm_layer=platform.comm)

    schedkit = get_scheduler(platform=platform)

    # Configure perf stat to collect specific events
    perf_stat = PerfStatWrap(
        events=[
            "context-switches",
            "cpu-migrations",
            "page-faults",
            "cache-misses",
        ],
        use_json=False,
        separator=";",
        aggregate_hybrid=True,
    )

    campaign = CampaignCartesianProduct(
        name="listing8_leveldb_perfstat",
        benchmark=LevelDBBench(),
        variables={
            "nb_threads": [24],
            "bench_name": ["readrandom"],
            "scheduler": SCHEDULERS,
        },
        pretty={
            "scheduler": PRETTY_SCHEDULERS,
        },
        nb_runs=3,
        duration_s=30,
        command_wrappers=[perf_stat],
        pre_run_hooks=[schedkit.start_sched_hook],
        post_run_hooks=[
            schedkit.end_sched_hook,
            perf_stat.post_run_hook_update_results,
        ],
        platform=platform,
    )

    campaign.run()

    # Generate multiple plots for different metrics
    campaign.generate_graph(
        plot_name="barplot",
        x="scheduler",
        y="throughput",
        hue="scheduler",
        title="Throughput by Scheduler",
    )

    campaign.generate_graph(
        plot_name="barplot",
        x="scheduler",
        y="perf-stat/cache-misses",
        hue="scheduler",
        title="Cache Misses by Scheduler",
    )

    campaign.generate_graph(
        plot_name="barplot",
        x="scheduler",
        y="perf-stat/context-switches",
        hue="scheduler",
        title="Context Switches by Scheduler",
    )


if __name__ == "__main__":
    main()
