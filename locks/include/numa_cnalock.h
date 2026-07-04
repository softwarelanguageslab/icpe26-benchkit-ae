/*
 * NUMA-aware CNA (Compact NUMA-Aware) lock wrapper.
 *
 * Paper reference: Section 4.1 - one of the NUMA-aware hierarchical locks
 *                  evaluated in Figures 3 and 6.
 *                  See Dice & Kogan, "Compact NUMA-aware Locks", EuroSys 2019.
 *
 * This header wraps libvsync's cnalock implementation with NUMA-node awareness.
 * On acquire/release, it determines the calling thread's NUMA node using the
 * platform's CPU topology (imported from the generated HMCS header) and passes
 * it to the CNA lock so that hand-offs preferentially stay within the same
 * NUMA node, reducing cross-node coherence traffic.
 *
 * The NUMA-node calculation uses HMCS_NB_CORES, HMCS_NB_NUMAS, and
 * HMCS_CPU_P_CORE defines from the generated numa_hmcslock.h header, which
 * is produced by lib/lockgen/hmcs.py at experiment setup time.
 *
 * This file is compiled by locks/CMakeLists.txt into a shared library that
 * tilt can load via LD_PRELOAD.
 */

#ifndef BENCHKIT_NUMA_CNALOCK_H
#define BENCHKIT_NUMA_CNALOCK_H

#include <vsync/spinlock/cnalock.h>

#include <numa_hmcslock.h> /* for HMCS_NB_CORES, HMCS_NB_NUMAS, etc. */

typedef struct numa_cnalock_s {
    cnalock_t lock;
} numa_cnalock_t;

static inline void
numa_cnalock_init(numa_cnalock_t *l)
{
    cnalock_init(&l->lock);
}

static inline vsize_t _get_numa_node(vsize_t cpu_id)
{
    const vsize_t vcpu_id = (cpu_id % HMCS_NB_CORES) * HMCS_CPU_P_CORE + (cpu_id / HMCS_NB_CORES);
    const vsize_t numa_node = vcpu_id / (HMCS_NB_CORES / HMCS_NB_NUMAS);
    return numa_node;
}

static inline void
numa_cnalock_acquire(numa_cnalock_t *l, cna_node_t *n)
{
    const vsize_t cpu = cid_of_cur_thread();
    const vuint32_t numa_node = (vuint32_t) _get_numa_node(cpu);

    cnalock_acquire(&l->lock, n, numa_node);
}

static inline void
numa_cnalock_release(numa_cnalock_t *l, cna_node_t *n)
{
    const vsize_t cpu = cid_of_cur_thread();
    const vuint32_t numa_node = (vuint32_t) _get_numa_node(cpu);
    // TODO check if it must be the same node as acquire()
    //      or if migration is allowed.

    cnalock_release(&l->lock, n, numa_node);
}
#endif /* BENCHKIT_NUMA_CNALOCK_H */
