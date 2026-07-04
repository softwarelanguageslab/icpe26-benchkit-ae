#!/usr/bin/env python3
# Copyright (C) 2024 Vrije Universiteit Brussel. All rights reserved.
# SPDX-License-Identifier: MIT
"""
Figure 7 Experiment: benchkit framework overhead measurement.

Paper reference:
    Section 5 (Overhead of benchkit), Figure 7.

What this script does:
    Measures benchkit's overhead by running LevelDB readrandom on both the
    native host and inside a Docker container, then comparing throughput
    with equivalent hand-written shell scripts (shell_host.sh, shell_docker.sh).

    The script:
    1. Builds a Docker image (benchkit_overhead) using pythainer
    2. Runs a benchkit campaign on the host (figure7_leveldb_host)
    3. Runs a benchkit campaign inside Docker (figure7_leveldb_docker)
    4. Generates a strip plot comparing host vs. Docker throughput

    After this script completes, run shell_host.sh and shell_docker.sh to
    produce the shell baseline data, then run plot_overhead.py to generate
    the final 3-panel comparison figure (Figure 7 in the paper).

    The paper shows that benchkit introduces no measurable overhead (<2.2%)
    compared to equivalent hand-written shell scripts.

Hardware used in the paper:
    Intel Core i7-13800H laptop, Ubuntu 22.04.5, Linux 6.8.0.
    Works on any Linux machine with Docker installed.

Expected execution time:
    ~15-20 minutes total:
      - Docker image build: ~2 minutes (first time only)
      - benchkit host campaign: ~5 minutes (3 threads x 10 runs x 10 s)
      - benchkit Docker campaign: ~5 minutes (same)

Prerequisites:
    - System packages: build-essential, cmake, libsnappy-dev
    - Docker installed and current user in docker group
    - Python environment set up (see README)

How to run (full Figure 7 reproduction):
    cd experiments/figure7_overhead/

    # Step 1: Run benchkit campaigns (host + Docker)
    python figure7_leveldb_overhead.py

    # Step 2: Run shell baselines
    ./shell_host.sh
    ./shell_docker.sh

    # Step 3: Generate the final comparison plot
    python plot_overhead.py

Output:
    - Campaign CSVs in ~/.benchkit/results/
    - Shell results in ~/.benchkit/results/figure7_shell_{host,docker}/
    - Final figure: ~/.benchkit/results/figure7_overhead.{pdf,png}
"""

import argparse
from pathlib import Path

import pandas as pd
from benchkit import CampaignCartesianProduct
from benchkit.benches.leveldb import LevelDBBench
from benchkit.campaign import CampaignSuite
from benchkit.communication.docker import DockerCommLayer
from benchkit.platforms import Platform
from benchkit.utils.dir import benchkit_home_dir, gitmainrootdir
from pythainer.examples.builders import get_user_builder
from pythainer.runners import ConcreteDockerRunner

from lib import get_platform
from lib.plots import load_campaign_df, set_paper_style, stripplot_by_category

# Note: Run this script before shell_host.sh/shell_docker.sh, as it builds the
# Docker image and clones the LevelDB repository that the shell scripts reuse.
# See the README for pythainer documentation.


# ---- User-tunable defaults (paper values) ----
DEFAULT_NB_RUNS = 10
DEFAULT_DURATION_S = 10
DEFAULT_THREADS = [2, 4, 8]


def _get_os_version() -> str:
    """Get the current OS version for Docker base image."""
    osinfo = {}
    with open("/etc/os-release") as f:
        for line in f:
            if "=" in line:
                k, v = line.strip().split("=", 1)
                osinfo[k] = v.strip('"')
    return f"{osinfo['ID']}:{osinfo['VERSION_ID']}"


def _get_docker_platform() -> Platform:
    """Create a Docker platform for container experiments."""
    image_name = "benchkit_overhead"
    work_dir = "/home/user/workspace"
    docker_path = Path(work_dir)
    repo_dir = gitmainrootdir().resolve()

    # Build Docker image
    builder = get_user_builder(
        image_name=image_name,
        base_ubuntu_image=_get_os_version(),
    )
    builder.root()
    builder.add_packages(packages=["libsnappy-dev"])
    builder.user()
    builder.workdir(path=work_dir)
    builder.build()

    # Configure volume mounts
    host_benchkit_dir = benchkit_home_dir().expanduser() / "docker"
    dock_benchkit_dir = benchkit_home_dir().expanduser()
    host_benchkit_dir.mkdir(parents=True, exist_ok=True)

    runner = ConcreteDockerRunner(
        image=image_name,
        name="container",
        volumes={
            f"{repo_dir}": f"{docker_path}",
            f"{host_benchkit_dir}": f"{dock_benchkit_dir}",
        },
    )

    comm = DockerCommLayer(docker_runner=runner)
    platform = Platform(comm_layer=comm)
    return platform


def _get_campaign(
    name: str,
    run_type: str,
    platform: Platform,
    nb_runs: int,
    threads: list[int],
    duration_s: int,
):
    """Create a LevelDB campaign for the given platform."""
    return CampaignCartesianProduct(
        name=name,
        benchmark=LevelDBBench(),
        nb_runs=nb_runs,
        variables={
            "bench_name": ["readrandom"],
            "nb_threads": threads,
        },
        constants={
            "run_type": run_type,
        },
        duration_s=duration_s,
        platform=platform,
    )


def _int_list(text: str) -> list[int]:
    """Parse a comma-separated list of ints, e.g. '2,4,8'."""
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

    host_platform = get_platform()
    docker_platform = _get_docker_platform()

    campaigns = [
        _get_campaign(
            name="figure7_leveldb_docker",
            run_type="benchkit_docker",
            platform=docker_platform,
            nb_runs=nb_runs,
            threads=threads,
            duration_s=duration_s,
        ),
        _get_campaign(
            name="figure7_leveldb_host",
            run_type="benchkit_host",
            platform=host_platform,
            nb_runs=nb_runs,
            threads=threads,
            duration_s=duration_s,
        ),
    ]
    suite = CampaignSuite(campaigns=campaigns)

    suite.print_durations()
    suite.run_suite()

    # Paper-styled host-vs-Docker strip plot (Figure 7, benchkit panels; the full
    # figure with the shell baselines is assembled by plot_overhead.py)
    set_paper_style(use_latex=paper_fonts)
    df = pd.concat([load_campaign_df(c) for c in campaigns], ignore_index=True)
    results_dir = Path.home() / ".benchkit" / "results"
    stripplot_by_category(
        df,
        x="run_type",
        y="throughput",
        facet_col="nb_threads",
        ylabel="Throughput (ops/sec)",
        out_path=results_dir / "figure7_overhead.pdf",
    )

    print("\nResults saved to: ~/.benchkit/results/")
    print("\nTo compare with shell scripts, run:")
    print("  ./shell_host.sh")
    print("  ./shell_docker.sh")


def main() -> None:
    parser = argparse.ArgumentParser(
        description="Figure 7: benchkit framework overhead (host vs Docker).",
    )
    parser.add_argument(
        "--nb-runs",
        type=int,
        default=DEFAULT_NB_RUNS,
        help=f"Repetitions per thread count (default: {DEFAULT_NB_RUNS}, paper value).",
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
        help="Comma-separated thread counts (default: 2,4,8).",
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
