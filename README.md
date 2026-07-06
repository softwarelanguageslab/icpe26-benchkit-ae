# Artifact: **benchkit**

This artifact accompanies the ICPE 2026 paper:

> **benchkit: A Declarative Framework for Composable Performance Evaluation of System Software**

It provides all scripts, configurations, and instructions required to
**reproduce the experimental results** presented in the paper and to
**inspect the underlying data and artifacts** produced during execution.

> **Looking for benchkit itself?** This repository is the *artifact* accompanying the
> paper; the scripts and data needed to reproduce its results. For documentation on the
> **benchkit framework** (installation, API, and general usage beyond this paper), refer to
> the framework repository (<https://github.com/open-s4c/benchkit>) or the paper itself
> (DOI [10.1145/3777884.3796997](https://doi.org/10.1145/3777884.3796997)).

---

## What this artifact demonstrates

**benchkit** is a Python framework for **systematic, composable
performance experimentation**.  Rather than focusing on a single benchmark or
workload, the artifact demonstrates how experiments can be *assembled declaratively*
from reusable components:

* benchmarks (LevelDB, RocksDB, KyotoCabinet, SPEC CPU 2017, microbenchmarks)
* locking mechanisms (tilt, wrapping spinlock implementations like CAS, MCS, CNA, HMCS, etc.)
* scheduling policies (schedkit, implementing CLOSE, FAR, SAS, SAM, etc.)
* profiling tools (`perf stat`, `perf record`, flame graphs)
* execution environments (host, Docker)

The artifact contains **three main case studies** from the paper:

1. **Hybrid-core variability analysis** (Section 3)
   Understanding performance variability on asymmetric processors (P/E cores) and
   the impact of affinity and placement control.

2. **Locks and schedulers study** (Section 4)
   Composing locking mechanisms, scheduling policies, and profiling tools on a
   large NUMA system to study scalability and interaction effects.

3. **Framework overhead analysis** (Section 5)
   Quantifying the runtime overhead introduced by the benchkit framework,
   comparing native shell-based execution with framework-managed execution,
   both on the host and inside containers.

---

## Repository structure

```
artifact/
├── README.md                 # This file
├── pyproject.toml            # Artifact Python package
├── requirements.txt          # Python dependencies
│
├── examples/                 # Runnable code examples (paper listings)
│   ├── listing1_leveldb.py            # Listing 1: Basic LevelDB campaign
│   ├── listing2_spec.py               # Listing 2: SPEC baseline variability
│   ├── listing3_heater.py             # Listing 3: Sequential heater sweep
│   ├── listing4_spec_placement.py     # Listing 4: TasksetWrap (SPEC CPU)
│   ├── listing4_leveldb_placement.py  # Listing 4: TasksetWrap (LevelDB variant)
│   ├── listing5_leveldb_locks.py      # Listing 5: Lock campaign with tilt
│   ├── listing6_sched_hooks.py        # Listing 6: Scheduler hook demo
│   ├── listing7_leveldb_schedulers.py # Listing 7: Scheduler campaign with schedkit
│   ├── listing8_leveldb_perfstat.py   # Listing 8: perf-stat integration
│   └── listing9_leveldb_flamegraph.py # Listing 9: Flame graph generation
│
├── experiments/              # Full experiments producing paper figures
│   ├── figure2_heater.py              # Figure 2 (right): Per-CPU heater
│   ├── figure2_placement_spec.py      # Figure 2 (left):  Placement (SPEC)
│   ├── figure2_placement_leveldb.py   # Figure 2 (left):  Placement (LevelDB, alternative)
│   ├── figure3_locks.py               # Figure 3: Lock sweep (5 panels)
│   ├── figure4_schedulers.py          # Figure 4: Scheduler sweep (5 panels)
│   ├── figure5_leveldb_perfstat.py    # Figure 5: perf-stat + schedulers (5 panels)
│   ├── figure6_leveldb_flamegraph.py  # Figure 6: Differential flame graphs
│   └── figure7_overhead/              # Figure 7: Framework overhead
│       ├── figure7_leveldb_overhead.py #  benchkit campaigns (host + Docker)
│       ├── shell_host.sh             #   shell baseline (host)
│       ├── shell_docker.sh           #   shell baseline (Docker)
│       └── plot_overhead.py          #   final comparison figure
│
├── lib/                      # Shared helpers (installed via pip -e .)
│   ├── __init__.py
│   ├── locks.py              # Lock configuration and tilt integration
│   ├── schedulers.py         # Scheduler hooks (schedkit integration)
│   ├── panels.py             # Panel dataclass for multi-panel figures
│   ├── platforms.py          # Platform detection
│   ├── flame.py              # Flame graph utilities
│   └── lockgen/              # Lock code generation for tilt
│
├── locks/                    # Custom lock implementations (CNA)
├── generatedlocks/           # Generated locks (HMCS)
│
└── deps/                     # External dependencies (git submodules)
    ├── benchkit/             # Core framework
    ├── schedkit/             # User-space scheduler
    ├── tilt/                 # Lock interposition library
    ├── libvsync/             # Spinlock implementations
    └── pythainer/            # Docker image builders
```

**Rule of thumb for reviewers**:

* `examples/` are *short, fast, illustrative* — they correspond to the code listings in the paper.
* `experiments/` are *full paper results* — they produce the figures reported in the paper.

---

## Hardware assumptions

This artifact assumes a **Linux-based system**. All experiments were developed
and validated on recent Linux distributions, including **Ubuntu** (20.04 LTS,
22.04 LTS, 24.04 LTS) and **Manjaro** (26.0.1).

No distribution-specific kernel patches or vendor tools are required beyond
standard Linux facilities (e.g., `perf`, `taskset`, `cpupower`), and the artifact
is expected to run on other modern Linux distributions with equivalent tooling.

The following capabilities are required:
- availability of hardware performance counters (`perf`)
- support for CPU affinity control (`taskset`, `sched_setaffinity`)
- support for NUMA placement (for Section 4 experiments)

Other Unix-like systems (e.g., macOS) may execute some scripts but will **not**
produce correct or meaningful results for experiments involving CPU affinity,
NUMA placement, or Linux scheduling behavior.

The experiments were run on two representative platforms:

### Platform A: Hybrid-Core Laptop (Section 3 — Figure 2)
- **CPU**: AMD Ryzen AI 9 HX 370 (4 P-cores + 8 E-cores, 12 cores / 24 threads)
- **RAM**: 32 GiB
- **OS**: Manjaro 26.0.1 with Linux 6.18+
- **Use case**: Hybrid-core variability study

### Platform B: Large NUMA Server (Section 4 — Figures 3, 4, 5, 6)
- **CPU**: 2x Kunpeng 920-4826 (96 cores across 4 NUMA nodes)
- **RAM**: 539 GiB
- **Architecture**: aarch64
- **OS**: Ubuntu 20.04.6 LTS, kernel 5.4.0-200-generic
- **Use case**: Lock/scheduler studies on many-core ARM

The **overhead study** (Section 5, Figure 7) was conducted on a third platform
(Intel Core i7-13800H, Ubuntu 22.04.5) but can be **replicated on any Linux
machine with Docker installed**. The specific hardware is not important for this
experiment, as it measures the relative overhead of the framework compared to
hand-written shell scripts on the same machine.

Results may differ on other hardware. The experiments are designed to demonstrate
benchkit's capabilities; absolute performance numbers are platform-specific.

> The artifact **does not require identical hardware** to run.
> Absolute performance numbers will differ, but **qualitative trends**
> and **experiment structure** remain reproducible. In particular, the
> experiments' main conclusions (e.g., that NUMA-aware locks outperform flat
> locks under contention, or that thread placement significantly affects
> variability on hybrid-core CPUs) should hold on any machine with
> similar architectural characteristics (multi-socket NUMA or
> heterogeneous cores, respectively).

---

## Installation (quick start)

### Software Dependencies

#### System Packages

```bash
# Ubuntu/Debian
sudo apt update
sudo apt install -y \
    build-essential \
    cmake \
    git \
    python3 \
    python3-pip \
    python3-venv \
    linux-tools-generic \
    linux-tools-common \
    linux-tools-$(uname -r) \
    numactl \
    fuseiso \
    libbz2-dev \
    libgflags-dev \
    liblz4-dev \
    libsnappy-dev \
    libzstd-dev \
    zlib1g-dev \
    fzf \
    curl \
    perl
```

> **Note:** On a fresh Ubuntu installation, a **reboot** may be required after
> installing `linux-tools-*` for `perf` to be recognized in your `PATH`.
> We recommend rebooting after installing all packages above before proceeding.

Some experiments rely on Linux `perf` for profiling. By default, modern Linux
kernels restrict access to performance counters to privileged users. To allow
running `perf` **without sudo** (as expected by the artifact scripts), you must
lower the `perf_event_paranoid` level:

```bash
sudo sysctl -w kernel.perf_event_paranoid=-1
```

> **Note**: This setting is **temporary** and must be reapplied after each
> reboot. It affects only the current session and is sufficient for running
> the artifact without elevated privileges.

#### External Tools

| Tool | Purpose | Installation |
|------|---------|--------------|
| [perf](https://perf.wiki.kernel.org/) | Performance profiling | Included in `linux-tools-*` |
| [Docker](https://www.docker.com/) | Container experiments (Figure 7 only) | See below |


#### Docker Installation (required only for Figure 7)

We recommend installing Docker using the official convenience script rather than Ubuntu packages:

```bash
curl -fsSL https://get.docker.com -o get-docker.sh
sudo sh get-docker.sh
sudo usermod -aG docker $USER
# Log out and back in for group membership to take effect
```

#### Framework Components Overview

| Component | Repository | Purpose |
|-----------|------------|---------|
| **benchkit** | [open-s4c/benchkit](https://github.com/open-s4c/benchkit) | Core framework |
| **tilt** | [open-s4c/tilt](https://github.com/open-s4c/tilt) | Lock interposition |
| **schedkit** | [open-s4c/schedkit](https://github.com/open-s4c/schedkit) | User-space scheduler |
| **libvsync** | [open-s4c/libvsync](https://github.com/open-s4c/libvsync) | Spinlock implementations (CAS, Ticket, MCS, TTAS, Hemlock) |
| **pythainer** | [apaolillo/pythainer](https://github.com/apaolillo/pythainer) | Composable Docker builders |

#### libvsync

[libvsync](https://github.com/open-s4c/libvsync) is a C library of verified
synchronization primitives, including spinlock algorithms such as
CAS, Ticket, MCS, TTAS, and Hemlock.
In this artifact, libvsync provides the lock implementations that are injected
into benchmarks via tilt (LD_PRELOAD) for the locking experiments (Figures 3, 6).
libvsync is included in the artifact as a git submodule and will be installed
with the instructions below.

#### Pythainer

[Pythainer](https://github.com/apaolillo/pythainer) is a Python library for
programmable, composable Docker image building.
It is used by benchkit to manage container-based experiments (Figure 7).
Pythainer is included in the artifact as a git submodule and will be installed
with the instructions below.

#### Install everything

##### 1. Clone the repository

```bash
git clone --recursive https://github.com/softwarelanguageslab/icpe26-benchkit-ae.git
cd icpe26-benchkit-ae/
```

#### 2. Set up Python environment

> **Python version:** use **Python 3.10-3.12** (3.12 is the reference version).
> **Python 3.14 is not supported** -- it triggers a `RecursionError` in
> seaborn/matplotlib during plot generation. If your system `python3` is 3.13+,
> create the virtualenv with an explicit 3.12 interpreter, e.g.
> `python3.12 -m venv .venv`.

```bash
# Create and activate virtual environment
python3 -m venv .venv
source .venv/bin/activate

# Install dependencies
pip install --upgrade pip
pip install -r requirements.txt

# Install the artifact library in editable mode
pip install -e .

# Install the framework components in editable mode
pip3 install --editable deps/benchkit
pip3 install --editable deps/schedkit
pip3 install --editable deps/pythainer
```

> **Note**: Benchmark sources (LevelDB, RocksDB, etc.) are fetched automatically
> by benchkit during the first run of each campaign via the `fetch()` method.
> No manual build step is required. The benchmark sources are stored in
> `~/.benchkit/benches/`.

---

## How results are produced and stored

Each experiment is expressed as a **campaign**.
When a campaign is executed, benchkit automatically creates:

* **one aggregated CSV file** that contains both the tabular data (columns for
  each variable and metric) and run metadata (platform, kernel version,
  commit hash, timestamps, etc.) embedded as `#`-prefixed comment lines at
  the top (and bottom) of the file.
* **one directory containing all per-run artifacts**

Both are stored under:

```
~/.benchkit/results/
```

They have the same name:

```
benchmark_<hostname>_<campaign_name>_<timestamp>.csv
benchmark_<hostname>_<campaign_name>_<timestamp>/
```

Example:

```
benchmark_proton_listing4_placement_spec_20260127_192431_194508.csv
benchmark_proton_listing4_placement_spec_20260127_192431_194508/
```

The directory contains:

* exact commands executed (`commands.sh`)
* generated figures (PNG/PDF)
* hierarchical subdirectories reflecting the parameter space
* in each of the "leaves" of the hierarchy:
  * per-run logs,
  * JSON results,
  * profiler outputs

For example, a flame-graph campaign (Listing 9 and Figure 6) produces the following
structure:

```
benchmark_vm_figure6_leveldb_flamegraph_20260128_205003_953967
├── benchkit-20260128-205034-01.pdf
├── benchkit-20260128-205034-01.png
├── commands.sh
├── diff_cas_vs_mcs.svg
├── diff_mcs_vs_cas.svg
└── nb_threads-32
    └── bench_name-readrandom
        └── scheduler-CLOSE
            ├── lock-caslock
            │   └── run-1
            │       ├── experiment_results.json
            │       ├── flamegraph.svg
            │       ├── perf.data
            │       ├── perf.folded
            │       ├── perf.report
            │       ├── schedkit.err
            │       └── schedkit.out
            └── lock-mcslock
                └── run-1
                    ├── experiment_results.json
                    ├── flamegraph.svg
                    ├── perf.data
                    ├── perf.folded
                    ├── perf.report
                    ├── schedkit.err
                    └── schedkit.out
```

At the **campaign directory level**, benchkit stores:
- the generated paper figures (PDF/PNG),
- differential flame graphs (`diff_*.svg`),
- and the full list of executed commands (`commands.sh`).

At the **per-run level**, benchkit stores:
- raw profiling data (`perf.data`, `perf.report`, `perf.folded`),
- derived (individual) flame graphs (`flamegraph.svg`),
- scheduler logs (`schedkit.out`, `schedkit.err`),
- and structured metrics (`experiment_results.json`).

This structure makes it possible to inspect **both the final figures used in the paper
and the raw profiler traces they were derived from**, supporting independent validation
and post-processing. Each "recorded configuration" has its own leaf directory
in the hierarchy, allowing for easy comparison across experiments.

**We strongly encourage reviewers to explore this directory**: it is designed
to make experiments transparent and inspectable.

To find your latest results after running a campaign:
```bash
ls -larth ~/.benchkit/results/
```
The most recent campaigns are listed last.

**About `/tmp/benchkit.sh` (command trace and reproducibility aid)**

During execution, benchkit records **every external command it executes**
(e.g., benchmark runs, `git clone`, build commands, scheduler control scripts)
into a temporary shell script located at:

```text
/tmp/benchkit.sh
```

This file is **append-only** and serves two purposes:

* **Live inspection**: users can monitor progress in real time using
  `tail -f /tmp/benchkit.sh` to see exactly which commands are being executed.
* **Post-mortem debugging and reproducibility**: in case of a crash or interruption,
  the last executed commands can be inspected and **re-run manually** by copy-pasting
  them from this file.

This mechanism is intentionally simple and transparent: it provides reviewers
with a concrete, low-level trace of what the framework does under the hood,
without requiring any internal instrumentation or logging format.

---

## Running the experiments

During execution, benchkit provides **live progress information** in the console
output, including an estimate of the **remaining execution time** for long-running
campaigns. This estimate is updated as runs complete and is especially useful for
experiments that sweep large parameter spaces (e.g., Figures 3 and 4).

---

### Adjusting experiment duration

Almost every script exposes two parameters that control execution time:

- **`nb_runs`**: number of repetitions per configuration (affects statistical confidence)
- **`duration_s`**: duration in seconds of each individual benchmark run
  (affects measurement stability)

Reviewers who want to **quickly verify that a script runs correctly** can reduce
these values. The full experiments in `experiments/` accept them as command-line
flags, e.g.:

```bash
python figure3_locks.py --nb-runs 1 --duration-s 3
```

This is especially useful for the long-running experiments (Figures 3 and 4).
The defaults reproduce the paper's values; run any experiment with `--help` to see
all available flags. The `examples/` listings instead pass these parameters directly
in the campaign constructor (edit the value in the script to change them).

> **Trade-off**: Reducing `nb_runs` increases variance in the plotted results;
> reducing `duration_s` may cause short-lived benchmarks to be dominated by
> startup overhead rather than steady-state behavior. The default values used
> in the scripts are those that produced the paper's figures. For a quick
> smoke test, `--nb-runs 1 --duration-s 5` are reasonable choices that still
> produce meaningful (if noisier) plots.

---

### Regenerating the paper figures

Each `experiments/` script produces its **paper-styled** figure automatically at
the end of the run (via `lib/plots.py`), saved as a PDF in
`~/.benchkit/results/`. The figures use standard fonts by default so they render
without a LaTeX toolchain; pass `--paper-fonts` for the exact paper typography:

```bash
python figure3_locks.py --paper-fonts
```

---

### Code Examples (`examples/`)

These scripts are runnable versions of the **code listings** in the paper.
They are designed to run quickly on any Linux machine and illustrate specific
benchkit features. All examples are self-contained and require only the basic
system packages listed above (no NUMA server, no Docker).

Each example script contains a detailed docstring with paper references,
expected timing, hardware context, prerequisites, and output description.

| Script | Paper Listing | What it demonstrates | Est. time |
|--------|-------------|----------------------|-----------|
| `listing1_leveldb.py` | Listing 1 | Basic campaign (benchmark + parameter space + plot) | ~5 min |
| `listing2_spec.py` | Listing 2 | SPEC baseline variability under default scheduling (requires license) | ~5-30 min |
| `listing3_heater.py` | Listing 3 | Per-CPU sequential heater sweep | ~3 min (24 threads) |
| `listing4_spec_placement.py` | Listing 4 | TasksetWrap for CPU placement (SPEC CPU 2017, requires license) | ~5-120 min |
| `listing4_leveldb_placement.py` | Listing 4 | TasksetWrap for CPU placement (LevelDB) | ~20 min |
| `listing5_leveldb_locks.py` | Listing 5 | Lock interposition via tilt (LD_PRELOAD) | ~15 min |
| `listing6_sched_hooks.py` | Listing 6 | Scheduler hook mechanism (illustrative, no benchmark run) | instant |
| `listing7_leveldb_schedulers.py` | Listing 7 | Scheduler sweep with pre/post-run hooks | ~15 min |
| `listing8_leveldb_perfstat.py` | Listing 8 | perf stat + scheduling policies | ~10 min |
| `listing9_leveldb_flamegraph.py` | Listing 9 | Flame graph and differential flame graph generation | ~2 min |

```bash
cd examples/

# Listing 1: Basic LevelDB campaign
python listing1_leveldb.py

# Listing 2: SPEC baseline variability (requires license, only on x86)
python listing2_spec.py /path/to/cpu2017-1.1.9.iso

# Listing 3: Sequential heater (per-CPU characterization)
python listing3_heater.py

# Listing 4: TasksetWrap for CPU placement (SPEC CPU 2017, requires license, only on x86)
python listing4_spec_placement.py /path/to/cpu2017-1.1.9.iso

# Listing 4: TasksetWrap for CPU placement (LevelDB variant)
python listing4_leveldb_placement.py

# Listing 5: Lock campaign with tilt
python listing5_leveldb_locks.py

# Listing 6: Scheduler hook demo (no benchmark run)
python listing6_sched_hooks.py

# Listing 7: Scheduler campaign
python listing7_leveldb_schedulers.py

# Listing 8: perf-stat integration
python listing8_leveldb_perfstat.py

# Listing 9: Flame graph generation
python listing9_leveldb_flamegraph.py
```

---

### Full experiments (paper figures)

Each script in `experiments/` reproduces one or more figures from the paper.
Below is a detailed tutorial for each figure.

---

#### Figure 2: Hybrid-Core Variability Analysis

**Paper reference**: Section 3 (Drilldown Case Study on Hybrid-Core Variability)

**Hardware used in the paper**: Platform A — hybrid-core laptop
(AMD Ryzen AI 9 HX 370, 4 P-cores + 8 E-cores, 12 cores / 24 threads, 32 GiB RAM).

**What it produces**: A two-panel figure showing (left) runtime/throughput
variability under different CPU placements and (right) per-CPU throughput
from the sequential heater.

**Scripts involved** (run in order):

| Step | Script | What it does | Est. time |
|------|--------|-------------|-----------|
| 1 | `figure2_heater.py` | Per-CPU heater sweep to identify P/E cores (Fig. 2 right) | ~3 min |
| 2 | `figure2_placement_spec.py` | Placement experiment with SPEC CPU 2017 (Fig. 2 left, requires license) | ~5-120 min |
| 2 (alt.) | `figure2_placement_leveldb.py` | Open-source alternative using LevelDB (same methodology, no license needed) | ~5 min |

**Procedure**:

```bash
cd experiments/

# Step 1: Characterize your CPUs (identify P vs E cores)
python figure2_heater.py
# -> Inspect the bar plot to determine which cores are fast (P) vs slow (E)

# Step 2: SPEC placement experiment (as used in the paper, requires license)
# Edit P_CORES and E_CORES in figure2_placement_spec.py based on Step 1
python figure2_placement_spec.py /path/to/cpu2017-1.1.9.iso

# Step 2 (alternative): Open-source placement experiment (LevelDB, no license needed)
# Edit P_CORES and E_CORES in figure2_placement_leveldb.py based on Step 1
python figure2_placement_leveldb.py
```

**Notes**:
- The paper uses **SPEC CPU 2017** for Figure 2 (left). If you have a SPEC
  license, use `figure2_placement_spec.py` to reproduce the exact experiment.
- If you do not have a SPEC license, `figure2_placement_leveldb.py` demonstrates
  the same benchkit features and methodology using LevelDB as a drop-in
  replacement.
- On **homogeneous** machines (no P/E asymmetry), all three placement conditions
  will produce similar results — this is expected.

---

#### Figure 3: Lock Throughput Study (5-panel)

**Paper reference**: Section 4.1 (Studying Locking Impact)

**Hardware used in the paper**: Platform B — NUMA server
(2x Kunpeng 920-4826, 96 cores, 4 NUMA nodes, 539 GiB RAM, aarch64).

**What it produces**: A 5-panel line plot showing throughput vs. thread count
for 8 lock implementations across KyotoCabinet, LevelDB/readrandom,
LevelDB/seekrandom, RocksDB/readrandom, and RocksDB/seekrandom.

**Expected execution time**: with the default paper parameters (`nb_runs=3`,
`duration_s=10`), several hours on the paper's 96-core server; a reduced run
(`--nb-runs 2 --duration-s 5`) took ~96 minutes (measured: `real 95m40s`).
Thread counts are automatically filtered to available CPUs, so it runs faster
on smaller machines.

**Procedure**:

```bash
cd experiments/
python figure3_locks.py
```

**Notes**:
- The tilt shared library (lock interposition) is built automatically.
- On non-NUMA machines, the NUMA-aware locks (CNA, HMCS) may not show the
  performance advantages reported in the paper.
- RocksDB requires additional system packages: `libgflags-dev liblz4-dev libzstd-dev zlib1g-dev`.

---

#### Figure 4: Scheduler Throughput Study (5-panel)

**Paper reference**: Section 4.2 (Studying Thread-Placement Impact)

**Hardware used in the paper**: Platform B — NUMA server
(2x Kunpeng 920-4826, 96 cores, 4 NUMA nodes, 539 GiB RAM, aarch64).

**What it produces**: A 5-panel line plot showing throughput vs. thread count
for 6 scheduling policies across the same benchmarks as Figure 3.

**Expected execution time**: with the default paper parameters (`nb_runs=3`,
`duration_s=10`), several hours on the paper's 96-core server; a reduced run
(`--nb-runs 2 --duration-s 5`) took ~96 minutes (measured: `real 95m26s`).

**Procedure**:

```bash
cd experiments/
python figure4_schedulers.py
```

**Notes**:
- The schedkit daemon is built and managed automatically via pre/post-run hooks.
- On non-NUMA machines, NUMA-aware policies (CLOSE, FAR, etc.) may not produce
  meaningful differences.

---

#### Figure 5: perf-stat Analysis with Schedulers (5-panel)

**Paper reference**: Section 4.3 (Using perf for Profiling and Run-Time Statistics)

**Hardware used in the paper**: Platform B — NUMA server (2x Kunpeng 920-4826, 96 cores, aarch64).

**What it produces**: A 5-panel bar chart for LevelDB readrandom at 24 threads:
throughput, context-switches, cpu-migrations, page-faults, and cache-misses,
under 6 scheduling policies.

**Expected execution time**: ~10 minutes (measured: `real 9m58s`).

**Prerequisites**: `sudo sysctl -w kernel.perf_event_paranoid=-1`

**Procedure**:

```bash
cd experiments/
python figure5_leveldb_perfstat.py
```

---

#### Figure 6: Differential Flame Graphs

**Paper reference**: Section 4.4 (Visualizing Performance with Flame Graphs in benchkit)

**Hardware used in the paper**: Platform B — NUMA server (2x Kunpeng 920-4826, 96 cores, aarch64).

**What it produces**: Individual flame graphs for CAS and MCS locks, plus two
differential flame graphs showing where each lock spends more or less time
than the other. The paper highlights that CAS spends significantly more time
in `pthread_mutex_lock` compared to MCS.

**Expected execution time**: ~1 minute (measured: `real 0m56s`).

**Prerequisites**: `sudo sysctl -w kernel.perf_event_paranoid=-1`

**Procedure**:

```bash
cd experiments/
python figure6_leveldb_flamegraph.py
```

**Output**: Look for `flamegraph.svg` files in per-run directories and
`diff_*.svg` files at the campaign root (see "How results are produced
and stored" above).

---

#### Figure 7: Framework Overhead

**Paper reference**: Section 5 (Overhead of benchkit)

**Hardware used in the paper**: Intel Core i7-13800H laptop, Ubuntu 22.04.5, Linux 6.8.0.

**What it produces**: A 3-panel strip plot (one per thread count: 2, 4, 8)
comparing throughput of benchkit vs. hand-written shell scripts, on host and
inside Docker. The paper shows <2.2% overhead on host and <0.7% inside Docker.

**Expected execution time**: ~20 minutes total (broken down below).

**Prerequisites**: Docker installed and current user in `docker` group.

**Procedure** (4 steps, must be run in order):

```bash
cd experiments/figure7_overhead/

# Step 1: Run benchkit campaigns (host + Docker)
# This also builds the Docker image and clones LevelDB.
# Est. time: ~12 minutes (image build + 2 campaigns)
python figure7_leveldb_overhead.py

# Step 2: Run the shell baseline on the host
# Est. time: ~5 minutes
./shell_host.sh

# Step 3: Run the shell baseline inside Docker
# Est. time: ~5 minutes
./shell_docker.sh

# Step 4: Generate the final comparison figure
python plot_overhead.py
# -> Output: ~/.benchkit/results/figure7_overhead.{pdf,png}
# -> Console: overhead summary table
```

**Notes**:
- Step 1 must run before Steps 2-3 because it builds the Docker image and
  clones LevelDB into `~/.benchkit/benches/`.
- The shell scripts reuse the LevelDB source cloned by benchkit and the
  Docker image built by pythainer.

---

### Summary of all experiments

| Script | Figure | Section | Platform | Est. time | Needs |
|--------|--------|---------|----------|-----------|-------|
| `figure2_heater.py` | 2 (right) | 3.2 | A (laptop) | ~3 min | — |
| `figure2_placement_spec.py` | 2 (left) | 3.1-3.3 | A (laptop) | 5-120 min | SPEC license |
| `figure2_placement_leveldb.py` | 2 (left) | 3.3 | A (laptop) | ~5 min | — (alternative) |
| `figure3_locks.py` | 3 | 4.1 | B (server) | ~5 h (96 min reduced) | — |
| `figure4_schedulers.py` | 4 | 4.2 | B (server) | ~5 h (96 min reduced) | — |
| `figure5_leveldb_perfstat.py` | 5 | 4.3 | B (server) | ~10 min | perf access |
| `figure6_leveldb_flamegraph.py` | 6 | 4.4 | B (server) | ~1 min | perf access |
| `figure7_overhead/` | 7 | 5 | Any Linux | ~20 min | Docker |

---

## Troubleshooting

If an experiment crashes, inspecting the last lines of `/tmp/benchkit.sh`
often reveals the exact command that failed (useful to try again and
troubleshoot the error).

Benchkit automatically fetches and builds benchmark sources (e.g., LevelDB,
RocksDB, KyotoCabinet, SPEC CPU, microbenchmarks) into `~/.benchkit/benches/`.
This directory acts as a **local cache** to avoid re-downloading and rebuilding
benchmarks across runs. In rare cases (e.g., interruption during a fetch or build),
this cache may become **inconsistent**. For example, a directory may exist even
though the benchmark source was not fully cloned or built.
If a benchmark fails unexpectedly during the `fetch` or `build` phase, a simple
workaround is to remove the corresponding directory (or the entire
`~/.benchkit/benches/` directory) and re-run the experiment. Benchkit will
then re-fetch and rebuild all required benchmarks from scratch.

### Common issues

| Symptom | Cause | Fix |
|---------|-------|-----|
| `perf` permission error | `perf_event_paranoid` too high | `sudo sysctl -w kernel.perf_event_paranoid=-1` |
| Docker permission denied | User not in `docker` group | `sudo usermod -aG docker $USER` then re-login |
| `cmake` build failure | Missing dev libraries | Install all packages from the "System Packages" section |
| `ModuleNotFoundError` | Virtual environment not activated | `source .venv/bin/activate` |
| Inconsistent benchmark cache | Interrupted fetch/build | `rm -rf ~/.benchkit/benches/<benchmark>` and re-run |
| Flame graph scripts missing or broken | Interrupted clone of FlameGraph tools | `rm -rf ~/.benchkit/tools/` and re-run |

---

## Artifact badges

This artifact obtained the following badges:

* **Artifacts Available**: The artifact is hosted on a public GitHub
  repository with all source code, scripts, and documentation. In addition,
  all frameworks and tools introduced in the paper (benchkit, tilt, and
  schedkit) are publicly available as open-source projects under the MIT
  license.
* **Artifacts Evaluated -- Functional**: All scripts are documented,
  consistent with the paper, complete (open-source alternatives provided
  where proprietary software is needed), and exercisable on any Linux machine.
* **Artifacts Evaluated -- Reusable**: Each script is thoroughly documented
  with paper references, hardware context, timing expectations, prerequisites,
  and step-by-step instructions. The modular structure (benchmarks, locks,
  schedulers, profilers as independent components) facilitates repurposing
  for new studies.

---
