#!/usr/bin/env python3
# Copyright (C) 2024 Vrije Universiteit Brussel. All rights reserved.
# SPDX-License-Identifier: MIT
"""
Listing 5: benchkit campaign for LevelDB with different lock implementations.

Paper reference:
    Section 4.1 (Studying Locking Impact), Listing 5.

What this script does:
    Demonstrates how to use shared libraries (via LD_PRELOAD) to inject
    different lock implementations into a benchmark without modifying its
    source code. The tilt library interposes pthread mutex
    calls and replaces them with the selected spinlock algorithm.

    Lock algorithms tested: CAS, TTAS, Ticket, MCS, Hemlock, CNA, HMCS,
    and the default glibc pthread_mutex baseline.

Hardware used in the paper:
    Platform B - NUMA server (2x Kunpeng 920-4826, 96 cores, aarch64).
    Works on any Linux machine; thread counts are automatically filtered
    to the number of available CPUs.

Expected execution time:
    ~15 minutes (8 locks x 7 thread counts x 3 runs x 10 s ~= 1680 s,
    reduced on machines with fewer than 32 cores).

Prerequisites:
    - System packages: build-essential, cmake, libsnappy-dev
    - Python environment set up (see README)
    - The tilt shared library is built automatically by the script

How to run:
    cd examples/
    python listing5_leveldb_locks.py

Output:
    - CSV results and a line-plot (PNG/PDF) in ~/.benchkit/results/
    - Line plot shows throughput vs. thread count, one line per lock
"""

from benchkit import CampaignCartesianProduct
from benchkit.benches.leveldb import LevelDBBench

from lib import LOCKS, get_platform, get_tilt_lib


def main() -> None:
    platform = get_platform()
    tiltlib = get_tilt_lib(platform=platform)

    campaign = CampaignCartesianProduct(
        name="listing5_leveldb_locks",
        benchmark=LevelDBBench(),
        shared_libs=[tiltlib],
        variables={
            "nb_threads": [1, 2, 4, 8, 16, 24, 32],
            "bench_name": ["readrandom"],
            "lock": LOCKS,
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
        hue="lock",
        title="LevelDB readrandom - throughput by lock",
    )


if __name__ == "__main__":
    main()
