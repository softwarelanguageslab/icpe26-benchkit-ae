#!/usr/bin/env python3
# Copyright (C) 2024 Vrije Universiteit Brussel. All rights reserved.
# SPDX-License-Identifier: MIT
"""
Plot Figure 7: benchkit overhead comparison.

Paper reference:
    Section 5 (Overhead of benchkit), Figure 7.

What this script does:
    Collects results from four sources and produces the final comparison figure:
      1. benchkit host campaign (CSV in ~/.benchkit/results/...figure7...host...)
      2. benchkit Docker campaign (CSV in ~/.benchkit/results/...figure7...docker...)
      3. Shell host runs (text files in ~/.benchkit/results/figure7_shell_host/)
      4. Shell Docker runs (text files in ~/.benchkit/results/figure7_shell_docker/)

    Produces a 3-panel strip plot (one per thread count: 2, 4, 8) comparing
    benchkit vs. shell throughput, faceted by execution environment.

    Also prints an overhead summary table showing the percentage difference
    between benchkit and shell for each thread count and environment.

Prerequisites:
    Run these three scripts first (in order):
      1. python figure7_leveldb_overhead.py   (benchkit campaigns)
      2. ./shell_host.sh                     (shell baseline on host)
      3. ./shell_docker.sh                   (shell baseline in Docker)

How to run:
    cd experiments/figure7_overhead/
    python plot_overhead.py

Output:
    - ~/.benchkit/results/figure7_overhead.pdf
    - ~/.benchkit/results/figure7_overhead.png
    - Overhead summary table printed to console
"""

from pathlib import Path

import matplotlib.pyplot as plt
import pandas as pd
import seaborn as sns

# from benchkit.benches.leveldb import LevelDBBench
from benchkit.charts.dataframes import get_dataframe

RESULTS_DIR = Path.home() / ".benchkit" / "results"


def _collect_benchkit_csvs() -> pd.DataFrame:
    """
    Find the last benchkit campaign CSV for host and docker, parse with get_dataframe,
    and return a unified DataFrame with columns: run_type, nb_threads, throughput.
    """
    csv_files = sorted(RESULTS_DIR.glob("benchmark_*figure7*.csv"))

    # Keep the last CSV per category (sorted by name includes timestamp)
    last_per_type: dict[str, Path] = {}
    for p in csv_files:
        if "docker" in p.name:
            last_per_type["benchkit_docker"] = p
        elif "host" in p.name:
            last_per_type["benchkit_host"] = p

    frames = []
    for run_type, csv_path in last_per_type.items():
        df = get_dataframe(csv_path)
        df["run_type"] = run_type
        frames.append(df[["run_type", "nb_threads", "throughput"]])

    return pd.concat(frames, ignore_index=True) if frames else pd.DataFrame()


def _parse_shell_file(path: Path) -> dict:
    """
    Parse a single shell output file using LevelDBBench.collect() logic.

    We build a minimal CollectContext-like shim so we can reuse the same
    parsing that benchkit uses internally.
    """
    output = path.read_text()

    # bench = LevelDBBench()
    # Reproduce the collect() parsing inline since we don't have a real
    # CollectContext. The parsing only needs the stdout string.

    if "benchstats:" not in output:
        raise ValueError(f"Missing benchstats line in {path}")

    benchstats = output.split("benchstats:")[-1].strip()
    values = benchstats.split(";")
    nb_threads = len(values) - 2

    duration_raw = float(values[0])
    global_count = int(float(values[1]))
    duration = duration_raw / nb_threads if nb_threads > 0 else duration_raw
    throughput = global_count / duration if duration > 0 else 0.0

    return {
        "nb_threads": nb_threads,
        "throughput": throughput,
    }


def _collect_shell_results(dirname: str, run_type: str) -> pd.DataFrame:
    """Parse all shell result files from a directory."""
    shell_dir = RESULTS_DIR / dirname
    if not shell_dir.exists():
        return pd.DataFrame()

    rows = []
    for txt_file in sorted(shell_dir.glob("run_t*_r*.txt")):
        try:
            rec = _parse_shell_file(txt_file)
            rec["run_type"] = run_type
            rows.append(rec)
        except Exception as e:
            print(f"WARNING: skipping {txt_file.name}: {e}")

    return pd.DataFrame(rows) if rows else pd.DataFrame()


def main():
    # --- Collect all data ---
    dfs = [
        _collect_benchkit_csvs(),
        _collect_shell_results("figure7_shell_host", "shell_host"),
        _collect_shell_results("figure7_shell_docker", "shell_docker"),
    ]
    df = pd.concat([d for d in dfs if not d.empty], ignore_index=True)

    if df.empty:
        print("No data found in", RESULTS_DIR)
        return

    print(df.to_string(index=False))
    print()

    # --- Pretty labels + ordering ---
    run_type_order = ["benchkit_host", "benchkit_docker", "shell_host", "shell_docker"]
    run_type_pretty = {
        "benchkit_host": "benchkit host",
        "benchkit_docker": "benchkit docker",
        "shell_host": "Shell host",
        "shell_docker": "Shell docker",
    }

    df["run_type_pretty"] = df["run_type"].map(run_type_pretty)
    present_types = [r for r in run_type_order if r in df["run_type"].values]
    thread_order = sorted(df["nb_threads"].unique())

    # --- Plot ---
    sns.set_theme(
        context="talk",
        style="whitegrid",
        palette="colorblind",
        font_scale=1.15,
        rc={
            "figure.figsize": (8, 6),
            "pdf.fonttype": 42,
        },
    )

    g = sns.catplot(
        data=df,
        x="run_type_pretty",
        y="throughput",
        hue="run_type_pretty",
        col="nb_threads",
        col_order=thread_order,
        order=[run_type_pretty[r] for r in present_types],
        kind="strip",
        dodge=True,
        height=4,
        aspect=0.9,
        sharey=False,
        legend=False,
    )

    g.set_titles("Threads = {col_name}")
    g.set_axis_labels("", "Throughput (ops/sec)")

    for ax in g.axes.flatten():
        ax.set_xticklabels(ax.get_xticklabels(), rotation=25, ha="right")

    plt.tight_layout()

    # --- Save ---
    out_pdf = RESULTS_DIR / "figure7_overhead.pdf"
    out_png = RESULTS_DIR / "figure7_overhead.png"
    g.savefig(str(out_pdf))
    g.savefig(str(out_png), dpi=150)
    print(f"Saved: {out_pdf}")
    print(f"Saved: {out_png}")

    # --- Overhead summary table ---
    summary = (
        df[df["run_type"].isin(present_types)]
        .groupby(["run_type", "nb_threads"])
        .agg(mean_throughput=("throughput", "mean"))
        .reset_index()
    )
    pivot = summary.pivot(index="nb_threads", columns="run_type", values="mean_throughput")

    if {"benchkit_host", "shell_host"}.issubset(pivot.columns):
        pivot["host_overhead_%"] = (
            100 * (pivot["benchkit_host"] - pivot["shell_host"]) / pivot["shell_host"]
        )
    if {"benchkit_docker", "shell_docker"}.issubset(pivot.columns):
        pivot["docker_overhead_%"] = (
            100 * (pivot["benchkit_docker"] - pivot["shell_docker"]) / pivot["shell_docker"]
        )

    print("\nOverhead summary:")
    print(pivot.to_string())

    plt.show()


if __name__ == "__main__":
    main()
