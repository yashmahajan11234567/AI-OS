"""
AI-OS CLI Commands Package.

Central registration of all CLI command modules.
"""

# Import all command modules to register them
from aios.cli.commands import doctor  # noqa: F401
from aios.cli.commands import onboard  # noqa: F401
from aios.cli.commands import kernel  # noqa: F401
from aios.cli.commands import status  # noqa: F401
from aios.cli.commands import health  # noqa: F401
from aios.cli.commands import ready  # noqa: F401
from aios.cli.commands import diagnostics  # noqa: F401

__all__ = [
    "doctor",
    "onboard",
    "kernel",
    "status",
    "health",
    "ready",
    "diagnostics",
]