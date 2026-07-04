#!/usr/bin/env python3
# Copyright (C) 2024 Vrije Universiteit Brussel. All rights reserved.
# SPDX-License-Identifier: MIT
"""
Figure 4 Experiment: Scheduler throughput across KyotoCabinet, LevelDB, RocksDB.

Paper reference:
    Section 4.2 (Studying Thread-Placement Impact), Figure 4.

What this script does:
    Runs a comprehensive scheduler sweep across three key-value store benchmarks
    (KyotoCabinet, LevelDB, RocksDB) with two workloads each for LevelDB and
    RocksDB (readrandom, seekrandom), producing a 5-panel figure.

    Six scheduling policies are compared: Normal (default Linux), FAR, CLOSE,
    AsymSched, SAM, and SAS. Thread counts sweep from 1 to 96 (filtered to
    available CPUs). Each configuration is repeated 3 times for 10 seconds.

    The schedkit daemon is managed via pre/post-run hooks.

Hardware used in the paper:
    Platform B - NUMA server (2x Kunpeng 920-4826, 96 cores across 4 NUMA
    nodes, 539 GiB RAM, Ubuntu 20.04.6 LTS, kernel 5.4.0-200-generic, aarch64).

    On non-NUMA machines, the NUMA-aware policies may not show meaningful
    differences compared to the default Linux scheduler.

Expected execution time:
    Defaults reproduce the paper parameters (nb_runs=3, duration_s=10). A reduced
    run (--nb-runs 2 --duration-s 5) took ~96 minutes (real 95m26s) on the paper's
    96-core server; the default paper parameters take roughly 3x longer. Scales
    with core count and number of schedulers.

Prerequisites:
    - System packages: build-essential, cmake, libsnappy-dev, libgflags-dev,
      liblz4-dev, libzstd-dev, zlib1g-dev (for RocksDB)
    - Python environment set up (see README)

How to run:
    cd experiments/
    python figure4_schedulers.py

Output:
    - CSV results per panel and line-plots (PNG/PDF) in ~/.benchkit/results/
    - One line plot per panel: throughput vs. threads, one line per scheduler
"""

import argparse
from pathlib import Path

from benchkit import CampaignCartesianProduct
from benchkit.benches.kyotocabinet import KyotoCabinetBench
from benchkit.benches.leveldb import LevelDBBench
from benchkit.benches.rocksdb import RocksDBBench
from benchkit.campaign import CampaignSuite

from lib import PRETTY_SCHEDULERS, SCHEDULERS, Panel, get_platform, get_scheduler
from lib.plots import combine_panel_dfs, lineplot_by_bench, set_paper_style

# ---- User-tunable defaults (paper values) ----
# Defaults reproduce the paper plots (nb_runs=3, duration_s=10). For a quicker
# run, reduce them on the command line, e.g. --nb-runs 2 --duration-s 5.
DEFAULT_THREADS = [1, 2, 4, 8, 16, 24, 32, 64, 72, 80, 88, 96]
DEFAULT_NB_RUNS = 3
DEFAULT_DURATION_S = 10


def _int_list(text: str) -> list[int]:
    """Parse a comma-separated list of ints, e.g. '1,2,4,8'."""
    return [int(x) for x in text.split(",") if x.strip()]


def run(
    *,
    nb_runs: int = DEFAULT_NB_RUNS,
    duration_s: int = DEFAULT_DURATION_S,
    threads: list[int] | None = None,
    paper_fonts: bool = False,
) -> None:
    if threads is None:
        threads = DEFAULT_THREADS

    platform = get_platform()
    schedkit = get_scheduler(platform=platform)

    # Filter thread counts to available CPUs
    max_cpus = platform.nb_cpus()
    threads = [t for t in threads if t <= max_cpus]

    # Define the panels (one per benchmark/workload)
    panels = [
        Panel(
            name="kyotocabinet",
            campaign_name="figure4_kyotocabinet",
            bench=KyotoCabinetBench(),
            parameter_space={
                "nb_threads": threads,
                "scheduler": SCHEDULERS,
            },
        ),
        Panel(
            name="leveldb/readrandom",
            campaign_name="figure4_leveldb_readrandom",
            bench=LevelDBBench(),
            parameter_space={
                "nb_threads": threads,
                "bench_name": ["readrandom"],
                "scheduler": SCHEDULERS,
            },
        ),
        Panel(
            name="leveldb/seekrandom",
            campaign_name="figure4_leveldb_seekrandom",
            bench=LevelDBBench(),
            parameter_space={
                "nb_threads": threads,
                "bench_name": ["seekrandom"],
                "scheduler": SCHEDULERS,
            },
        ),
        Panel(
            name="rocksdb/readrandom",
            campaign_name="figure4_rocksdb_readrandom",
            bench=RocksDBBench(),
            parameter_space={
                "nb_threads": threads,
                "bench_name": ["readrandom"],
                "scheduler": SCHEDULERS,
            },
        ),
        Panel(
            name="rocksdb/seekrandom",
            campaign_name="figure4_rocksdb_seekrandom",
            bench=RocksDBBench(),
            parameter_space={
                "nb_threads": threads,
                "bench_name": ["seekrandom"],
                "scheduler": SCHEDULERS,
            },
        ),
    ]

    # Create campaigns for each panel
    campaigns = [
        CampaignCartesianProduct(
            name=p.campaign_name,
            benchmark=p.bench,
            pre_run_hooks=[schedkit.start_sched_hook],
            post_run_hooks=[schedkit.end_sched_hook],
            variables=p.parameter_space,
            pretty={"scheduler": PRETTY_SCHEDULERS},
            nb_runs=nb_runs,
            duration_s=duration_s,
            platform=platform,
        )
        for p in panels
    ]

    # Run all campaigns
    suite = CampaignSuite(campaigns=campaigns)
    suite.print_durations()
    suite.run_suite()

    # Generate the paper-styled 5-panel figure (Figure 4)
    set_paper_style(use_latex=paper_fonts)
    df = combine_panel_dfs(zip(panels, campaigns))
    df["Scheduler"] = df["scheduler"].map(PRETTY_SCHEDULERS)
    results_dir = Path.home() / ".benchkit" / "results"
    lineplot_by_bench(
        df,
        hue="Scheduler",
        legend_ncol=len(SCHEDULERS),
        out_path=results_dir / "figure4_schedulers.pdf",
    )

    print("\nResults saved to: ~/.benchkit/results/")


def main() -> None:
    parser = argparse.ArgumentParser(
        description="Figure 4: scheduler throughput sweep across KyotoCabinet, LevelDB, RocksDB.",
    )
    parser.add_argument(
        "--nb-runs",
        type=int,
        default=DEFAULT_NB_RUNS,
        help=f"Repetitions per configuration (default: {DEFAULT_NB_RUNS}, paper value).",
    )
    parser.add_argument(
        "--duration-s",
        type=int,
        default=DEFAULT_DURATION_S,
        help=f"Duration in seconds per run (default: {DEFAULT_DURATION_S}, paper value).",
    )
    parser.add_argument(
        "--threads",
        type=_int_list,
        default=None,
        help="Comma-separated thread counts (default: 1,2,4,8,16,24,32,64,72,80,88,96).",
    )
    parser.add_argument(
        "--paper-fonts",
        action="store_true",
        help="Use LaTeX fonts for exact paper typography (requires a LaTeX install).",
    )
    args = parser.parse_args()
    run(
        nb_runs=args.nb_runs,
        duration_s=args.duration_s,
        threads=args.threads,
        paper_fonts=args.paper_fonts,
    )


if __name__ == "__main__":
    main()
