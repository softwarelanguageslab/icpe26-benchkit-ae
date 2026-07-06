#!/usr/bin/env python3
# Copyright (C) 2024 Vrije Universiteit Brussel. All rights reserved.
# SPDX-License-Identifier: MIT
"""
Figure 2 Experiment (right panel): Sequential heater per-CPU characterization.

Paper reference:
    Section 3.2 (Sequential CPU-ID Characterization), Figure 2 (right).

What this script does:
    Runs the sequential heater benchmark pinned to each logical CPU in turn,
    producing a bar chart of per-core throughput. On hybrid-core processors,
    this reveals two distinct plateaus corresponding to P-cores and E-cores.
    The resulting core-to-speed mapping is used to configure P_CORES / E_CORES
    for the placement experiments (figure2_placement_spec.py, figure2_placement_leveldb.py).

Hardware used in the paper:
    Platform A - hybrid-core laptop (AMD Ryzen AI 9 HX 370, 12 cores, 24 threads).
    Works on any Linux machine; homogeneous machines show a flat bar chart.

Expected execution time:
    ~3 minutes on a 24-thread machine (24 CPUs x 3 runs x 3 s = 216 s).

Prerequisites:
    - System packages: build-essential, cmake
    - Python environment set up (see README)

How to run:
    cd experiments/
    python figure2_heater.py

Output:
    - CSV results and a bar-plot (PNG/PDF) in ~/.benchkit/results/
    - Bar plot shows per-CPU operations count, revealing P/E core asymmetry
"""

import argparse
import os

from benchkit.benches.heater import heater_seq_campaign

from lib.plots import barplot_by_category, load_campaign_df, set_paper_style

# ---- User-tunable defaults (paper values) ----
DEFAULT_NB_RUNS = 3
DEFAULT_DURATION_S = 3


def run(
    *,
    nb_runs: int = DEFAULT_NB_RUNS,
    duration_s: int = DEFAULT_DURATION_S,
    paper_fonts: bool = False,
) -> None:
    # Create a campaign that runs the heater on each CPU
    campaign = heater_seq_campaign(
        name="figure2_heater",
        nb_runs=nb_runs,
        duration_s=duration_s,
        cpu=range(0, os.cpu_count()),
    )

    # Execute the campaign
    campaign.run()

    # Generate the paper-styled per-CPU bar chart (Figure 2, right panel)
    set_paper_style(use_latex=paper_fonts)
    df = load_campaign_df(campaign)
    barplot_by_category(
        df,
        x="cpu",
        y="ops",
        xlabel="CPU id",
        ylabel="Number of Operations",
        title="Sequential Heater",
        aspect=2.2,
        out_path=campaign.base_data_dir() / "figure2_heater.pdf",
    )


def main() -> None:
    parser = argparse.ArgumentParser(
        description="Figure 2 (right): sequential heater per-CPU characterization.",
    )
    parser.add_argument(
        "--nb-runs",
        type=int,
        default=DEFAULT_NB_RUNS,
        help=f"Number of repetitions per CPU (default: {DEFAULT_NB_RUNS}).",
    )
    parser.add_argument(
        "--duration-s",
        type=int,
        default=DEFAULT_DURATION_S,
        help=f"Duration in seconds of each heater run (default: {DEFAULT_DURATION_S}).",
    )
    parser.add_argument(
        "--paper-fonts",
        action="store_true",
        help="Use LaTeX fonts for exact paper typography (requires a LaTeX install).",
    )
    args = parser.parse_args()
    run(nb_runs=args.nb_runs, duration_s=args.duration_s, paper_fonts=args.paper_fonts)


if __name__ == "__main__":
    main()
