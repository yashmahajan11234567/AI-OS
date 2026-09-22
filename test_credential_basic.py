#!/usr/bin/env python3
"""
Basic test to verify credential rotation components work.
"""

import asyncio
import os

# Set up environment for testing - use correct length for AES key
os.environ["AIOS_CREDENTIAL_STORE_KEY"] = "0123456789abcdef0123456789abcdef"  # 32 bytes for AES-256


def test_imports():
    """Test that we can import the key modules."""
    print("Testing imports...")

    try:
        from aios.core.configuration_manager import get_configuration_manager, reset_configuration_manager_singleton
        from aios.core.provider_registry import get_provider_registry, reset_provider_registry_singleton
        from aios.core.provider import Provider
        from aios.events.core.bus import EventBus, EventBusConfig, reset_event_bus_singleton
        print("✓ All imports successful")
        return True
    except Exception as e:
        print(f"❌ Import failed: {e}")
        return False


def test_provider_abc():
    """Test that Provider ABC has the required methods."""
    print("\nTesting Provider ABC...")

    try:
        from aios.core.provider import Provider

        # Check that Provider has configure and reload_credentials methods
        assert hasattr(Provider, 'configure')
        assert hasattr(Provider, 'reload_credentials')

        # Check that they have proper docstrings
        assert Provider.configure.__doc__ is not None
        assert Provider.reload_credentials.__doc__ is not None

        print("✓ Provider ABC has configure and reload_credentials methods")
        print("✓ Methods have documentation")
        return True
    except Exception as e:
        print(f"❌ Provider ABC test failed: {e}")
        return False


def test_nim_provider_methods():
    """Test that NimProvider implements the required methods."""
    print("\nTesting NimProvider methods...")

    try:
        from aios.adapters.nim import NimProvider, NimConfig

        # Create provider instance
        provider = NimProvider(NimConfig())

        # Check that it has the required methods
        assert hasattr(provider, 'configure')
        assert hasattr(provider, 'reload_credentials')
        assert callable(provider.configure)
        assert callable(provider.reload_credentials)

        # Check that reload_credentials is async
        import inspect
        assert inspect.iscoroutinefunction(provider.reload_credentials)

        print("✓ NimProvider has configure and reload_credentials methods")
        print("✓ reload_credentials is properly async")
        return True
    except Exception as e:
        print(f"❌ NimProvider test failed: {e}")
        return False


def test_freellmapi_provider_methods():
    """Test that FreeLLMAPIProvider implements the required methods."""
    print("\nTesting FreeLLMAPIProvider methods...")

    try:
        from aios.adapters.freellmapi import FreeLLMAPIProvider, FreeLLMAPIConfig

        # Create provider instance
        provider = FreeLLMAPIProvider(FreeLLMAPIConfig())

        # Check that it has the required methods
        assert hasattr(provider, 'configure')
        assert hasattr(provider, 'reload_credentials')
        assert callable(provider.configure)
        assert callable(provider.reload_credentials)

        # Check that reload_credentials is async
        import inspect
        assert inspect.iscoroutinefunction(provider.reload_credentials)

        print("✓ FreeLLMAPIProvider has configure and reload_credentials methods")
        print("✓ reload_credentials is properly async")
        return True
    except Exception as e:
        print(f"❌ FreeLLMAPIProvider test failed: {e}")
        return False


def test_provider_registry_methods():
    """Test that ProviderRegistry has the reload method."""
    print("\nTesting ProviderRegistry methods...")

    try:
        from aios.core.provider_registry import ProviderRegistry

        # Create registry instance
        registry = ProviderRegistry()

        # Check that it has the reload method
        assert hasattr(registry, 'reload_provider_credentials')
        assert callable(registry.reload_provider_credentials)

        print("✓ ProviderRegistry has reload_provider_credentials method")
        return True
    except Exception as e:
        print(f"❌ ProviderRegistry test failed: {e}")
        return False


def test_configuration_manager_rotation():
    """Test that ConfigurationManager has rotation and notification methods."""
    print("\nTesting ConfigurationManager rotation methods...")

    try:
        from aios.core.configuration_manager import ConfigurationManager

        # Check that it has the required methods
        assert hasattr(ConfigurationManager, 'rotate_secret')
        assert hasattr(ConfigurationManager, '_notify_provider_credential_rotation')
        assert callable(ConfigurationManager.rotate_secret)
        assert callable(ConfigurationManager._notify_provider_credential_rotation)

        print("✓ ConfigurationManager has rotate_secret and _notify_provider_credential_rotation methods")
        return True
    except Exception as e:
        print(f"❌ ConfigurationManager test failed: {e}")
        return False


def test_secret_path_detection():
    """Test that secret path detection works for provider credentials."""
    print("\nTesting secret path detection...")

    try:
        from aios.core.configuration_manager import is_secret_path

        # Test provider credential paths
        nim_path = ["llm", "providers", "nim", "apiKey"]
        freellmapi_path = ["llm", "providers", "freellmapi", "apiKey"]

        assert is_secret_path(nim_path) == True
        assert is_secret_path(freellmapi_path) == True

        # Test non-secret paths
        non_secret_path = ["llm", "providers", "nim", "base_url"]
        assert is_secret_path(non_secret_path) == False

        print("✓ Secret path detection works correctly for provider credentials")
        return True
    except Exception as e:
        print(f"❌ Secret path detection test failed: {e}")
        return False


def run_all_tests():
    """Run all tests and report results."""
    print("=" * 60)
    print("BASIC CREDENTIAL ROTATION COMPONENT TESTS")
    print("=" * 60)

    tests = [
        test_imports,
        test_provider_abc,
        test_nim_provider_methods,
        test_freellmapi_provider_methods,
        test_provider_registry_methods,
        test_configuration_manager_rotation,
        test_secret_path_detection
    ]

    passed = 0
    total = len(tests)

    for test in tests:
        if test():
            passed += 1

    print("\n" + "=" * 60)
    print(f"RESULTS: {passed}/{total} tests passed")

    if passed == total:
        print("✓ ALL BASIC TESTS PASSED")
        print("✓ Provider ABC has required methods")
        print("✓ NIM and FreeLLMAPI providers implement required methods")
        print("✓ ProviderRegistry has notification method")
        print("✓ ConfigurationManager has rotation methods")
        print("✓ Secret path detection works correctly")
        return True
    else:
        print("❌ SOME TESTS FAILED")
        return False


if __name__ == "__main__":
    success = run_all_tests()
    exit(0 if success else 1)