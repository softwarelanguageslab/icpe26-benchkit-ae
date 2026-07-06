#!/bin/sh
# Copyright (C) 2024 Vrije Universiteit Brussel. All rights reserved.
# SPDX-License-Identifier: MIT
#
# Figure 7: Shell-based overhead measurement (host execution)
#
# Paper reference: Section 5 (Overhead of benchkit), Figure 7.
#
# This script is the hand-written shell equivalent of the benchkit campaign,
# used to measure framework overhead. It performs exactly the same steps as
# the benchkit campaign in figure7_leveldb_overhead.py but using plain shell:
#   1. Builds db_bench from the LevelDB source (reuses benchkit's cached clone)
#   2. Runs fillseq once to initialize the database
#   3. Runs readrandom for threads in {2, 4, 8}, 10 repetitions each
#   4. Saves raw output to ~/.benchkit/results/figure7_shell_host/
#
# Prerequisites:
#   - Run figure7_leveldb_overhead.py first (it clones LevelDB into ~/.benchkit/benches/)
#   - System packages: build-essential, cmake, libsnappy-dev
#
# Expected execution time: ~5 minutes (3 thread counts x 10 runs x 10 s)
#
# How to run:
#   cd experiments/figure7_overhead/
#   ./shell_host.sh
#
# After running, use plot_overhead.py to generate the comparison figure.

set -e

NB_RUNS=10
DURATION=10

# Benchkit home on host (supports BENCHKIT_HOME override)
BENCHKIT_HOME_HOST="${BENCHKIT_HOME:-$HOME/.benchkit}"

# LevelDB location (matches benchkit default)
LEVELDB_SRC="$BENCHKIT_HOME_HOST/benches/leveldb"

# Build directory
BUILD_DIR="$LEVELDB_SRC/build-shellhost"
DB_DIR="$BUILD_DIR/tmp/shell_leveldb_db"

# Output directory
OUT_DIR="$BENCHKIT_HOME_HOST/results/figure7_shell_host"

mkdir -p "$BUILD_DIR" "$DB_DIR" "$OUT_DIR"

echo "[host] benchkit home: $BENCHKIT_HOME_HOST"
echo "[host] leveldb src:   $LEVELDB_SRC"
echo "[host] build dir:     $BUILD_DIR"
echo "[host] db dir:        $DB_DIR"
echo "[host] output dir:    $OUT_DIR"

cd "$BUILD_DIR"

# Configure & build db_bench
echo "[host] Building db_bench..."
cmake -DCMAKE_BUILD_TYPE=Release "$LEVELDB_SRC"
make -j "$(nproc --all)" db_bench

# Initialize DB once (fillseq)
echo "[host] Initializing database..."
./db_bench \
  --threads=1 \
  --benchmarks=fillseq \
  --db="$DB_DIR"

# Sweep nb_threads and repetitions
for threads in 2 4 8; do
  for rep in $(seq 1 "$NB_RUNS"); do
    out_file="$OUT_DIR/run_t${threads}_r${rep}.txt"
    echo "[host] threads=$threads rep=$rep -> $out_file"

    ./db_bench \
      --threads="$threads" \
      --benchmarks=readrandom \
      --use_existing_db=1 \
      --db="$DB_DIR" \
      --duration="$DURATION" \
      > "$out_file"
  done
done

echo "[host] Done. Results in: $OUT_DIR"
