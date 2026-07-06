# Copyright (C) 2024 Vrije Universiteit Brussel. All rights reserved.
# SPDX-License-Identifier: MIT
"""
Scheduler (schedkit) integration for benchkit campaigns.

Paper reference:
    Section 4.2 (Studying Thread-Placement Impact), Listings 6-7 and Figure 4.

This module wraps the schedkit daemon (``deps/schedkit/``), a user-space
scheduler that dynamically adjusts thread CPU affinities during benchmark
execution according to a chosen placement policy.

Architecture:
    SchedProcess manages the daemon lifecycle via two campaign hooks:

    - **start_sched_hook** (pre-run): reads the ``scheduler`` variable from
      the current campaign record, computes the CPU ordering for the selected
      policy, and launches the schedkit daemon in the background.
    - **end_sched_hook** (post-run): terminates the daemon so no residual
      state persists across runs.

    Because the hooks receive the campaign variables automatically, scheduling
    policies become ordinary run-time parameters that benchkit sweeps over in
    the cartesian product, just like thread counts or lock types.

Supported scheduling policies:
    Normal      Default Linux scheduler (no intervention; daemon not started).
    FAR         Spread threads evenly across NUMA nodes to reduce local
                contention, at the cost of increased remote memory access.
    CLOSE       Pack threads onto nearby cores to maximize cache locality.
    AsymSched   NUMA-aware asymmetric scheduling (Lepers et al., ATC '15).
    SAM         Sharing-Aware Mapping (Srikanthan et al., ATC '15).
    SAS         Sharing-Aware Scheduling (Tam et al., EuroSys '07).

Key functions:
    get_scheduler()     Returns a configured SchedProcess instance whose
                        ``start_sched_hook`` and ``end_sched_hook`` methods
                        can be passed directly to campaign hooks.
"""

from pathlib import Path
from typing import List

import psutil
from benchkit.benchmark import PathType, RecordResult, WriteRecordFileFunction
from benchkit.platforms import Platform
from benchkit.shell.shellasync import shell_async
from benchkit.utils.dir import gitmainrootdir

_repo_dir = gitmainrootdir().resolve()
_sched_dir = _repo_dir / "deps/schedkit"
_venv_dir = _repo_dir / ".venv"

# Available scheduling policies
SCHEDULERS = [
    "Normal",
    "FAR",
    "CLOSE",
    "AsymSched",
    "SAM",
    "SAS",
]

# Pretty names for plotting
PRETTY_SCHEDULERS = {
    "Normal": "Default Linux Scheduler",
    "FAR": "NUMA-aware FAR",
    "CLOSE": "NUMA-aware CLOSE",
    "AsymSched": "AsymSched",
    "SAM": "Sharing-Aware Mapping",
    "SAS": "Sharing-Aware Scheduling",
}


