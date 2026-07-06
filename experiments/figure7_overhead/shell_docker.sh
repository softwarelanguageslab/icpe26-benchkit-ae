#!/bin/sh
# Copyright (C) 2024 Vrije Universiteit Brussel. All rights reserved.
# SPDX-License-Identifier: MIT
#
# Figure 7: Shell-based overhead measurement (Docker execution)
#
# Paper reference: Section 5 (Overhead of benchkit), Figure 7.
#
# This script is the hand-written shell equivalent of the benchkit campaign
# running inside a Docker container. It performs the same steps as shell_host.sh
# but executes all commands inside the benchkit_overhead Docker image:
#   1. Builds db_bench inside the container
#   2. Runs fillseq once to initialize the database
#   3. Runs readrandom for threads in {2, 4, 8}, 10 repetitions each
#   4. Saves raw output to ~/.benchkit/results/figure7_shell_docker/
#
# Prerequisites:
#   - Run figure7_leveldb_overhead.py first (it builds the Docker image and
#     clones LevelDB into ~/.benchkit/benches/)
#   - Docker installed and current user in docker group
#
# Expected execution time: ~5 minutes (3 thread counts x 10 runs x 10 s)
#
# How to run:
#   cd experiments/figure7_overhead/
#   ./shell_docker.sh
#
# After running, use plot_overhead.py to generate the comparison figure.

set -e

SCRIPT_DIR="$(cd "$(dirname "$0")" && pwd)"
REPO_DIR="$(cd "$SCRIPT_DIR/../../.." && pwd)"

IMAGE_NAME="benchkit_overhead"
NB_RUNS=10
DURATION=10

# Benchkit home on host (supports BENCHKIT_HOME override)
BENCHKIT_HOME_HOST="${BENCHKIT_HOME:-$HOME/.benchkit}"

# Benchkit home inside container
BENCHKIT_HOME_CONT="/home/user/.benchkit"

# LevelDB location inside container
LEVELDB_SRC_CONT="$BENCHKIT_HOME_CONT/docker/benches/leveldb"

# Build directory inside container
BUILD_DIR_CONT="$LEVELDB_SRC_CONT/build-shelldocker"
DB_DIR_CONT="$BUILD_DIR_CONT/tmp/shell_leveldb_db"

# Output directory on host
OUT_DIR="$BENCHKIT_HOME_HOST/results/figure7_shell_docker"

mkdir -p "$OUT_DIR"

echo "[docker] repo (host):          $REPO_DIR"
echo "[docker] benchkit home (host): $BENCHKIT_HOME_HOST"
echo "[docker] benchkit home (ct):   $BENCHKIT_HOME_CONT"
echo "[docker] leveldb (ct):         $LEVELDB_SRC_CONT"
echo "[docker] build (ct):           $BUILD_DIR_CONT"
echo "[docker] db (ct):              $DB_DIR_CONT"
echo "[docker] output (host):        $OUT_DIR"

run_in_docker() {
  # Run a single command string inside the container
  docker run --rm --tty --interactive \
    --volume="$REPO_DIR":"/home/user/workspace" \
    --volume="$BENCHKIT_HOME_HOST":"$BENCHKIT_HOME_CONT" \
    --hostname=benchkit_overhead \
    --user=1000:1000 \
    "$IMAGE_NAME" \
    bash --login -c "$1"
}

# Ensure build/db directories exist
run_in_docker "mkdir -p '$BUILD_DIR_CONT' '$DB_DIR_CONT'"

# Configure & build db_bench inside container
echo "[docker] Building db_bench..."
run_in_docker "cd '$BUILD_DIR_CONT' && cmake -DCMAKE_BUILD_TYPE=Release '$LEVELDB_SRC_CONT'"
run_in_docker "cd '$BUILD_DIR_CONT' && make -j \$(nproc --all) db_bench"

# Initialize DB once (fillseq)
echo "[docker] Initializing database..."
run_in_docker "cd '$BUILD_DIR_CONT' && ./db_bench --threads=1 --benchmarks=fillseq --db='$DB_DIR_CONT'"

# Sweep nb_threads and repetitions
for threads in 2 4 8; do
  for rep in $(seq 1 "$NB_RUNS"); do
    out_file="$OUT_DIR/run_t${threads}_r${rep}.txt"
    echo "[docker] threads=$threads rep=$rep -> $out_file"

    cmd="cd '$BUILD_DIR_CONT' && ./db_bench \
      --threads=$threads \
      --benchmarks=readrandom \
      --use_existing_db=1 \
      --db='$DB_DIR_CONT' \
      --duration=$DURATION"

    # Redirect stdout to the outfile on the host
    run_in_docker "$cmd" > "$out_file"
  done
done

echo "[docker] Done. Results in: $OUT_DIR"
