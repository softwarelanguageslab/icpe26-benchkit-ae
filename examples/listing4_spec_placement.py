#!/usr/bin/env python3
# Copyright (C) 2024 Vrije Universiteit Brussel. All rights reserved.
# SPDX-License-Identifier: MIT
"""
Listing 4: benchkit campaign using TasksetWrap to enforce core placement (SPEC CPU 2017).

Paper reference:
    Section 3.3 (Controlled Placement with taskset), Listing 4.

What this script does:
    Same placement experiment as listing4_leveldb_placement.py but uses the
    SPEC CPU 2017 500.perlbench benchmark. Three placement conditions are
    compared: No Pinning, P-Cores only, E-Cores only.

    IMPORTANT: Requires a valid SPEC CPU 2017 license and ISO image.
    For an open-source alternative, use listing4_leveldb_placement.py instead.

Hardware used in the paper:
    Platform A - hybrid-core laptop (AMD Ryzen AI 9 HX 370, 12 cores, 24 threads).
    Adjust P_CORES / E_CORES for your hardware (use listing3_heater.py to identify).

Expected execution time:
    ~5-10 minutes with size="test", ~90-120 minutes with size="ref".

Prerequisites:
    - SPEC CPU 2017 ISO image (e.g., cpu2017-1.1.9.iso)
    - System packages: build-essential, cmake, fuseiso
    - Python environment set up (see README)
    - Adjust P_CORES / E_CORES constants for your CPU

How to run:
    cd examples/
    python listing4_spec_placement.py /path/to/cpu2017-1.1.9.iso

Output:
    - CSV results and a strip-plot (PNG/PDF) in ~/.benchkit/results/
    - Strip plot shows runtime variability across placements
"""

import argparse
import sys
from pathlib import Path

from benchkit import CampaignCartesianProduct
from benchkit.benches.speccpu2017 import SPECCPU2017Bench
from benchkit.commandwrappers.taskset import TasksetWrap

# CPU configuration for AMD Ryzen AI 9 HX 370
# Adjust these for your specific hybrid-core processor.
# Use listing3_heater.py to identify P-cores (high throughput) vs E-cores (lower throughput).
P_CORES = [0, 1, 2, 3, 12, 13, 14, 15]
E_CORES = [4, 5, 6, 7, 8, 9, 10, 11, 16, 17, 18, 19, 20, 21, 22, 23]


def main() -> None:
    parser = argparse.ArgumentParser(
        description="Listing 4: SPEC CPU 2017 placement experiment with TasksetWrap.",
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
        name="listing4_placement_spec",
        benchmark=SPECCPU2017Bench(),
        variables={
            "spec_source_iso": [spec_iso],
            "bench_name": ["500.perlbench"],
            # "size": ["ref"],
            "size": ["test"],
            "cpu_list": {
                "no_pinning": [],  # Let the scheduler decide
                "p_cores": P_CORES,  # Pin to P-cores only
                "e_cores": E_CORES,  # Pin to E-cores only
            },
        },
        command_wrappers=[TasksetWrap(set_all_cpus=True)],
        nb_runs=10,
        pretty={
            "cpu_list": {
                "__category__": "CPU Placement",
                "no_pinning": "No Pinning",
                "p_cores": "P-Cores",
                "e_cores": "E-Cores",
            },
            "operations/second": "Throughput (ops/s)",
            "duration_s": "Runtime (s)",
        },
    )

    campaign.run()

    campaign.generate_graph(
        plot_name="stripplot",
        x="CPU Placement",
        y="Runtime (s)",
        hue="CPU Placement",
        title="SPEC CPU 2017 perlbench - runtime variability by placement",
    )


if __name__ == "__main__":
    main()
