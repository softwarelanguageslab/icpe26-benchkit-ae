#!/usr/bin/env python3
# Copyright (C) 2024 Vrije Universiteit Brussel. All rights reserved.
# SPDX-License-Identifier: MIT
"""
Figure 3 Experiment: Lock throughput across KyotoCabinet, LevelDB, RocksDB.

Paper reference:
    Section 4.1 (Studying Locking Impact), Figure 3.

What this script does:
    Runs a comprehensive lock sweep across three key-value store benchmarks
    (KyotoCabinet, LevelDB, RocksDB) with two workloads each for LevelDB and
    RocksDB (readrandom, seekrandom), producing a 5-panel figure.

    Eight lock implementations are compared: CAS, TTAS, Ticket, MCS, Hemlock,
    CNA, HMCS, and the default glibc pthread_mutex baseline. Thread counts
    sweep from 1 to 96 (filtered to available CPUs). Each configuration is
    repeated 3 times for 10 seconds.

    The tilt shared library is built automatically and injected via LD_PRELOAD.

Hardware used in the paper:
    Platform B - NUMA server (2x Kunpeng 920-4826, 96 cores across 4 NUMA
    nodes, 539 GiB RAM, Ubuntu 20.04.6 LTS, kernel 5.4.0-200-generic, aarch64).

    On machines with fewer cores, thread counts are automatically filtered.
    Qualitative trends (e.g., NUMA-aware locks outperforming flat locks at
    high thread counts) may differ on non-NUMA or small-core-count machines.

Expected execution time:
    Defaults reproduce the paper parameters (nb_runs=3, duration_s=10). A reduced
    run (--nb-runs 2 --duration-s 5) took ~96 minutes (real 95m39s) on the paper's
    96-core server; the default paper parameters take roughly 3x longer. Scales
    with core count and number of locks.

Prerequisites:
    - System packages: build-essential, cmake, libsnappy-dev, libgflags-dev,
      liblz4-dev, libzstd-dev, zlib1g-dev (for RocksDB)
    - Python environment set up (see README)

How to run:
    cd experiments/
    python figure3_locks.py

Output:
    - CSV results per panel and line-plots (PNG/PDF) in ~/.benchkit/results/
    - One line plot per panel: throughput vs. threads, one line per lock
"""

import argparse
from pathlib import Path

from benchkit import CampaignCartesianProduct
from benchkit.benches.kyotocabinet import KyotoCabinetBench
from benchkit.benches.leveldb import LevelDBBench
from benchkit.benches.rocksdb import RocksDBBench
from benchkit.campaign import CampaignSuite

from lib import LOCKS, PRETTY_LOCKS, Panel, get_platform, get_tilt_lib
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
    tiltlib = get_tilt_lib(platform=platform)

    # Filter thread counts to available CPUs
    max_cpus = platform.nb_cpus()
    threads = [t for t in threads if t <= max_cpus]

    # Define the panels (one per benchmark/workload)
    panels = [
        Panel(
            name="kyotocabinet",
            campaign_name="figure3_kyotocabinet",
            bench=KyotoCabinetBench(),
            parameter_space={
                "nb_threads": threads,
                "lock": LOCKS,
            },
        ),
        Panel(
            name="leveldb/readrandom",
            campaign_name="figure3_leveldb_readrandom",
            bench=LevelDBBench(),
            parameter_space={
                "nb_threads": threads,
                "bench_name": ["readrandom"],
                "lock": LOCKS,
            },
        ),
        Panel(
            name="leveldb/seekrandom",
            campaign_name="figure3_leveldb_seekrandom",
            bench=LevelDBBench(),
            parameter_space={
                "nb_threads": threads,
                "bench_name": ["seekrandom"],
                "lock": LOCKS,
            },
        ),
        Panel(
            name="rocksdb/readrandom",
            campaign_name="figure3_rocksdb_readrandom",
            bench=RocksDBBench(),
            parameter_space={
                "nb_threads": threads,
                "bench_name": ["readrandom"],
                "lock": LOCKS,
            },
        ),
        Panel(
            name="rocksdb/seekrandom",
            campaign_name="figure3_rocksdb_seekrandom",
            bench=RocksDBBench(),
            parameter_space={
                "nb_threads": threads,
                "bench_name": ["seekrandom"],
                "lock": LOCKS,
            },
        ),
    ]

    # Create campaigns for each panel
    campaigns = [
        CampaignCartesianProduct(
            name=p.campaign_name,
            benchmark=p.bench,
            shared_libs=[tiltlib],
            variables=p.parameter_space,
            pretty={"lock": PRETTY_LOCKS},
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

    # Generate the paper-styled 5-panel figure (Figure 3)
    set_paper_style(use_latex=paper_fonts)
    df = combine_panel_dfs(zip(panels, campaigns))
    df["Lock"] = df["lock"].map(PRETTY_LOCKS)
    results_dir = Path.home() / ".benchkit" / "results"
    lineplot_by_bench(
        df,
        hue="Lock",
        legend_ncol=len(LOCKS),
        out_path=results_dir / "figure3_locks.pdf",
    )

    print("\nResults saved to: ~/.benchkit/results/")


def main() -> None:
    parser = argparse.ArgumentParser(
        description="Figure 3: lock throughput sweep across KyotoCabinet, LevelDB, RocksDB.",
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
