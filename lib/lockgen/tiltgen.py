#!/usr/bin/env python3
# Copyright (C) 2024 Vrije Universiteit Brussel. All rights reserved.
# SPDX-License-Identifier: MIT
"""
tilt-compatible C wrapper generation for libvsync spinlocks.

This module generates the C source files that allow tilt to interpose
pthread_mutex calls with alternative spinlock implementations from the
libvsync library (``deps/libvsync/``).

For each lock, the generator:
1. Parses the lock's header file to determine its API shape:
   - Does ``acquire()`` take a per-thread context argument? (context-aware vs. context-free)
   - Is ``tryacquire()`` implemented?
   - Does the context require initialization (``node_init``)?
   - Is there a ``destroy()`` function?
2. Selects the appropriate C template (template.c or template_context.c).
3. Fills in the template with the lock name, context type, and conditional
   code snippets (tryacquire, node_init, destroy).
4. Writes the generated ``.c`` file to the output directory.

The generated files are then compiled by the CMakeLists.txt in
``generatedlocks/`` into individual shared libraries (one ``.so`` per lock),
which tilt loads via LD_PRELOAD.

Key functions:
    get_context_info()          Analyze a lock header and return its API properties.
    generate_tilt_file()        Generate one C wrapper for a given lock.
    generate_all_vsync_locks()  Generate wrappers for all locks in libvsync.
    generate_locks_from_dir()   Generate wrappers for locks in an arbitrary directory.
"""

import re
from pathlib import Path
from string import Template
from typing import List


def get_context_info(lock_header_path: Path) -> (bool, str, bool, bool, bool):
    """
    Determines if a lock requires a per-thread context, extracts the context type,
    checks if the lock has a tryacquire function, determines if the context must be initialized,
    and checks for the existence of a destroy function.

    Args:
        lock_header_path (Path): Path to the lock's header file.

    Returns:
        (bool, str, bool, bool, bool): A tuple where:
            - The first element indicates if the lock requires context.
            - The second element is the context type (or None if not applicable).
            - The third element indicates if tryacquire is implemented.
            - The fourth element indicates if the context requires initialization.
            - The fifth element indicates if a destroy function is implemented.
    """
    with lock_header_path.open() as f:
        content = f.read()

    # Regex patterns to match acquire, tryacquire, and destroy function signatures
    acquire_pattern = re.compile(
        r"^\s*static\s+.*?\s+\w+_acquire\s*\(\s*([^\)]*?)\)",  # Extract parameters
        re.MULTILINE,
    )
    tryacquire_pattern = re.compile(
        r"^\s*static\s+.*?\s+\w+_tryacquire\s*\(",  # Check for tryacquire function
        re.MULTILINE,
    )
    node_init_pattern = re.compile(
        r"^\s*static\s+.*?\s+\w+_node_init\s*\(",  # Check for node_init function
        re.MULTILINE,
    )
    destroy_pattern = re.compile(
        r"^\s*static\s+.*?\s+\w+_destroy\s*\(",  # Check for destroy function
        re.MULTILINE,
    )

    acquire_match = acquire_pattern.search(content)
    if not acquire_match:
        raise ValueError(f"No acquire function found in {lock_header_path}")

    # Extract the parameters from the acquire function
    parameters = acquire_match.group(1)

    # Split the parameters by commas to check if there's more than one
    params = [param.strip() for param in parameters.split(",")]

    # If there is only one parameter, it's not context-aware
    if len(params) == 1:
        context_required = False
        context_type = None
    else:
        context_required = True
        context_param = params[1]
        # The type is the first word in the parameter declaration:
        context_type = context_param.split()[0]

    # Check if tryacquire function exists
    tryacquire_exists = bool(tryacquire_pattern.search(content))

    # Check if node initialization is required
    context_init_required = bool(node_init_pattern.search(content))

    # Check if destroy function exists
    destroy_exists = bool(destroy_pattern.search(content))

    return context_required, context_type, tryacquire_exists, context_init_required, destroy_exists


