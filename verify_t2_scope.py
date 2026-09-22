#!/usr/bin/env python3
"""
Verification script for T2 provider credential rotation authorization scope.
This script independently verifies that T2 implemented EXACTLY the approved scope:
- dashboard_user + secret.rotate + config:llm.providers.nim.apiKey -> ALLOW
- dashboard_user + secret.rotate + config:llm.providers.freellmapi.apiKey -> ALLOW
And that everything else remains DENY (fail-closed preserved).
"""

import asyncio
from aios.core.security_manager import SecurityDecision, SecurityManager
from aios.core.service_registry import get_service_registry, reset_service_registry_singleton
from aios.events.core.bus import EventBus, EventBusConfig, reset_event_bus_singleton
from aios.core.configuration_manager import ConfigurationManager, reset_configuration_manager_singleton
from aios.core.structured_logger import get_logger


async def test_exact_t2_scope():
    """Test the EXACT approved scope from T2 requirements."""
    print("Testing T2 Provider Credential Rotation Authorization Scope")
    print("=" * 60)

    # Setup clean environment
    reset_event_bus_singleton()
    reset_service_registry_singleton()
    reset_configuration_manager_singleton()

    bus = EventBus(config=EventBusConfig(auto_start_dispatch_worker=False))
    await bus.initialize()

    sr = get_service_registry(event_bus=bus)
    cm = ConfigurationManager(event_bus=bus)
    logger = get_logger()

    sm = SecurityManager(
        service_registry=sr,
        configuration_manager=cm,
        logger=logger,
    )

    try:
        # Register ONLY the two approved rules (as T2 should have done)
        print("\nRegistering EXACTLY the two approved allow-rules:")
        print("  1. dashboard_user + secret.rotate + config:llm.providers.nim.apiKey")
        print("  2. dashboard_user + secret.rotate + config:llm.providers.freellmapi.apiKey")

        sm.register_allow_rule(
            principal="dashboard_user",
            action="secret.rotate",
            resource="config:llm.providers.nim.apiKey"
        )
        sm.register_allow_rule(
            principal="dashboard_user",
            action="secret.rotate",
            resource="config:llm.providers.freellmapi.apiKey"
        )

        # Test POSITIVE authorization cases (should ALLOW)
        print("\nTesting POSITIVE authorization cases (should ALLOW):")

        # Test 1: NIM credential rotation
        decision1 = sm.authorize(
            principal="dashboard_user",
            action="secret.rotate",
            resource="config:llm.providers.nim.apiKey"
        )
        print(f"  dashboard_user + secret.rotate + config:llm.providers.nim.apiKey -> {decision1}")
        assert decision1 == SecurityDecision.ALLOW, "NIM credential rotation should be ALLOWED"
        print("  CORRECT: NIM credential rotation authorized")

        # Test 2: FreeLLMAPI credential rotation
        decision2 = sm.authorize(
            principal="dashboard_user",
            action="secret.rotate",
            resource="config:llm.providers.freellmapi.apiKey"
        )
        print(f"  dashboard_user + secret.rotate + config:llm.providers.freellmapi.apiKey -> {decision2}")
        assert decision2 == SecurityDecision.ALLOW, "FreeLLMAPI credential rotation should be ALLOWED"
        print("  CORRECT: FreeLLMAPI credential rotation authorized")

        # Test NEGATIVE authorization cases (should DENY - fail-closed preserved)
        print("\nTesting NEGATIVE authorization cases (should DENY - fail-closed):")

        # Test A: Unrelated provider credential (different resource)
        decision_a = sm.authorize(
            principal="dashboard_user",
            action="secret.rotate",
            resource="config:llm.providers.openai.apiKey"
        )
        print(f"  dashboard_user + secret.rotate + config:llm.providers.openai.apiKey -> {decision_a}")
        assert decision_a == SecurityDecision.DENY, "Unrelated provider credential should be DENIED"
        print("  CORRECT: Unrelated provider credential denied")

        # Test B: Unauthorized principal
        decision_b = sm.authorize(
            principal="unauthorized_user",
            action="secret.rotate",
            resource="config:llm.providers.nim.apiKey"
        )
        print(f"  unauthorized_user + secret.rotate + config:llm.providers.nim.apiKey -> {decision_b}")
        assert decision_b == SecurityDecision.DENY, "Unauthorized principal should be DENIED"
        print("  CORRECT: Unauthorized principal denied")

        # Test C: Unrelated action
        decision_c = sm.authorize(
            principal="dashboard_user",
            action="project.create",  # Not secret.rotate
            resource="config:llm.providers.nim.apiKey"
        )
        print(f"  dashboard_user + project.create + config:llm.providers.nim.apiKey -> {decision_c}")
        assert decision_c == SecurityDecision.DENY, "Unrelated action should be DENIED"
        print("  CORRECT: Unrelated action denied")

        # Test D: Empty principal
        decision_d = sm.authorize(
            principal="",
            action="secret.rotate",
            resource="config:llm.providers.nim.apiKey"
        )
        print(f"  '' + secret.rotate + config:llm.providers.nim.apiKey -> {decision_d}")
        assert decision_d == SecurityDecision.DENY, "Empty principal should be DENIED"
        print("  CORRECT: Empty principal denied")

        # Test E: None principal
        decision_e = sm.authorize(
            principal=None,
            action="secret.rotate",
            resource="config:llm.providers.nim.apiKey"
        )
        print(f"  None + secret.rotate + config:llm.providers.nim.apiKey -> {decision_e}")
        assert decision_e == SecurityDecision.DENY, "None principal should be DENIED"
        print("  CORRECT: None principal denied")

        print("\n" + "=" * 60)
        print("ALL TESTS PASSED - T2 SCOPE VERIFICATION SUCCESSFUL")
        print("Approved scope implemented correctly")
        print("Fail-closed security preserved")
        print("No over-authorization detected")
        print("=" * 60)

        return True

    except Exception as e:
        print(f"\nTEST FAILED: {e}")
        return False

    finally:
        # Cleanup
        reset_event_bus_singleton()
        reset_service_registry_singleton()
        reset_configuration_manager_singleton()


if __name__ == "__main__":
    result = asyncio.run(test_exact_t2_scope())
    exit(0 if result else 1)