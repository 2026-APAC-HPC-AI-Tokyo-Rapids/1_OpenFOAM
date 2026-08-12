#!/usr/bin/env python3
"""Allow a sibling VTune collector to attach, then exec the target."""

import ctypes
import os
import sys

PR_SET_PTRACER = 0x59616D61
PR_SET_PTRACER_ANY = ctypes.c_ulong(-1).value


def main() -> None:
    if len(sys.argv) < 2:
        raise SystemExit("usage: allow-vtune-attach.py TARGET [ARG ...]")

    libc = ctypes.CDLL(None, use_errno=True)
    libc.prctl.argtypes = [
        ctypes.c_int,
        ctypes.c_ulong,
        ctypes.c_ulong,
        ctypes.c_ulong,
        ctypes.c_ulong,
    ]
    libc.prctl.restype = ctypes.c_int
    if libc.prctl(PR_SET_PTRACER, PR_SET_PTRACER_ANY, 0, 0, 0) != 0:
        error = ctypes.get_errno()
        raise OSError(error, os.strerror(error))

    os.execv(sys.argv[1], sys.argv[1:])


if __name__ == "__main__":
    main()
