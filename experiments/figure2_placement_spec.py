#!/usr/bin/env python3
# Copyright (C) 2024 Vrije Universiteit Brussel. All rights reserved.
# SPDX-License-Identifier: MIT
"""
Figure 2 Experiment (left panel, SPEC): Hybrid-core variability with SPEC CPU 2017.

Paper reference:
    Section 3.1-3.3 (Benchmark Setup, Controlled Placement), Figure 2 (left).

What this script does:
    Reproduces the exact placement experiment from Section 3 of the paper using
    the SPEC CPU 2017 500.perlbench_r workload. It runs the benchmark under
    three placement conditions (No Pinning, P-Cores, E-Cores) with repeated
    executions, producing a strip plot showing runtime variability.

    IMPORTANT: Requires a valid SPEC CPU 2017 license and ISO image.
    For an open-source alternative, see figure2_placement_leveldb.py.

Hardware used in the paper:
    Platform A - hybrid-core laptop (AMD Ryzen AI 9 HX 370, 4 P-cores + 8
    E-cores, 12 cores / 24 threads, 32 GiB RAM, Manjaro 26.0.1, Linux 6.18+).
    Adjust P_CORES / E_CORES for your hardware.

Expected execution time:
    - size="ref" (default, paper values): ~90-120 minutes (10 runs per placement,
      each ~2 minutes) -- reproduces Section 3's ten repeated executions.
    - size="test" (quick, non-representative): ~5-10 minutes
      (use --size test --nb-runs 1000).

Prerequisites:
    - SPEC CPU 2017 ISO image (e.g., cpu2017-1.1.9.iso)
    - System packages: build-essential, cmake, fuseiso
    - Python environment set up (see README)
    - Adjust P_CORES / E_CORES constants for your CPU

How to run:
    cd experiments/
    python figure2_placement_spec.py /path/to/cpu2017-1.1.9.iso

Output:
    - CSV results and a strip-plot (PNG/PDF) in ~/.benchkit/results/
    - Strip plot shows runtime variability across placements
"""

import argparse
import os
import sys
from pathlib import Path

from benchkit import CampaignCartesianProduct
from benchkit.benches.speccpu2017 import SPECCPU2017Bench
from benchkit.commandwrappers.taskset import TasksetWrap

from lib import get_platform
from lib.plots import load_campaign_df, set_paper_style, stripplot_by_category

# Placement display order (matches benchkit's auto-generated `cpu_list_pretty` column,
# built from the campaign's `pretty` mapping below).
_PLACEMENT_LABELS = {"no_pinning": "No Pinning", "p_cores": "P-Cores", "e_cores": "E-Cores"}

# ---- User-tunable defaults -------------------------------------------------

DEFAULT_BENCH_NAME = "500.perlbench"
DEFAULT_SIZE = "ref"  # paper value; use "test" for quick, non-representative runs
DEFAULT_NB_RUNS = 10  # paper value: ten repeated executions (cf. Section 3)
P_CORES = [0, 1, 2, 3, 12, 13, 14, 15]
E_CORES = [4, 5, 6, 7, 8, 9, 10, 11, 16, 17, 18, 19, 20, 21, 22, 23]

DEFAULT_BENCHKIT_HOME = Path("~/.benchkit").expanduser().resolve()


