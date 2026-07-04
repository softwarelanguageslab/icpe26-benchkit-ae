#!/usr/bin/env python3
# Copyright (C) 2024 Vrije Universiteit Brussel. All rights reserved.
# SPDX-License-Identifier: MIT
"""
Figure 5 Experiment: perf-stat analysis for LevelDB with schedulers.

Paper reference:
    Section 4.3 (Using perf for Profiling and Run-Time Statistics), Figure 5.

What this script does:
    Runs LevelDB readrandom at 24 threads under six scheduling policies while
    collecting hardware performance counters via `perf stat`. The campaign
    produces a 5-panel bar chart: throughput, context-switches, cpu-migrations,
    page-faults, and cache-misses.

    Each policy is run 3 times for 30 seconds, with perf stat collecting
    system-wide events. The PerfStatWrap wrapper and its post-run hook
    handle perf invocation and result parsing automatically.

Hardware used in the paper:
    Platform B - NUMA server (2x Kunpeng 920-4826, 96 cores across 4 NUMA
    nodes, 539 GiB RAM, Ubuntu 20.04.6 LTS, kernel 5.4.0-200-generic, aarch64).

Expected execution time:
    ~10 minutes (6 schedulers x 3 runs x 30 s = 540 s).
    Measured on paper hardware: real 9m58s.

Prerequisites:
    - System packages: build-essential, cmake, libsnappy-dev, linux-tools-*
    - Perf access: sudo sysctl -w kernel.perf_event_paranoid=-1
    - Python environment set up (see README)

How to run:
    cd experiments/
    python figure5_leveldb_perfstat.py

Output:
    - CSV results and bar-plots (PNG/PDF) in ~/.benchkit/results/
    - Five bar plots: throughput + four perf-stat metrics, one bar per scheduler
"""

import argparse

from benchkit import CampaignCartesianProduct
from benchkit.benches.leveldb import LevelDBBench
from benchkit.commandwrappers.perf import PerfStatWrap, enable_non_sudo_perf

from lib import PRETTY_SCHEDULERS, SCHEDULERS, get_platform, get_scheduler
from lib.plots import load_campaign_df, perfstat_barplot, set_paper_style

# ---- User-tunable defaults (paper values) ----
DEFAULT_NB_THREADS = 24
DEFAULT_NB_RUNS = 3
DEFAULT_DURATION_S = 30


def run(
    *,
    nb_threads: int = DEFAULT_NB_THREADS,
    nb_runs: int = DEFAULT_NB_RUNS,
    duration_s: int = DEFAULT_DURATION_S,
    paper_fonts: bool = False,
) -> None:
    platform = get_platform()

    # Enable perf without sudo (best-effort)
    enable_non_sudo_perf(comm_layer=platform.comm)

    schedkit = get_scheduler(platform=platform)

    # Configure perf stat
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
        name="figure5_leveldb_perfstat",
        benchmark=LevelDBBench(),
        variables={
            "nb_threads": [nb_threads],
            "bench_name": ["readrandom"],
            "scheduler": SCHEDULERS,
        },
        pretty={"scheduler": PRETTY_SCHEDULERS},
        nb_runs=nb_runs,
        duration_s=duration_s,
        command_wrappers=[perf_stat],
        pre_run_hooks=[schedkit.start_sched_hook],
        post_run_hooks=[
            schedkit.end_sched_hook,
            perf_stat.post_run_hook_update_results,
        ],
        platform=platform,
    )

    campaign.run()

    # Paper-styled per-metric bar grid (Figure 5): throughput + perf-stat counters.
    # Use the short raw scheduler names (Normal/FAR/CLOSE/AsymSched/SAM/SAS) as in the
    # paper -- the long PRETTY_SCHEDULERS labels overflow this dense multi-panel grid.
    set_paper_style(use_latex=paper_fonts)
    df = load_campaign_df(campaign)
    perfstat_barplot(
        df,
        group_col="scheduler",
        out_path=campaign.base_data_dir() / "figure5_leveldb_perfstat.pdf",
    )

    print("\nResults saved to: ~/.benchkit/results/")


def main() -> None:
    parser = argparse.ArgumentParser(
        description="Figure 5: perf-stat analysis for LevelDB across schedulers.",
    )
    parser.add_argument(
        "--nb-threads",
        type=int,
        default=DEFAULT_NB_THREADS,
        help=f"Number of benchmark threads (default: {DEFAULT_NB_THREADS}).",
    )
    parser.add_argument(
        "--nb-runs",
        type=int,
        default=DEFAULT_NB_RUNS,
        help=f"Repetitions per scheduler (default: {DEFAULT_NB_RUNS}).",
    )
    parser.add_argument(
        "--duration-s",
        type=int,
        default=DEFAULT_DURATION_S,
        help=f"Duration in seconds per run (default: {DEFAULT_DURATION_S}).",
    )
    parser.add_argument(
        "--paper-fonts",
        action="store_true",
        help="Use LaTeX fonts for exact paper typography (requires a LaTeX install).",
    )
    args = parser.parse_args()
    run(
        nb_threads=args.nb_threads,
        nb_runs=args.nb_runs,
        duration_s=args.duration_s,
        paper_fonts=args.paper_fonts,
    )


if __name__ == "__main__":
    main()
