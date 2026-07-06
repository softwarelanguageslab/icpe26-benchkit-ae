# Copyright (C) 2024 Vrije Universiteit Brussel. All rights reserved.
# SPDX-License-Identifier: MIT
"""
Lock code generation package for tilt interposition.

This package generates tilt-compatible C source files that bridge spinlock
implementations (from libvsync and custom headers) to the pthread_mutex API
intercepted by the tilt shared library via LD_PRELOAD.

Modules:
    tiltgen     Generates C wrappers for libvsync spinlocks (CAS, TTAS, Ticket,
                MCS, Hemlock) and for custom lock headers (CNA). It analyzes
                each lock's header to determine whether the lock requires
                per-thread context, supports tryacquire, needs initialization,
                or has a destroy function, then selects and fills the
                appropriate C template.

    hmcs        Generates the HMCS (Hierarchical MCS) lock header file with
                platform-specific hierarchy parameters (number of NUMA nodes,
                cache partitions, cores) and threshold values. The generated
                header is placed in ``generatedlocks/include/`` and compiled
                alongside the other locks.

Templates (in this directory):
    template.c                  Context-free lock wrapper (single-parameter acquire)
    template_context.c          Context-aware lock wrapper (two-parameter acquire)
    template_context_trylock.c  Trylock snippet for context-aware locks
    template_context_malloc.c   Context with malloc-based allocation
    template_context_pkey.c     Context with pkey-based allocation
    template_hmcs.h             HMCS lock header template (filled by hmcs.py)
"""