def run_placement_experiment(
    *,
    spec_iso: Path,
    p_cores: list[int],
    e_cores: list[int],
    nb_runs: int = DEFAULT_NB_RUNS,
    bench_name: str = DEFAULT_BENCH_NAME,
    size: str = DEFAULT_SIZE,
    nb_threads: int = os.cpu_count(),
    benchkit_home: Path = DEFAULT_BENCHKIT_HOME,
    paper_fonts: bool = False,
):
    """
    Run the placement experiment: repeated benchmark runs under different CPU sets.

    Notes on wrappers/variables:
      - TasksetWrap(set_all_cpus=True) ensures taskset is available to pin, and
        benchkit can apply the cpu_order placement.
      - cpu_order is treated as an experimental variable: each value corresponds
        to a distinct placement condition to compare in plots.
    """
    platform = get_platform()

    benches_dir = benchkit_home / "benches"

    campaign = CampaignCartesianProduct(
        name="figure2_placement_spec",
        benchmark=SPECCPU2017Bench(),
        # Wrapper enabling CPU pinning; actual CPU list comes from variable cpu_order.
        command_wrappers=[TasksetWrap(set_all_cpus=True)],
        variables={
            "parent_dir": [benches_dir],
            "spec_source_iso": [spec_iso],
            "bench_name": [bench_name],
            "size": [size],
            "nb_threads": [nb_threads],
            # Each entry is one experimental condition (placement).
            "cpu_list": {
                "no_pinning": [],  # Let the scheduler decide
                "p_cores": p_cores,  # Pin to P-cores only
                "e_cores": e_cores,  # Pin to E-cores only
            },
        },
        pretty={
            "cpu_list": {
                "__category__": "CPU Placement",
                "no_pinning": "No Pinning",
                "p_cores": "P-Cores",
                "e_cores": "E-Cores",
            },
            "operations/second": "Throughput (ops/s)",
        },
        nb_runs=nb_runs,
        platform=platform,
    )

    campaign.run()

    # Paper-styled placement strip plot (Figure 2, left panel). Use benchkit's
    # auto-generated `cpu_list_pretty` column (No Pinning / P-Cores / E-Cores).
    set_paper_style(use_latex=paper_fonts)
    df = load_campaign_df(campaign)
    stripplot_by_category(
        df,
        x="cpu_list_pretty",
        y="duration_s",
        order=list(_PLACEMENT_LABELS.values()),
        ylabel="Runtime (sec)",
        title="Runtime by CPU Order",
        rotate_xticks=45,
        out_path=campaign.base_data_dir() / "figure2_placement_spec.pdf",
    )

    print(f"\nPlacement results saved to: {campaign.base_data_dir()}")
    return campaign


def main() -> None:
    parser = argparse.ArgumentParser(
        description="Figure 2 (left): SPEC CPU 2017 placement experiment.",
    )
    parser.add_argument(
        "spec_iso",
        type=Path,
        help="Path to the SPEC CPU 2017 ISO image (e.g., /path/to/cpu2017-1.1.9.iso)",
    )
    parser.add_argument(
        "--nb-runs",
        type=int,
        default=DEFAULT_NB_RUNS,
        help=f"Repetitions per placement condition (default: {DEFAULT_NB_RUNS}).",
    )
    parser.add_argument(
        "--bench-name",
        type=str,
        default=DEFAULT_BENCH_NAME,
        help=f"SPEC benchmark name (default: {DEFAULT_BENCH_NAME}).",
    )
    parser.add_argument(
        "--size",
        type=str,
        default=DEFAULT_SIZE,
        help=f'SPEC input size, e.g. "test" or "ref" (default: {DEFAULT_SIZE}).',
    )
    parser.add_argument(
        "--nb-threads",
        type=int,
        default=os.cpu_count(),
        help="Number of threads (default: all available CPUs).",
    )
    parser.add_argument(
        "--paper-fonts",
        action="store_true",
        help="Use LaTeX fonts for exact paper typography (requires a LaTeX install).",
    )
    args = parser.parse_args()

    spec_iso = args.spec_iso.expanduser().resolve()
    if not spec_iso.exists():
        print(f"Error: SPEC ISO not found: {spec_iso}", file=sys.stderr)
        sys.exit(1)

    run_placement_experiment(
        spec_iso=spec_iso,
        p_cores=P_CORES,
        e_cores=E_CORES,
        nb_runs=args.nb_runs,
        bench_name=args.bench_name,
        size=args.size,
        nb_threads=args.nb_threads,
        paper_fonts=args.paper_fonts,
    )

    print("\n" + "=" * 60)
    print("Figure 2 placement experiment complete!")
    print("=" * 60)


if __name__ == "__main__":
    main()
