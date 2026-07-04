#!/usr/bin/env python3
# Copyright (C) 2024 Vrije Universiteit Brussel. All rights reserved.
# SPDX-License-Identifier: MIT
"""
Listing 9: benchkit campaign using perf record to generate flame graphs.

Paper reference:
    Section 4.4 (Visualizing Performance with Flame Graphs in benchkit), Listing 9.

What this script does:
    Demonstrates how to generate flame graphs and differential flame graphs
    using the PerfRecordWrap command wrapper. The wrapper prepends
    `perf record` to the benchmark invocation; a post-run hook converts
    the resulting perf.data into a folded stack trace and then into an SVG
    flame graph (using Brendan Gregg's FlameGraph tools, fetched automatically).

    Two lock implementations (CAS and MCS) are compared under the CLOSE
    scheduling policy at 32 threads. After the campaign, differential flame
    graphs are generated showing where CAS spends more time than MCS and
    vice versa.

Hardware used in the paper:
    Platform B - NUMA server (2x Kunpeng 920-4826, 96 cores, aarch64).
    Works on any Linux machine with perf access.

Expected execution time:
    ~2 minutes (2 locks x 1 run x 10 s = 20 s + profiling overhead).

Prerequisites:
    - System packages: build-essential, cmake, libsnappy-dev, linux-tools-*, perl
    - Perf access: sudo sysctl -w kernel.perf_event_paranoid=-1
    - Python environment set up (see README)
    - FlameGraph tools are fetched automatically on first run

How to run:
    cd examples/
    python listing9_leveldb_flamegraph.py

Output:
    - Per-run flame graphs (flamegraph.svg) in per-run directories
    - Differential flame graphs (diff_cas_vs_mcs.svg, diff_mcs_vs_cas.svg)
      at the campaign directory level
    - All stored under ~/.benchkit/results/
"""

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

# Experiment parameters
NB_THREADS = 32
DURATION_S = 10
SCHEDULER = "CLOSE"
LOCKS = ["caslock", "mcslock"]
BENCH_NAME = "readrandom"


def main() -> None:
    platform = get_platform()
    enable_non_sudo_perf(comm_layer=platform.comm)

    tiltlib = get_tilt_lib(platform=platform)
    schedkit = get_scheduler(platform=platform)

    # Configure perf record with FlameGraph tools
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
        name="listing9_leveldb_flamegraph",
        benchmark=LevelDBBench(),
        shared_libs=[tiltlib],
        variables={
            "nb_threads": [NB_THREADS],
            "bench_name": [BENCH_NAME],
            "scheduler": [SCHEDULER],
            "lock": LOCKS,
        },
        nb_runs=1,
        duration_s=DURATION_S,
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

    # Generate a quick sanity plot
    campaign.generate_graph(
        plot_name="barplot",
        x="lock",
        y="throughput",
        hue="lock",
        title="LevelDB readrandom - throughput by lock",
    )

    # Generate differential flame graphs
    results_path = campaign.base_data_dir()
    folded_paths = sorted(results_path.rglob("perf.folded"))

    if len(folded_paths) != 2:
        print(f"[WARN] Expected 2 folded files, got {len(folded_paths)}")
        return

    src_folded, dst_folded = folded_paths[0], folded_paths[1]
    subtitle = f" ({DURATION_S} sec., {NB_THREADS} threads, {SCHEDULER} scheduler)"

    # CAS vs MCS
    # TODO align with paper by "selecting" record with values?
    generate_differential_flamegraph(
        perf_record=perf_record,
        src_folded_path=src_folded,
        dst_folded_path=dst_folded,
        out_svg_path=results_path / "diff_cas_vs_mcs.svg",
        flamegraph_subtitle="CAS lock against MCS lock" + subtitle,
    )

    # MCS vs CAS
    generate_differential_flamegraph(
        perf_record=perf_record,
        src_folded_path=dst_folded,
        dst_folded_path=src_folded,
        out_svg_path=results_path / "diff_mcs_vs_cas.svg",
        flamegraph_subtitle="MCS lock against CAS lock" + subtitle,
    )

    print(f"\nResults directory: {results_path}")
    for svg in sorted(results_path.rglob("*.svg")):
        print(f"  {svg}")


if __name__ == "__main__":
    main()
