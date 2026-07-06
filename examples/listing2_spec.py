#!/usr/bin/env python3
# Copyright (C) 2024 Vrije Universiteit Brussel. All rights reserved.
# SPDX-License-Identifier: MIT
"""
Listing 2: Example benchkit campaign for a SPEC single-threaded benchmark.

Paper reference:
    Section 3.1 (Benchmark Setup and Baseline Experiment), Listing 2.

What this script does:
    Demonstrates how to set up a SPEC CPU 2017 benchmark in benchkit and
    expose run-to-run variability on hybrid-core processors. The campaign
    runs 500.perlbench_r repeatedly under the default Linux scheduler. On
    hybrid-core machines, this produces multimodal runtimes because the OS
    scheduler may place the workload on either fast P-cores or slower E-cores.

    The resulting strip plot (Figure 2, left, "No Pinning" condition) shows
    the spread of runtimes, motivating the controlled placement experiment
    in Section 3.3 (Listing 4).

    IMPORTANT: Requires a valid SPEC CPU 2017 license and ISO image.

Hardware used in the paper:
    Platform A - hybrid-core laptop (AMD Ryzen AI 9 HX 370, 12 cores, 24 threads,
    32 GiB RAM, Manjaro 26.0.1, Linux 6.18+).

Expected execution time:
    - size="test" (default): ~5 minutes (10 short runs)
    - size="ref": ~30 minutes (10 runs, each ~2-3 minutes)

Prerequisites:
    - SPEC CPU 2017 ISO image (e.g., cpu2017-1.1.9.iso)
    - System packages: build-essential, cmake, fuseiso
    - Python environment set up (see README)

How to run:
    cd examples/
    python listing2_spec.py /path/to/cpu2017-1.1.9.iso

Output:
    - CSV results and a strip-plot (PNG/PDF) in ~/.benchkit/results/
    - Strip plot shows runtime variability under default scheduling
"""

import argparse
import sys
from pathlib import Path

from benchkit import CampaignCartesianProduct
from benchkit.benches.speccpu2017 import SPECCPU2017Bench


def main() -> None:
    parser = argparse.ArgumentParser(
        description="Listing 2: SPEC CPU 2017 baseline variability experiment.",
    )
    parser.add_argument(
        "spec_iso",
        type=Path,
        help="Path to the SPEC CPU 2017 ISO image (e.g., /path/to/cpu2017-1.1.9.iso)",
    )
    args = parser.parse_args()

    spec_iso = args.spec_iso.expanduser().resolve()
    if not spec_iso.exists():
        print(f"Error: SPEC ISO not found: {spec_iso}", file=sys.stderr)
        sys.exit(1)

    campaign = CampaignCartesianProduct(
        name="listing2_spec_baseline",
        benchmark=SPECCPU2017Bench(),
        variables={
            "spec_source_iso": [spec_iso],
            "bench_name": ["500.perlbench"],
            # "size": ["ref"],
            "size": ["test"],
        },
        nb_runs=10,
        pretty={
            "duration_s": "Runtime (s)",
        },
    )

    campaign.run()

    campaign.generate_graph(
        plot_name="stripplot",
        x="bench_name",
        y="Runtime (s)",
        title="SPEC CPU 2017 perlbench - runtime variability (no pinning)",
    )


if __name__ == "__main__":
    main()
