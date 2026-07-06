#!/usr/bin/env python3
# Copyright (C) 2024 Vrije Universiteit Brussel. All rights reserved.
# SPDX-License-Identifier: MIT
"""
Listing 4 (variant): benchkit campaign using TasksetWrap to enforce core placement (LevelDB).

Paper reference:
    Section 3.3 (Controlled Placement with taskset), Listing 4 (open-source variant).

What this script does:
    Demonstrates how to use the TasksetWrap command wrapper to control CPU
    placement declaratively. The wrapper injects `taskset` commands around
    the benchmark invocation. Three placement conditions are compared:
      - No Pinning: default Linux scheduler placement
      - P-Cores: pinned to performance cores only
      - E-Cores: pinned to efficiency cores only

    This is the open-source (LevelDB) variant of the placement experiment.
    For the SPEC CPU 2017 variant shown in the paper, see listing4_spec_placement.py.

Hardware used in the paper:
    Platform A - hybrid-core laptop (AMD Ryzen AI 9 HX 370, 12 cores, 24 threads).
    The P_CORES and E_CORES lists below must be adjusted for your hardware.
    Run listing3_heater.py first to identify which cores are fast (P) vs. slow (E).
    On a homogeneous machine, all three conditions will yield similar results.

Expected execution time:
    ~20 minutes (3 placements x 100 runs; each run executes 40 000 iterations).

Prerequisites:
    - System packages: build-essential, cmake, libsnappy-dev
    - Python environment set up (see README)
    - Adjust P_CORES / E_CORES constants below for your CPU

How to run:
    cd examples/
    python listing4_leveldb_placement.py

Output:
    - CSV results and a strip-plot (PNG/PDF) in ~/.benchkit/results/
    - Strip plot shows throughput variability across placements
"""

from benchkit import CampaignCartesianProduct
from benchkit.benches.leveldb import LevelDBBench
from benchkit.commandwrappers.taskset import TasksetWrap

# CPU configuration for AMD Ryzen AI 9 HX 370
# Adjust these for your specific hybrid-core processor.
# Use listing3_heater.py to identify P-cores (high throughput) vs E-cores (lower throughput).
P_CORES = [0, 1, 2, 3, 12, 13, 14, 15]
E_CORES = [4, 5, 6, 7, 8, 9, 10, 11, 16, 17, 18, 19, 20, 21, 22, 23]


def main() -> None:
    campaign = CampaignCartesianProduct(
        name="listing4_placement_leveldb",
        benchmark=LevelDBBench(),
        variables={
            "bench_name": ["readrandom"],
            "nb_threads": [1],
            "nb_iterations": [40000],
            "cpu_list": {
                "no_pinning": [],  # Let the scheduler decide
                "p_cores": P_CORES,  # Pin to P-cores only
                "e_cores": E_CORES,  # Pin to E-cores only
            },
        },
        command_wrappers=[TasksetWrap(set_all_cpus=True)],
        nb_runs=100,
        pretty={
            "cpu_list": {
                "__category__": "CPU Placement",
                "no_pinning": "No Pinning",
                "p_cores": "P-Cores",
                "e_cores": "E-Cores",
            },
            "operations/second": "Throughput (ops/s)",
        },
    )

    campaign.run()

    campaign.generate_graph(
        plot_name="stripplot",
        x="CPU Placement",
        y="Throughput (ops/s)",
        hue="CPU Placement",
        title="LevelDB readrandom - throughput variability by placement",
    )


if __name__ == "__main__":
    main()
