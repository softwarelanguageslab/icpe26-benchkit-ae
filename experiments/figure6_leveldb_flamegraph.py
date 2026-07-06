#!/usr/bin/env python3
# Copyright (C) 2024 Vrije Universiteit Brussel. All rights reserved.
# SPDX-License-Identifier: MIT
"""
Figure 6 Experiment: Differential flame graphs for CAS vs MCS locks.

Paper reference:
    Section 4.4 (Visualizing Performance with Flame Graphs in benchkit), Figure 6.

What this script does:
    Runs LevelDB readrandom at 32 threads under two lock implementations
    (CAS and MCS) with a fixed CLOSE scheduling policy, records execution
    profiles via `perf record`, and generates:
      - Individual flame graphs for each lock (flamegraph.svg per run)
      - Differential flame graphs comparing CAS vs. MCS and vice versa

    In the differential flame graphs, red indicates functions where more time
    is spent in the source lock, blue where less. The paper shows that CAS
    spends more time in pthread_mutex_lock compared to MCS.

Hardware used in the paper:
    Platform B - NUMA server (2x Kunpeng 920-4826, 96 cores across 4 NUMA
    nodes, 539 GiB RAM, Ubuntu 20.04.6 LTS, kernel 5.4.0-200-generic, aarch64).

Expected execution time:
    ~1 minute (2 locks x 1 run x 10 s = 20 s + profiling/folding overhead).
    Measured on paper hardware: real 0m56s.

Prerequisites:
    - System packages: build-essential, cmake, libsnappy-dev, linux-tools-*, perl
    - Perf access: sudo sysctl -w kernel.perf_event_paranoid=-1
    - Python environment set up (see README)
    - FlameGraph tools are fetched automatically on first run

How to run:
    cd experiments/
    python figure6_leveldb_flamegraph.py

Output:
    - Per-run flame graphs (flamegraph.svg) in per-run directories
    - Differential flame graphs (diff_cas_vs_mcs.svg, diff_mcs_vs_cas.svg)
    - All stored under ~/.benchkit/results/
"""

import argparse

from benchkit import CampaignCartesianProduct
from benchkit.benches.leveldb import LevelDBBench
from benchkit.commandwrappers.perf import PerfRecordWrap, enable_non_sudo_perf
from benchkit.utils.dir import get_tools_dir

from lib import (
    flame_post_hook,
    generate_differential_flamegraph,
    get_platform,
    get_scheduler,
    get_tilt_lib,
)
from lib.plots import (
    barplot_by_category,
    flamegraph_svg_to_pdf,
    load_campaign_df,
    set_paper_style,
)

# Experiment configuration (fixed comparison: CAS vs MCS under CLOSE)
SCHEDULER = "CLOSE"
LOCKS = ["caslock", "mcslock"]
BENCH_NAME = "readrandom"

# ---- User-tunable defaults (paper values) ----
DEFAULT_NB_THREADS = 32
DEFAULT_DURATION_S = 10


def run(
    *,
    nb_threads: int = DEFAULT_NB_THREADS,
    duration_s: int = DEFAULT_DURATION_S,
    paper_fonts: bool = False,
) -> None:
    platform = get_platform()
    enable_non_sudo_perf(comm_layer=platform.comm)

    tiltlib = get_tilt_lib(platform=platform, locks=LOCKS)
    schedkit = get_scheduler(platform=platform)

    # Configure perf record
    flamegraph_dir = get_tools_dir(None) / "FlameGraph"
    perf_record = PerfRecordWrap(
        freq=99,
        report_interactive=False,
        report_file=True,
        flamegraph_path=flamegraph_dir,
    )

    # Fetch FlameGraph tools if not present
    perf_record.fetch_flamegraph()

    campaign = CampaignCartesianProduct(
        name="figure6_leveldb_flamegraph",
        benchmark=LevelDBBench(),
        shared_libs=[tiltlib],
        variables={
            "nb_threads": [nb_threads],
            "bench_name": [BENCH_NAME],
            "scheduler": [SCHEDULER],
            "lock": LOCKS,
        },
        nb_runs=1,
        duration_s=duration_s,
        command_wrappers=[perf_record],
        pre_run_hooks=[schedkit.start_sched_hook],
        post_run_hooks=[
            schedkit.end_sched_hook,
            perf_record.post_run_hook_report,
            flame_post_hook(perf_record=perf_record),
        ],
        platform=platform,
    )

    campaign.run()

    # Paper-styled sanity bar chart of throughput by lock
    set_paper_style(use_latex=paper_fonts)
    df = load_campaign_df(campaign)
    barplot_by_category(
        df,
        x="lock",
        y="throughput",
        ylabel="Throughput",
        out_path=campaign.base_data_dir() / "figure6_throughput.pdf",
    )

    # Generate differential flame graphs
    results_path = campaign.base_data_dir()
    folded_paths = sorted(results_path.rglob("perf.folded"))

    if len(folded_paths) != 2:
        print(f"[WARN] Expected 2 folded files, got {len(folded_paths)}:")
        for p in folded_paths:
            print(f"  - {p}")
        return

    src_folded, dst_folded = folded_paths[0], folded_paths[1]
    subtitle = f" ({duration_s} sec., {nb_threads} threads, {SCHEDULER} scheduler)"

    # Differential: CAS vs MCS (red = more time in CAS)
    generate_differential_flamegraph(
        perf_record=perf_record,
        src_folded_path=src_folded,
        dst_folded_path=dst_folded,
        out_svg_path=results_path / "diff_cas_vs_mcs.svg",
        flamegraph_subtitle="CAS lock against MCS lock" + subtitle,
    )

    # Differential: MCS vs CAS (red = more time in MCS)
    generate_differential_flamegraph(
        perf_record=perf_record,
        src_folded_path=dst_folded,
        dst_folded_path=src_folded,
        out_svg_path=results_path / "diff_mcs_vs_cas.svg",
        flamegraph_subtitle="MCS lock against CAS lock" + subtitle,
    )

    # Convert the differential flame graphs to paper PDFs (Figure 6)
    for svg_name in ("diff_cas_vs_mcs.svg", "diff_mcs_vs_cas.svg"):
        svg_path = results_path / svg_name
        if svg_path.exists():
            flamegraph_svg_to_pdf(svg_path, svg_path.with_suffix(".pdf"))

    print(f"\nResults directory: {results_path}")
    print("\nGenerated flame graphs:")
    for svg in sorted(results_path.rglob("*.svg")):
        print(f"  {svg}")


def main() -> None:
    parser = argparse.ArgumentParser(
        description="Figure 6: differential flame graphs for CAS vs MCS locks.",
    )
    parser.add_argument(
        "--nb-threads",
        type=int,
        default=DEFAULT_NB_THREADS,
        help=f"Number of benchmark threads (default: {DEFAULT_NB_THREADS}).",
    )
    parser.add_argument(
        "--duration-s",
        type=int,
        default=DEFAULT_DURATION_S,
        help=f"Duration in seconds per profiled run (default: {DEFAULT_DURATION_S}).",
    )
    parser.add_argument(
        "--paper-fonts",
        action="store_true",
        help="Use LaTeX fonts for exact paper typography (requires a LaTeX install).",
    )
    args = parser.parse_args()
    run(nb_threads=args.nb_threads, duration_s=args.duration_s, paper_fonts=args.paper_fonts)


if __name__ == "__main__":
    main()
