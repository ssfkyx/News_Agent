# =============================================================================
# Module: tools.sitecustomize
# Responsibilities: DSH sandbox compatibility shim for CPython mkdir DACL (pip install helper).
# Dependencies: os, site
# Dependents: pip/venv bootstrap
# ADRs: ADR-0014
# Traceability: docs/decisions/README.md
# =============================================================================
"""DSH sandbox compatibility shim.

CPython on this machine applies a restrictive DACL when a directory is created
with mode 0o700, which makes directories produced by ``tempfile.mkdtemp()``
unwritable for the sandboxed process that just created them (pip, ensurepip,
build backends all break with ``PermissionError: [Errno 13]``).

Windows ignores POSIX modes for ``mkdir`` in stock CPython, so forcing 0o777
here only restores the normal Windows behavior. Activate by putting this
directory on PYTHONPATH.
"""

import os

_orig_mkdir = os.mkdir


def mkdir(path, mode=0o777, *, dir_fd=None):
    """Create a directory while ignoring POSIX mode restrictions.

    Preconditions:
        path is an absolute or relative filesystem path; the process may create it.
    Postconditions:
        The directory exists with the host's default Windows ACL (mode forced to 0o777).
    Prohibitions:
        Do not use this as a general-purpose chmod replacement; it exists only for pip/ensurepip.
    Raises:
        OSError from the underlying os.mkdir (permission, missing parent, existing file).
    """
    return _orig_mkdir(path, 0o777, dir_fd=dir_fd)


os.mkdir = mkdir
