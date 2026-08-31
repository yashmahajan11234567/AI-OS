"""
M7 Testing Compatibility Layer.

Provides the TestingService API expected by security tests,
which wraps the actual TestOrchestratorService implementation.
"""

from __future__ import annotations

from aios.services.testing import TestOrchestratorService

# Global singleton for compatibility
_global_testing_service: TestOrchestratorService | None = None


class TestingService(TestOrchestratorService):
    """
    Compatibility wrapper for TestOrchestratorService.

    The security tests expect TestingService(kernel=...).initialize()
    pattern. TestOrchestratorService has different constructor signature.
    """

    def __init__(self, kernel, **kwargs):
        # Store kernel reference for compatibility
        self._kernel_ref = kernel

        # Initialize TestOrchestratorService with required dependencies from kernel
        workflow_manager = getattr(kernel, '_workflow_manager', None)
        council_manager = getattr(kernel, '_council_manager', None)
        security_manager = getattr(kernel, '_security_manager', None)

        from aios.core.simplification_gate import SimplificationGate

        super().__init__(
            workflow_manager=workflow_manager,
            council_manager=council_manager,
            final_judge=None,
            simplification_gate=SimplificationGate(),
            security_manager=security_manager,
        )

    async def initialize(self) -> None:
        """Initialize the testing service (no-op for compatibility)."""
        # TestOrchestratorService doesn't have initialize, but we need it for tests
        pass


def get_testing_service() -> TestOrchestratorService | None:
    """Get the global testing service instance."""
    return _global_testing_service


def set_testing_service(service: TestOrchestratorService | None) -> None:
    """Set the global testing service instance."""
    global _global_testing_service
    _global_testing_service = service


__all__ = [
    "TestingService",
    "TestOrchestratorService",
    "get_testing_service",
    "set_testing_service",
]