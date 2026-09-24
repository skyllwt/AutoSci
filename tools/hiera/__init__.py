"""Optional Hiera experiment mode for AutoSci.

The package is deliberately sidecar-only: it owns ``runs/hiera`` artifacts
and never writes wiki files. Formal validation remains an explicit handoff to
the existing experiment workflow.
"""

from .contract import CONTRACT_SCHEMA_VERSION
from .semantic_space import SPACE_SCHEMA_VERSION

__all__ = ["CONTRACT_SCHEMA_VERSION", "SPACE_SCHEMA_VERSION"]
