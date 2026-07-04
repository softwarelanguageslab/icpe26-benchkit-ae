# Copyright (C) 2024 Vrije Universiteit Brussel. All rights reserved.
# SPDX-License-Identifier: MIT
"""
Flame graph generation utilities.

Paper reference:
    Section 4.4 (Visualizing Performance with Flame Graphs in benchkit),
    Listing 9 and Figure 6.

This module provides two helpers that wrap benchkit's PerfRecordWrap
functionality with artifact-specific defaults (title generation, sizing):

    flame_post_hook()
        Returns a post-run hook function that generates an individual flame
        graph (SVG) for each benchmark run. The hook extracts metadata from
        the campaign record (lock name, thread count, scheduler, duration)
        to produce descriptive titles and subtitles on the flame graph.

    generate_differential_flamegraph()
        Takes two folded stack-trace files (produced by ``perf script |
        stackcollapse-perf.pl``) and generates a differential flame graph
        highlighting which functions gained (red) or lost (blue) relative
        execution time between the two configurations.

The default styling constants (width, height, font size, minimum-width
threshold) are tuned for the paper's single-column figures.
"""

from pathlib import Path
from typing import Optional

from benchkit.benchmark import RecordResult, WriteRecordFileFunction
from benchkit.commandwrappers.perf import PerfRecordWrap
from benchkit.utils.types import PathType

# Default flame graph styling
FLAMEGRAPH_WIDTH = 510
FLAMEGRAPH_HEIGHT = 18
FLAMEGRAPH_FONTSIZE = 15
FLAMEGRAPH_MINWIDTH = 2.0


def flame_post_hook(
    perf_record: PerfRecordWrap,
    flamegraph_width: int = FLAMEGRAPH_WIDTH,
    flamegraph_height: int = FLAMEGRAPH_HEIGHT,
    flamegraph_fontsize: int = FLAMEGRAPH_FONTSIZE,
    flamegraph_minwidth: float = FLAMEGRAPH_MINWIDTH,
):
    """
    Create a post-run hook that generates a flame graph for each run.

    This hook extracts metadata from the campaign record (lock name, thread
    count, scheduler, etc.) to generate descriptive flame graph titles.

    Args:
        perf_record: The PerfRecordWrap instance used to record the run.
        flamegraph_width: Width of the flame graph in pixels.
        flamegraph_height: Height per stack frame in pixels.
        flamegraph_fontsize: Font size for labels.
        flamegraph_minwidth: Minimum width percentage to display a frame.

    Returns:
        A post-run hook function compatible with benchkit campaigns.
    """

    def hook(
        experiment_results_lines: list[RecordResult],
        record_data_dir: PathType,
        write_record_file_fun: WriteRecordFileFunction,
    ) -> Optional[RecordResult]:
        # Expect a single record line for this experiment point
        record = experiment_results_lines[0]

        # Extract metadata for flame graph title
        lock = record.get("lock", "")
        if lock:
            lock_name = lock.split("lock")[0].strip().upper()
        else:
            lock_name = "PTHREAD"

        bench_name = record.get("bench_name", "benchmark")
        nb_threads = record.get("nb_threads", "?")
        scheduler = record.get("scheduler", "default")
        duration_s = int(record.get("duration", 0))

        flamegraph_title = f"Flame Graph for {lock_name} lock"
        flame_subtitle = (
            f"LevelDB {bench_name}: "
            f"{duration_s} seconds, "
            f"{nb_threads} threads, "
            f"{scheduler} scheduler"
        )

        return perf_record.post_run_hook_flamegraph(
            experiment_results_lines=experiment_results_lines,
            record_data_dir=record_data_dir,
            write_record_file_fun=write_record_file_fun,
            flamegraph_title=flamegraph_title,
            flamegraph_subtitle=flame_subtitle,
            flamegraph_width=flamegraph_width,
            flamegraph_height=flamegraph_height,
            flamegraph_fontsize=flamegraph_fontsize,
            flamegraph_minwidth=flamegraph_minwidth,
        )

    return hook


def generate_differential_flamegraph(
    perf_record: PerfRecordWrap,
    src_folded_path: Path,
    dst_folded_path: Path,
    out_svg_path: Path,
    flamegraph_title: str = "Differential Flame Graph",
    flamegraph_subtitle: str = "",
    flamegraph_width: int = FLAMEGRAPH_WIDTH,
    flamegraph_height: int = FLAMEGRAPH_HEIGHT,
    flamegraph_fontsize: int = FLAMEGRAPH_FONTSIZE,
    flamegraph_minwidth: float = FLAMEGRAPH_MINWIDTH,
) -> None:
    """
    Generate a differential flame graph comparing two runs.

    A differential flame graph highlights the difference between two execution
    profiles. Red indicates functions that take more time in the destination
    profile, blue indicates functions that take less time.

    Args:
        perf_record: The PerfRecordWrap instance (provides flamegraph tools path).
        src_folded_path: Path to the source (baseline) folded stack file.
        dst_folded_path: Path to the destination (comparison) folded stack file.
        out_svg_path: Path where the differential SVG will be written.
        flamegraph_title: Title for the flame graph.
        flamegraph_subtitle: Subtitle with additional context.
        flamegraph_width: Width in pixels.
        flamegraph_height: Height per frame in pixels.
        flamegraph_fontsize: Font size for labels.
        flamegraph_minwidth: Minimum width percentage to display.
    """
    perf_record.differential_flamegraph(
        src_folded_path=src_folded_path,
        dst_folded_path=dst_folded_path,
        out_svg_path=out_svg_path,
        flamegraph_title=flamegraph_title,
        flamegraph_subtitle=flamegraph_subtitle,
        flamegraph_width=flamegraph_width,
        flamegraph_height=flamegraph_height,
        flamegraph_fontsize=flamegraph_fontsize,
        flamegraph_minwidth=flamegraph_minwidth,
    )
