#!/usr/bin/env python3
# Copyright (C) 2024 Vrije Universiteit Brussel. All rights reserved.
# SPDX-License-Identifier: MIT
"""
Listing 3: benchkit campaign sweeping all available CPUs for the sequential heater.

Paper reference:
    Section 3.2 (Sequential CPU-ID Characterization), Listing 3.

What this script does:
    Runs a simple compute-bound workload (sequential heater) pinned to each
    logical CPU in turn, measuring the number of arithmetic operations
    completed in a fixed time window. This reveals the relative speed of
    each core and exposes P-core vs. E-core asymmetry on hybrid processors.

    The heater is a tight C loop that counts operations while pinned via
    sched_setaffinity. benchkit sweeps all CPUs declaratively.

Hardware used in the paper:
    Platform A - hybrid-core laptop (AMD Ryzen AI 9 HX 370, 12 cores, 24 threads).
    Works on any Linux machine; results will reflect whatever core topology
    is present (homogeneous machines show a flat bar chart).

Expected execution time:
    ~3 minutes on a 24-thread machine (24 CPUs x 3 runs x 3 s ~= 216 s).
    Scales linearly with core count.

Prerequisites:
    - System packages: build-essential, cmake
    - Python environment set up (see README)

How to run:
    cd examples/
    python listing3_heater.py

Output:
    - CSV results and a bar-plot (PNG/PDF) in ~/.benchkit/results/
    - Bar plot shows operations per CPU, revealing P/E core clusters
"""

import os

from benchkit.benches.heater import heater_seq_campaign


def main() -> None:
    # Create a campaign that runs the heater on each CPU
    campaign = heater_seq_campaign(
        name="listing3_heater",
        nb_runs=3,
        duration_s=3,
        cpu=range(0, os.cpu_count()),
    )

    # Execute the campaign
    campaign.run()

    # Generate a bar plot showing per-CPU throughput
    campaign.generate_graph(
        plot_name="barplot",
        x="cpu",
        y="ops",
        title="Sequential heater - per-CPU throughput",
    )


if __name__ == "__main__":
    main()
