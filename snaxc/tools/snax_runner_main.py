"""Console-script entry point for the golden-vs-device verification harness.

Implementation lives in :mod:`snaxc.golden.verify`; this module exists so the
runner is exposed via ``[project.scripts]`` (``snax-runner``) alongside
``phsc`` and ``snax-opt``.
"""

from snaxc.golden.verify import main

__all__ = ["main"]
