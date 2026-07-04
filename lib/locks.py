# Copyright (C) 2024 Vrije Universiteit Brussel. All rights reserved.
# SPDX-License-Identifier: MIT
"""
Lock library configuration and tilt shared-library generation.

Paper reference:
    Section 4.1 (Studying Locking Impact).

This module manages the full pipeline for lock interposition experiments:

1. **Lock selection** - defines the set of available lock algorithms and their
   human-readable names for plot legends (LOCKS, PRETTY_LOCKS).

2. **Code generation** - for each selected lock, generates a tilt-compatible C
   wrapper that bridges the lock's native API to the pthread_mutex interface
   intercepted by tilt via LD_PRELOAD. NUMA-aware HMCS locks are additionally
   generated with platform-specific hierarchy parameters (number of NUMA nodes,
   cache partitions, etc.).

3. **Library build** - compiles the wrappers into tilt shared libraries
   (one ``.so`` per lock) that can be injected into any benchmark.

Supported lock algorithms:
    Flat locks (from libvsync, ``deps/libvsync/``):
        CAS, TTAS, Ticket, MCS, Hemlock

    NUMA-aware hierarchical locks:
        CNA  - Compact NUMA-Aware lock (``locks/include/numa_cnalock.h``)
        HMCS - Hierarchical MCS (generated into ``generatedlocks/``)

    Baseline:
        glibc pthread_mutex (when lock="default"; no LD_PRELOAD)

Key functions:
    get_locks()         Returns the list of all available lock names.
    get_tilt_lib()      Builds and returns a TiltLib instance ready for use
                        as a ``shared_libs`` entry in benchkit campaigns.
"""

import pathlib
from typing import List, Tuple

from benchkit.platforms import Platform
from benchkit.sharedlibs.tiltlib import TiltLib
from benchkit.utils.dir import gitmainrootdir

from lib.lockgen.hmcs import generate_hmcs_lock
from lib.lockgen.tiltgen import generate_all_vsync_locks, generate_locks_from_dir

_repo_dir = gitmainrootdir().resolve()

# Directories
_vsync_dir = (_repo_dir / "deps/libvsync").resolve()
_otherlocks_dir = (_repo_dir / "locks/include").resolve()
_tilt_genlocks_dir = _repo_dir / "generatedlocks/"
_includelock_dir = _tilt_genlocks_dir / "include"

# Lock configurations
_VSYNC_LOCKS = [
    "caslock",
    "ticketlock",
    "mcslock",
    "hemlock",
    "ttaslock",
]

_OTHER_LOCKS = {
    _otherlocks_dir: [
        "numa_cnalock",
    ],
    _includelock_dir: [
        "dnuma_hmcslock",
    ],
}

# All locks available for experiments
LOCKS = _VSYNC_LOCKS + sum(_OTHER_LOCKS.values(), start=[]) + ["default"]

# Pretty names for plotting
PRETTY_LOCKS = {
    "default": "Baseline (glibc pthread_mutex)",
    "": "Baseline (glibc pthread_mutex)",
    "caslock": "CAS lock",
    "ticketlock": "Ticket lock",
    "ttaslock": "TTAS lock",
    "mcslock": "MCS lock",
    "hemlock": "Hemlock",
    "numa_cnalock": "CNA lock",
    "dnuma_hmcslock": "HMCS lock",
}


def get_locks() -> List[str]:
    """
    Get the list of all available lock implementations.

    Returns:
        List of lock names that can be used in experiments.
    """
    return LOCKS.copy()


def _get_full_nomenc_size(platform: Platform) -> Tuple[Tuple[str, int], ...]:
    """Get full nomenclature with sizes for HMCS generation."""
    return (
        ("core", platform.nb_hyperthreaded_cores()),
        ("cache", platform.nb_cache_partitions()),
        ("numa", platform.nb_numa_nodes()),
        ("package", platform.nb_packages()),
        ("system", 1),
    )


def _generate_numa_locks(
    platform: Platform,
    gen_include_dir: pathlib.Path,
) -> None:
    """Generate NUMA-aware HMCS locks for the given platform."""
    match platform.architecture:
        case "x86_64":
            nomenclature = "core-numa-system"
            sizes = (
                platform.nb_hyperthreaded_cores(),
                platform.nb_numa_nodes(),
                1,
            )
            thresholds = (128, 128)
        case "aarch64":
            nomenclature = "cache-numa-system"
            sizes = (
                platform.nb_cache_partitions(),
                platform.nb_numa_nodes(),
                1,
            )
            thresholds = (128, 128)
        case _:
            raise ValueError(f"Unsupported architecture: {platform.architecture}")

    generate_hmcs_lock(
        vsync_dir=_vsync_dir,
        hmcs_spec="numa_hmcslock",
        target_directory=gen_include_dir,
        nomenclature=nomenclature,
        sizes=sizes,
        h_thresholds=thresholds,
        total_nb_cpus=platform.nb_cpus(),
        total_nb_cores=platform.nb_hyperthreaded_cores(),
        full_nomenc_size=_get_full_nomenc_size(platform=platform),
    )


def get_tilt_lib(
    platform: Platform,
    locks: List[str] | None = None,
    debug: bool = False,
) -> TiltLib:
    """
    Build and return the tilt shared library for lock interposition.

    This generates platform-specific lock implementations (including NUMA-aware
    HMCS locks) and compiles them into a shared library that can be injected
    via LD_PRELOAD.

    Args:
        platform: Target platform for lock generation.
        locks: List of locks to include. Defaults to all available locks.
        debug: Whether to build in debug mode.

    Returns:
        TiltLib instance ready for use as a shared_lib in campaigns.
    """
    if locks is None:
        vsync_locks = _VSYNC_LOCKS
        dir2locks = _OTHER_LOCKS
    else:
        vsync_locks = [lock for lock in locks if lock in _VSYNC_LOCKS]
        dir2locks = {d: [lock for lock in ls if lock in locks] for d, ls in _OTHER_LOCKS.items()}
        dir2locks = {d: ls for d, ls in dir2locks.items() if ls}

    tilt_src_dir = _tilt_genlocks_dir
    gen_src_dir = tilt_src_dir / "src/"
    gen_include_dir = tilt_src_dir / "include"

    # Generate NUMA-aware locks for this platform
    _generate_numa_locks(
        platform=platform,
        gen_include_dir=gen_include_dir,
    )

    # Generate vsync lock wrappers
    generate_all_vsync_locks(
        vsync_dir=_vsync_dir,
        output_dir=gen_src_dir,
        given_locks=vsync_locks,
    )

    # Generate other lock wrappers
    for header_dir, non_vsync_locks in dir2locks.items():
        generate_locks_from_dir(
            header_dir=header_dir,
            output_dir=gen_src_dir,
            given_locks=non_vsync_locks,
        )

    # Build the library
    tilt_lib = TiltLib(
        tilt_locks_dir=tilt_src_dir,
        debug_mode=debug,
    )
    tilt_lib.build()

    return tilt_lib
