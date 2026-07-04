# Copyright (C) 2024 Vrije Universiteit Brussel. All rights reserved.
# SPDX-License-Identifier: MIT
"""
Shared utilities for ICPE'26 benchkit artifact experiments.

This package (`lib/`) provides the reusable helper layer that all example and
experiment scripts import. It encapsulates the artifact-specific configuration
that sits between the generic benchkit framework and the individual figure
scripts, keeping the scripts concise and DRY.

Modules:
    platforms   Platform detection: recognizes known servers (e.g., "algol" ->
                Kunpeng 96-core NUMA) and falls back to auto-detection.
    locks       Lock library configuration: generates tilt shared
                libraries for LD_PRELOAD-based pthread_mutex interposition.
                Supports CAS, TTAS, Ticket, MCS, Hemlock (flat) and CNA, HMCS
                (NUMA-aware hierarchical).
    schedulers  Scheduler integration: provides SchedProcess, a manager for the
                schedkit daemon, with pre/post-run hooks that start
                and stop scheduling policies (Normal, FAR, CLOSE, AsymSched,
                SAM, SAS) around each benchmark run.
    panels      Panel dataclass: organizes multi-benchmark, multi-panel figures
                (used by figure3_locks.py and figure4_schedulers.py).
    flame       Flame graph utilities: post-run hooks for generating individual
                and differential flame graphs from perf record data.
    lockgen/    Lock code generation: generates tilt-compatible C wrappers from
                libvsync spinlock headers and HMCS lock templates.

Exported symbols (for ``from lib import ...``):
    get_platform, get_tilt_lib, get_locks, LOCKS, PRETTY_LOCKS,
    get_scheduler, SCHEDULERS, PRETTY_SCHEDULERS,
    Panel, flame_post_hook, generate_differential_flamegraph.
"""

from .flame import flame_post_hook, generate_differential_flamegraph
from .locks import LOCKS, PRETTY_LOCKS, get_locks, get_tilt_lib
from .panels import Panel
from .platforms import get_platform
from .schedulers import PRETTY_SCHEDULERS, SCHEDULERS, get_scheduler

__all__ = [
    "flame_post_hook",
    "generate_differential_flamegraph",
    "get_locks",
    "get_tilt_lib",
    "LOCKS",
    "PRETTY_LOCKS",
    "get_platform",
    "get_scheduler",
    "Panel",
    "SCHEDULERS",
    "PRETTY_SCHEDULERS",
]