class SchedProcess:
    """
    Manages the schedkit scheduling daemon.

    This class provides pre-run and post-run hooks that can be used in
    benchkit campaigns to control thread placement policies.
    """

    def __init__(
        self,
        platform: Platform,
        process_filter: List[str],
        interval_seconds: float | None = 0.2,
        cpu_percentage: float | None = 0.00,
    ) -> None:
        """
        Initialize the scheduler process manager.

        Args:
            platform: Target platform for scheduling.
            process_filter: List of process names to manage (e.g., ["db_bench"]).
            interval_seconds: Scheduling interval in seconds.
            cpu_percentage: CPU usage threshold for considering a thread "active".
        """
        self.platform = platform
        self._process_filter = [str(p) for p in process_filter]
        self._interval_seconds = interval_seconds
        self._cpu_percentage = cpu_percentage

        self.process = None
        self._schedkit_stdout_filename = None
        self._schedkit_stderr_filename = None
        self._python_path = _venv_dir / "bin/python3" if _venv_dir.is_dir() else "python3"

    def _get_command_head(self) -> List[str]:
        return [f"{self._python_path}", "schedkit.py"]

    def _check_and_terminate_leftover_processes(self) -> None:
        """Check for and terminate any leftover schedkit processes."""
        for proc in psutil.process_iter(attrs=["pid", "name", "cmdline"]):
            try:
                if proc.info["cmdline"] and "schedkit.py" in proc.info["cmdline"]:
                    pid = proc.info["pid"]
                    print(f"Terminating leftover schedkit process with PID: {pid}")
                    psutil.Process(pid).terminate()
                    psutil.Process(pid).wait(timeout=5)
            except (psutil.NoSuchProcess, psutil.AccessDenied, psutil.ZombieProcess):
                continue

    def cleanup(self) -> None:
        """Clean up any leftover scheduler processes."""
        self._check_and_terminate_leftover_processes()

        command = self._get_command_head() + ["cleanup"]
        self.platform.comm.shell(
            command=command,
            current_dir=_sched_dir,
        )

    def start(
        self,
        scheduler_name: str,
        process_filter: List[str],
        cpu_order: List[int],
        schedkit_stdout_filename: Path,
        schedkit_stderr_filename: Path,
    ) -> None:
        """Start the scheduler daemon with the given configuration."""
        command_head = self._get_command_head()

        options = ["run", f"{scheduler_name}"]
        if process_filter:
            process_filter_str = ",".join(map(str, process_filter))
            options.append(f"--filter={process_filter_str}")
        if self._interval_seconds is not None:
            options.append(f"--interval={self._interval_seconds}")
        if self._cpu_percentage is not None:
            options.append(f"--cpu-percentage={self._cpu_percentage}")
        if cpu_order:
            cpu_order_str = ",".join(map(str, cpu_order))
            options.append(f"--cpu-order={cpu_order_str}")

        command = command_head + options

        self.process = shell_async(
            command=command,
            stdout_path=schedkit_stdout_filename,
            stderr_path=schedkit_stderr_filename,
            platform=self.platform,
            current_dir=_sched_dir,
        )
        rc = self.process.premature_exitcode()
        if rc is not None:
            raise ValueError(
                f"SchedKit exited prematurely, please check logs:\n"
                f"  {schedkit_stderr_filename}\n"
                f"  {schedkit_stdout_filename}"
            )

    def stop(self) -> None:
        """Stop the scheduler daemon."""
        if self.process is not None:
            pec = self.process.premature_exitcode()
            if pec is not None:
                raise ValueError(
                    f"SchedKit exited prematurely with code {pec}, "
                    f"please check logs:\n"
                    f"  {self._schedkit_stderr_filename}\n"
                    f"  {self._schedkit_stdout_filename}"
                )

            self.process.kill()
            self.process = None

    def start_sched_hook(
        self,
        build_variables: RecordResult,
        run_variables: RecordResult,
        other_variables: RecordResult,
        record_data_dir: PathType,
    ) -> None:
        """
        Pre-run hook to start the scheduler before each benchmark run.

        This hook reads the "scheduler" variable from the campaign parameters
        and starts the appropriate scheduling policy.
        """
        assert build_variables or run_variables or True  # silence warning

        self.cleanup()

        selected_scheduler = other_variables["scheduler"]

        # "Normal" means use the default Linux scheduler (no intervention)
        if selected_scheduler == "Normal":
            return

        self._schedkit_stdout_filename = record_data_dir / "schedkit.out"
        self._schedkit_stderr_filename = record_data_dir / "schedkit.err"

        # Determine CPU order based on policy
        match selected_scheduler:
            case "CLOSE":
                cpu_order = self.platform.cpu_order(provided_order="desc")
            case "FAR":
                cpu_order = self.platform.cpu_order(provided_order="even")
            case _:
                cpu_order = []

        # Ensure CPU 0 is available for certain policies
        if selected_scheduler in ["CLOSE", "FAR"]:
            if cpu_order[0] != 0 and cpu_order[-1] == 0:
                cpu_order = [cpu_order[0]] + cpu_order

        self.start(
            scheduler_name=selected_scheduler,
            process_filter=self._process_filter,
            cpu_order=cpu_order,
            schedkit_stdout_filename=self._schedkit_stdout_filename,
            schedkit_stderr_filename=self._schedkit_stderr_filename,
        )

    def end_sched_hook(
        self,
        experiment_results_lines: List[RecordResult],
        record_data_dir: PathType,
        write_record_file_fun: WriteRecordFileFunction,
    ) -> RecordResult:
        """
        Post-run hook to stop the scheduler after each benchmark run.
        """
        assert record_data_dir or write_record_file_fun  # silence warning

        self.stop()

        return experiment_results_lines[0]


def get_scheduler(
    platform: Platform,
    process_filter: List[str] | None = None,
) -> SchedProcess:
    """
    Get a configured scheduler instance for the given platform.

    Args:
        platform: Target platform.
        process_filter: List of process names to manage. Defaults to common
            benchmark process names.

    Returns:
        SchedProcess instance with start_sched_hook and end_sched_hook methods
        ready for use in campaigns.
    """
    if process_filter is None:
        process_filter = [
            "db_bench",  # LevelDB, RocksDB
            "benchmark",  # KyotoCabinet
            "blogbench",  # BlogBench
            "cpppathtracer",  # C++ path tracer
            "raytracer",  # Ray tracer
        ]

    schedkit = SchedProcess(
        platform=platform,
        process_filter=process_filter,
        interval_seconds=0.2,
        cpu_percentage=0.00,
    )
    schedkit.cleanup()

    return schedkit