def generate_tilt_file(
    lock_name: str,
    lock_header_dir: Path,
    output_dir: Path,
    include_path: str,
) -> None:
    """
    Generates a tilt-compatible lock wrapper for a given lock name.

    Args:
        lock_name (str): The name of the lock (e.g., "mcslock").
        vsync_path (Path): Path to the `vsync` directory.
        output_dir (Path): Path to the directory where the generated file will be saved.
    """
    template_contextfree_file = Path(__file__).parent / "template.c"
    template_contextaware_file = Path(__file__).parent / "template_context.c"
    template_contexttrylock_file = Path(__file__).parent / "template_context_trylock.c"
    output_file = output_dir / f"{lock_name}.c"
    lock_header_path = lock_header_dir / f"{lock_name}.h"

    # Ensure the lock header exists
    if not lock_header_path.is_file():
        raise FileNotFoundError(f"Lock header file not found: {lock_header_path}")

    if not output_dir.is_dir():
        output_dir.mkdir(parents=True)

    # Determine lock properties
    requires_ctx, context_type, tryacquire_exists, context_init_required, destroy_exists = (
        get_context_info(lock_header_path)
    )
    template_to_use = template_contextaware_file if requires_ctx else template_contextfree_file

    # Adjust the implementation of tryacquire
    if tryacquire_exists:
        if requires_ctx:
            tryacquire_impl = (
                Template(template_contexttrylock_file.read_text())
                .substitute(
                    LOCK=lock_name,
                    CONTEXT_TYPE=context_type or "",
                )
                .rstrip()
            )
        else:
            tryacquire_impl = f"    return {lock_name}_tryacquire(&m->lock);"
    else:
        tryacquire_impl = (
            "    (void) m;\n"
            '    fprintf(stderr, "Error: tryacquire not implemented for ${LOCK}\\n");\n'
            "    exit(EXIT_FAILURE);"
        )

    # Adjust the lock implementation for context initialization
    node_init_code = f"\n    {lock_name}_node_init(node);" if context_init_required else ""

    # Adjust the lock implementation for destroy
    destroy_code = f"    {lock_name}_destroy(&m->lock);" if destroy_exists else "    (void) m;"

    # Read the template
    template_content = template_to_use.read_text()
    template = Template(template_content)

    # Substitute placeholders in the template
    content = template.substitute(
        LOCK=lock_name,
        CONTEXT_TYPE=context_type or "",
        TRYACQUIRE_IMPLEMENTATION=tryacquire_impl,
        NODE_INIT=node_init_code,
        DESTROY_IMPLEMENTATION=destroy_code,
        SPINLOCK_INCLUDE_PATH=f"{include_path}",
    )

    # Write the generated file
    output_file.write_text(content)
    context_type_msg = "context-aware" if requires_ctx else "context-free"
    print(f"Generated tilt file for {context_type_msg} lock: {output_file}")


def generate_all_vsync_locks(
    vsync_dir: Path,
    output_dir: Path,
    given_locks: List[str] = (),
) -> None:
    """
    Generates tilt-compatible lock wrappers for all locks in the vsync repository.

    Args:
        vsync_dir (Path): Path to the `vsync` repository.
        output_dir (Path): Path to the directory where the generated files will be saved.
        given_locks (List[str]): List of lock names to generate.
    """
    spinlock_dir = vsync_dir / "include" / "vsync" / "spinlock"
    locks = [lock_name.stem for lock_name in spinlock_dir.glob("*.h")]
    if given_locks:
        locks = [lock_name for lock_name in locks if lock_name in given_locks]

    for lock_name in locks:
        try:
            generate_tilt_file(
                lock_name=lock_name,
                lock_header_dir=vsync_dir / "include" / "vsync" / "spinlock",
                output_dir=output_dir,
                include_path="vsync/spinlock",
            )
        except Exception as e:
            print(f"Failed to generate tilt file for {lock_name}: {e}")


def generate_locks_from_dir(
    header_dir: Path,
    output_dir: Path,
    given_locks: List[str] = (),
):
    for lock_name in given_locks:
        try:
            generate_tilt_file(
                lock_name=lock_name,
                lock_header_dir=header_dir,
                output_dir=output_dir,
                include_path=str(header_dir),
            )
        except Exception as e:
            print(f"Failed to generate tilt file for {lock_name}: {e}")


def main() -> None:
    repo_dir = Path(__file__).parent.parent.parent.parent.resolve()
    vsync_dir = (repo_dir / "deps/libvsync").resolve()
    output_dir = (repo_dir / "generatedlocks/src").resolve()

    generate_all_vsync_locks(
        vsync_dir=vsync_dir,
        output_dir=output_dir,
        given_locks=[
            "mcslock",
            "ttaslock",
            "clhlock",
        ],
    )


if __name__ == "__main__":
    main()
