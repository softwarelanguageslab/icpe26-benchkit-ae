#!/usr/bin/env python3
# Copyright (C) 2024 Vrije Universiteit Brussel. All rights reserved.
# SPDX-License-Identifier: MIT
"""
Listing 6: Pre-run and post-run hooks for schedkit.

Paper reference:
    Section 4.2 (Studying Thread-Placement Impact), Listing 6.

What this script does:
    Demonstrates the hook mechanism used to integrate external scheduling
    daemons with benchkit campaigns. The pre-run hook starts the schedkit
    daemon before each benchmark run with the policy specified
    in the campaign parameters; the post-run hook terminates it afterward.

    This script is illustrative only - it prints the configured hooks but
    does not run a full campaign. See listing7_leveldb_schedulers.py for a
    complete example that uses these hooks in an actual campaign.

Hardware used in the paper:
    Platform B - NUMA server (2x Kunpeng 920-4826, 96 cores, aarch64).
    Works on any Linux machine (hooks are configured but not exercised here).

Expected execution time:
    Instant (< 1 second, no benchmark is executed).

Prerequisites:
    - Python environment set up (see README)

How to run:
    cd examples/
    python listing6_sched_hooks.py

Output:
    - Console output showing the configured hook functions
"""

from lib import get_platform, get_scheduler


def main() -> None:
    platform = get_platform()

    # Get a configured scheduler instance
    # This provides start_sched_hook and end_sched_hook methods
    schedkit = get_scheduler(platform=platform)

    # The hooks are used in campaigns like this:
    #
    # campaign = CampaignCartesianProduct(
    #     ...
    #     pre_run_hooks=[schedkit.start_sched_hook],
    #     post_run_hooks=[schedkit.end_sched_hook],
    #     parameter_space={
    #         "scheduler": ["Normal", "FAR", "CLOSE", "AsymSched", "SAM", "SAS"],
    #         ...
    #     },
    # )
    #
    # The start_sched_hook reads the "scheduler" variable from the campaign
    # parameters and starts the appropriate scheduling policy. The end_sched_hook
    # stops the scheduler after the benchmark run completes.

    print("Scheduler hooks configured successfully.")
    print(f"  start_sched_hook: {schedkit.start_sched_hook}")
    print(f"  end_sched_hook: {schedkit.end_sched_hook}")
    print("\nSee listing7_leveldb_schedulers.py for a complete example.")


if __name__ == "__main__":
    main()
