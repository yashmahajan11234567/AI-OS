"""
M8-T5 — Adapter Factory.

Instantiates adapters by allowlisted class-path from capability manifests.
Enforces explicit allowlist — no wildcard importlib of arbitrary paths.
Rejects path traversal, non-allowlisted modules, and unsafe imports.
"""

from __future__ import annotations

import importlib
import logging
from typing import Any

logger = logging.getLogger(__name__)


# ---------------------------------------------------------------------------
# Adapter Factory Errors
# ---------------------------------------------------------------------------


class AdapterFactoryError(Exception):
    """AdapterFactory failure."""

    def __init__(
        self,
        message: str,
        *,
        rule_id: str | None = None,
        original_error: BaseException | None = None,
    ) -> None:
        self.rule_id = rule_id
        self.original_error = original_error
        super().__init__(message)

    def __str__(self) -> str:
        base = super().__str__()
        if self.original_error is not None:
            base += (
                f" [original_error={type(self.original_error).__name__}: "
                f"{self.original_error}]"
            )
        return base


# ---------------------------------------------------------------------------
# AdapterFactory
# ---------------------------------------------------------------------------


class AdapterFactory:
    """
    Factory for instantiating capability adapters from manifests.

    Security model:
    - Only explicitly allowlisted adapter classes can be instantiated
    - No arbitrary importlib paths (prevents os, subprocess, etc.)
    - Path traversal protection (.. in module path)
    - Constructor kwargs passed through safely
    """

    def __init__(
        self,
        adapter_allowlist: tuple[str, ...] = (),
        mcp_manager: Any | None = None,
    ) -> None:
        """
        Initialize the adapter factory.

        Args:
            adapter_allowlist: Explicitly allowlisted fully-qualified class paths
            mcp_manager: MCPManager instance to inject into adapter constructors
        """
        self._adapter_allowlist = set(adapter_allowlist)
        self._mcp_manager = mcp_manager

    @property
    def adapter_allowlist(self) -> tuple[str, ...]:
        return tuple(self._adapter_allowlist)

    def get_adapter(
        self,
        class_path: str,
        kwargs: dict[str, Any] | None = None,
        mcp_manager: Any | None = None,
    ) -> Any:
        """
        Instantiate an adapter by allowlisted class path.

        Args:
            class_path: Fully-qualified class path (e.g., "aios.adapters.graphify_adapter.GraphifyAdapter")
            kwargs: Constructor keyword arguments
            mcp_manager: Optional MCPManager override (defaults to factory's mcp_manager)

        Returns:
            Instantiated adapter instance

        Raises:
            AdapterFactoryError: If class_path not allowlisted, path traversal,
                                 module not found, class not found, or instantiation fails
        """
        # 1. Path traversal protection
        if self._has_path_traversal(class_path):
            raise AdapterFactoryError(
                f"Path traversal detected in adapter class_path: {class_path}",
                rule_id="CM-ADAPTER-001",
            )

        # 2. Validate against explicit allowlist
        if class_path not in self._adapter_allowlist:
            raise AdapterFactoryError(
                f"Adapter class not in allowlist: {class_path}",
                rule_id="CM-ADAPTER-001",
            )

        # 3. Parse module and class name
        try:
            module_path, class_name = class_path.rsplit(".", 1)
        except ValueError:
            raise AdapterFactoryError(
                f"Invalid class_path format (expected 'module.Class'): {class_path}",
                rule_id="CM-ADAPTER-001",
            )

        # 4. Import module
        try:
            module = importlib.import_module(module_path)
        except ImportError as e:
            raise AdapterFactoryError(
                f"Failed to import adapter module '{module_path}': {e}",
                rule_id="CM-ADAPTER-001",
                original_error=e,
            )

        # 5. Get class from module
        try:
            adapter_class = getattr(module, class_name)
        except AttributeError:
            raise AdapterFactoryError(
                f"Class '{class_name}' not found in module '{module_path}'",
                rule_id="CM-ADAPTER-001",
            )

        # 6. Instantiate with kwargs and mcp_manager
        kwargs = dict(kwargs or {})
        effective_mcp_manager = mcp_manager if mcp_manager is not None else self._mcp_manager

        # Only inject mcp_manager if adapter accepts it (common pattern)
        if effective_mcp_manager is not None and "mcp_manager" not in kwargs:
            # Check if constructor accepts mcp_manager parameter
            import inspect
            sig = inspect.signature(adapter_class.__init__)
            if "mcp_manager" in sig.parameters:
                kwargs["mcp_manager"] = effective_mcp_manager

        try:
            adapter_instance = adapter_class(**kwargs)
        except Exception as e:
            raise AdapterFactoryError(
                f"Failed to instantiate adapter '{class_path}': {e}",
                rule_id="CM-ADAPTER-001",
                original_error=e,
            )

        logger.debug(f"Instantiated adapter: {class_path}")
        return adapter_instance

    def _has_path_traversal(self, class_path: str) -> bool:
        """Check for path traversal attempts in class path."""
        # Check for directory traversal
        if ".." in class_path:
            return True
        # Check for absolute paths (Windows and Unix)
        if class_path.startswith("/") or class_path.startswith("\\"):
            return True
        # Check for drive letters (Windows)
        if len(class_path) >= 2 and class_path[1] == ":":
            return True
        return False


# ---------------------------------------------------------------------------
# Convenience function for kernel boot
# ---------------------------------------------------------------------------


def create_adapter_factory(
    adapter_allowlist: tuple[str, ...] = (),
    mcp_manager: Any | None = None,
) -> AdapterFactory:
    """Create an AdapterFactory with the given allowlist and MCP manager."""
    return AdapterFactory(
        adapter_allowlist=adapter_allowlist,
        mcp_manager=mcp_manager,
    )