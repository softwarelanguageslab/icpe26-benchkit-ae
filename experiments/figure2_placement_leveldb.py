#!/usr/bin/env python3
# Copyright (C) 2024 Vrije Universiteit Brussel. All rights reserved.
# SPDX-License-Identifier: MIT
"""
Figure 2 Experiment (left panel, open-source alternative): Hybrid-core variability.

Paper reference:
    Section 3.3 (Controlled Placement with taskset), Figure 2 (left).

What this script does:
    Reproduces the placement experiment from Figure 2 (left) using LevelDB as
    an open-source alternative to SPEC CPU 2017 perlbench_r. It runs LevelDB
    readrandom under three CPU placements (No Pinning, P-Cores, E-Cores) with
    100 repetitions each, producing a strip plot that shows throughput variability.

    The paper's Figure 2 (left) uses SPEC CPU 2017 - see figure2_placement_spec.py for that
    version (requires a SPEC license). This script demonstrates the same
    methodology and benchkit features without proprietary dependencies.

Hardware used in the paper:
    Platform A - hybrid-core laptop (AMD Ryzen AI 9 HX 370, 4 P-cores + 8
    E-cores, 12 cores / 24 threads, 32 GiB RAM, Manjaro 26.0.1, Linux 6.18+).
    Adjust P_CORES / E_CORES for your hardware. Run examples/listing3_heater.py
    first to identify which cores are P vs. E.

Expected execution time:
    ~5 minutes (3 placements x 100 runs, each run is short: 40 000 iterations).

Prerequisites:
    - System packages: build-essential, cmake, libsnappy-dev
    - Python environment set up (see README)
    - Adjust P_CORES / E_CORES constants below for your CPU

How to run:
    cd experiments/
    python figure2_placement_leveldb.py

Output:
    - CSV results and a strip-plot (PNG/PDF) in ~/.benchkit/results/
    - Strip plot shows throughput by CPU placement condition
"""

import argparse

from benchkit import CampaignCartesianProduct
from benchkit.benches.leveldb import LevelDBBench
from benchkit.commandwrappers.taskset import TasksetWrap

from lib.plots import load_campaign_df, set_paper_style, stripplot_by_category

# Placement display order (matches benchkit's auto-generated `cpu_list_pretty` column,
# built from the campaign's `pretty` mapping below).
_PLACEMENT_LABELS = {"no_pinning": "No Pinning", "p_cores": "P-Cores", "e_cores": "E-Cores"}

# CPU configuration for AMD Ryzen AI 9 HX 370
# Adjust these for your specific hybrid-core processor.
# Use listing3_heater.py to identify P-cores (high throughput) vs E-cores (lower throughput).
P_CORES = [0, 1, 2, 3, 12, 13, 14, 15]
E_CORES = [4, 5, 6, 7, 8, 9, 10, 11, 16, 17, 18, 19, 20, 21, 22, 23]

# ---- User-tunable defaults (paper values) ----
DEFAULT_NB_RUNS = 100
DEFAULT_NB_ITERATIONS = 40000


def run(
    *,
    nb_runs: int = DEFAULT_NB_RUNS,
    nb_iterations: int = DEFAULT_NB_ITERATIONS,
    p_cores: list[int] = P_CORES,
    e_cores: list[int] = E_CORES,
    paper_fonts: bool = False,
) -> None:
    campaign = CampaignCartesianProduct(
        name="figure2_placement_leveldb",
        benchmark=LevelDBBench(),
        variables={
            "bench_name": ["readrandom"],
            "nb_threads": [1],
            "nb_iterations": [nb_iterations],
            "cpu_list": {
                "no_pinning": [],  # Let the scheduler decide
                "p_cores": p_cores,  # Pin to P-cores only
                "e_cores": e_cores,  # Pin to E-cores only
            },
        },
        command_wrappers=[TasksetWrap(set_all_cpus=True)],
        nb_runs=nb_runs,
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

    # Paper-styled placement strip plot (Figure 2, left panel). Use benchkit's
    # auto-generated `cpu_list_pretty` column (No Pinning / P-Cores / E-Cores).
    set_paper_style(use_latex=paper_fonts)
    df = load_campaign_df(campaign)
    stripplot_by_category(
        df,
        x="cpu_list_pretty",
        y="throughput",
        order=list(_PLACEMENT_LABELS.values()),
        ylabel="Throughput (ops/s)",
        title="Throughput by CPU Order",
        rotate_xticks=45,
        out_path=campaign.base_data_dir() / "figure2_placement_leveldb.pdf",
    )


def main() -> None:
    parser = argparse.ArgumentParser(
        description="Figure 2 (left, open-source): LevelDB placement variability.",
    )
    parser.add_argument(
        "--nb-runs",
        type=int,
        default=DEFAULT_NB_RUNS,
        help=f"Repetitions per placement condition (default: {DEFAULT_NB_RUNS}).",
    )
    parser.add_argument(
        "--nb-iterations",
        type=int,
        default=DEFAULT_NB_ITERATIONS,
        help=f"LevelDB iterations per run (default: {DEFAULT_NB_ITERATIONS}).",
    )
    parser.add_argument(
        "--paper-fonts",
        action="store_true",
        help="Use LaTeX fonts for exact paper typography (requires a LaTeX install).",
    )
    args = parser.parse_args()
    run(nb_runs=args.nb_runs, nb_iterations=args.nb_iterations, paper_fonts=args.paper_fonts)


if __name__ == "__main__":
    main()
