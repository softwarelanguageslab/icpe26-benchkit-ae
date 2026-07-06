#!/usr/bin/env python3
# Copyright (C) 2024 Vrije Universiteit Brussel. All rights reserved.
# SPDX-License-Identifier: MIT
"""
Listing 1: Example benchkit campaign for LevelDB.

Paper reference:
    Section 2.3 (Example), Listing 1.

What this script does:
    Demonstrates the basic structure of a benchkit campaign:
    - Define a benchmark (LevelDBBench, see `deps/benchkit/benchkit/benches/leveldb/__init__.py`)
    - Define a parameter space (bench_name x nb_threads)
    - Create a campaign that explores all combinations (cartesian product)
    - Run the campaign and generate a line-plot visualization

    The campaign runs two LevelDB micro-benchmarks (readrandom, seekrandom)
    across three thread counts (2, 4, 8), with 3 repetitions per configuration
    and 10-second duration per run.

Hardware used in the paper:
    Any Linux machine (no specific hardware requirement for this example).

Expected execution time:
    ~5 minutes (2 benchmarks x 3 thread counts x 3 runs x 10 s = 180 s
    + build/fetch overhead on first run).

Prerequisites:
    - System packages: build-essential, cmake, libsnappy-dev
    - Python environment set up (see README)

How to run (with venv enabled):
    cd examples/
    python listing1_leveldb.py

Output:
    - CSV results and a line-plot (PNG/PDF) in ~/.benchkit/results/
    - Plot shows throughput (ops/s) vs. thread count, one line per benchmark
"""

from benchkit import CampaignCartesianProduct
from benchkit.benches.leveldb import LevelDBBench


def main() -> None:
    # Define the parameter space to explore
    parameter_space = {
        "bench_name": ["readrandom", "seekrandom"],
        "nb_threads": [2, 4, 8],
    }

    # Create a campaign that runs all combinations
    campaign = CampaignCartesianProduct(
        name="listing1_leveldb",
        benchmark=LevelDBBench(),
        variables=parameter_space,
        nb_runs=3,
        duration_s=10,
    )

    # Execute the campaign
    campaign.run()

    # Generate a line plot of the results
    campaign.generate_graph(
        plot_name="lineplot",
        x="nb_threads",
        y="throughput",
        hue="bench_name",
        title="LevelDB - throughput by thread count",
    )


if __name__ == "__main__":
    main()
