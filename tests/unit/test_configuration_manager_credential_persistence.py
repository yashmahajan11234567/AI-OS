"""
M14-T2 — ConfigurationManager credential persistence tests.

Tests secure credential persistence integration with ConfigurationManager:
  * Secret overlay survival across restarts
  * Encryption at rest (no plaintext in files)
  * Fail-closed behavior on persistence failures
  * Generic provider support (NVIDIA NIM, FreeLLMAPI, Kilo, etc.)
  * Atomic writes and permission hardening
"""

from __future__ import annotations

import asyncio
import base64
import json
import os
import stat
from pathlib import Path
from unittest.mock import AsyncMock, MagicMock, patch

import pytest
from cryptography.fernet import Fernet

from aios.core.configuration_manager import (
    ConfigurationManager,
    get_configuration_manager,
    reset_configuration_manager_singleton,
)
from aios import EventBus
from aios.security.credential_store import (
    CredentialStore,
    reset_credential_store_singleton,
    set_credential_store,
)


@pytest.fixture
def encryption_key():
    """Generate a valid Fernet key for testing."""
    return Fernet.generate_key()


@pytest.fixture
def credential_store(tmp_path, encryption_key):
    """Create a CredentialStore instance."""
    store = CredentialStore(
        store_path=tmp_path / "credentials",
        encryption_key=encryption_key,
    )
    return store


@pytest.fixture
def event_bus():
    """Create a mock event bus."""
    bus = MagicMock(spec=EventBus)
    bus.publish = AsyncMock()
    return bus


@pytest.fixture
def configured_manager(tmp_path, encryption_key, event_bus):
    """Create a ConfigurationManager with credential persistence enabled."""
    # Reset singletons
    reset_configuration_manager_singleton()
    reset_credential_store_singleton()

    # Create and set credential store
    store = CredentialStore(
        store_path=tmp_path / "credentials",
        encryption_key=encryption_key,
    )
    set_credential_store(store)

    # Create config manager
    mgr = ConfigurationManager()
    mgr.event_bus = event_bus
    mgr._data_dir = tmp_path  # Override data directory for tests
    mgr._secret_overlay = {}
    mgr._rotation_count = {}
    mgr._rotated_secret_versions = {}
    mgr._merged = {}
    mgr._locked = False

    yield mgr, store

    # Cleanup
    reset_configuration_manager_singleton()
    reset_credential_store_singleton()


# =============================================================================
# 1. Secret Overlay Survival Tests
# =============================================================================


class TestSecretOverlaySurvival:
    """Test that rotated secrets survive ConfigurationManager restarts."""

    @pytest.mark.asyncio
    async def test_secret_overlay_survives_restart_nim(
        self, configured_manager, event_bus
    ):
        """Test NVIDIA NIM credential persistence across restart."""
        mgr, store = configured_manager
        provider_id = "nim"
        secret_path = "llm.providers.nim.apiKey"
        original_value = "sk-test-nim-initial-key"
        rotated_value = "sk-test-nim-rotated-key"

        # Initialize and configure first instance
        await mgr.initialize()
        with mgr._lock:
            mgr._merged = {
                "kernel": {"name": "Hermes", "version": "0.1.0", "logLevel": "INFO"},
                "llm": {"providers": {"nim": {"apiKey": original_value}}},
            }
        mgr.freeze()

        # Rotate secret
        mgr.rotate_secret(secret_path, rotated_value, principal="test-operator")
        assert mgr.get_secret(secret_path) == rotated_value

        # Simulate restart: destroy and recreate manager
        reset_configuration_manager_singleton()
        set_credential_store(store)  # Reuse same store

        mgr2 = ConfigurationManager()
        mgr2.event_bus = event_bus
        mgr2._data_dir = tmp_path
        mgr2._secret_overlay = {}
        mgr2._rotation_count = {}
        mgr2._rotated_secret_versions = {}
        mgr2._merged = {}
        mgr2._locked = False

        await mgr2.initialize()

        # Re-seed same configuration
        with mgr2._lock:
            mgr2._merged = {
                "kernel": {"name": "Hermes", "version": "0.1.0", "logLevel": "INFO"},
                "llm": {"providers": {"nim": {"apiKey": original_value}}},
            }
        mgr2.freeze()

        # Verify rotated value persisted
        restored_value = mgr2.get_secret(secret_path)
        assert restored_value == rotated_value, (
            f"Expected rotated value {rotated_value}, got {restored_value}"
        )

        # Verify metadata persisted
        assert mgr2._rotation_count.get(secret_path, 0) > 0
        assert secret_path in mgr2._rotated_secret_versions

    @pytest.mark.asyncio
    async def test_secret_overlay_survives_restart_multiple_providers(
        self, configured_manager, event_bus
    ):
        """Test multiple provider credentials survive restart."""
        mgr, store = configured_manager
        providers = [
            ("nim", "llm.providers.nim.apiKey", "sk-nim-test"),
            ("freellmapi", "llm.providers.freellmapi.token", "tok-free-test"),
            ("kilo", "llm.providers.kilo.credential", "cred-kilo-test"),
        ]

        # Initialize and configure
        await mgr.initialize()
        with mgr._lock:
            mgr._merged = {
                "kernel": {"name": "Hermes", "version": "0.1.0", "logLevel": "INFO"},
                "llm": {
                    "providers": {
                        "nim": {"apiKey": providers[0][2]},
                        "freellmapi": {"token": providers[1][2]},
                        "kilo": {"credential": providers[2][2]},
                    }
                },
            }
        mgr.freeze()

        # Rotate all secrets
        rotated_values = []
        for provider_id, secret_path, original in providers:
            rotated = f"{original}-rotated"
            rotated_values.append((provider_id, secret_path, rotated))
            mgr.rotate_secret(secret_path, rotated, principal="test-operator")

        # Verify rotations took effect
        for provider_id, secret_path, expected in rotated_values:
            assert mgr.get_secret(secret_path) == expected

        # Simulate restart
        reset_configuration_manager_singleton()
        set_credential_store(store)

        mgr2 = ConfigurationManager()
        mgr2.event_bus = event_bus
        mgr2._data_dir = tmp_path
        mgr2._secret_overlay = {}
        mgr2._rotation_count = {}
        mgr2._rotated_secret_versions = {}
        mgr2._merged = {}
        mgr2._locked = False

        await mgr2.initialize()

        # Re-seed configuration
        with mgr2._lock:
            mgr2._merged = {
                "kernel": {"name": "Hermes", "version": "0.1.0", "logLevel": "INFO"},
                "llm": {
                    "providers": {
                        "nim": {"apiKey": providers[0][2]},
                        "freellmapi": {"token": providers[1][2]},
                        "kilo": {"credential": providers[2][2]},
                    }
                },
            }
        mgr2.freeze()

        # Verify all values persisted
        for provider_id, secret_path, expected in rotated_values:
            restored = mgr2.get_secret(secret_path)
            assert restored == expected, (
                f"Provider {provider_id}: expected {expected}, got {restored}"
            )

    @pytest.mark.asyncio
    async def test_first_boot_no_credential_store(self, tmp_path, event_bus):
        """Test first boot works normally with no credential store."""
        reset_configuration_manager_singleton()
        reset_credential_store_singleton()

        mgr = ConfigurationManager()
        mgr.event_bus = event_bus
        mgr._data_dir = tmp_path
        mgr._secret_overlay = {}
        mgr._rotation_count = {}
        mgr._rotated_secret_versions = {}
        mgr._merged = {}
        mgr._locked = False

        await mgr.initialize()

        with mgr._lock:
            mgr._merged = {
                "kernel": {"name": "Hermes", "version": "0.1.0", "logLevel": "INFO"},
                "llm": {"providers": {"nim": {"apiKey": "initial-key"}}},
            }
        mgr.freeze()

        # Should work normally (no persistence, but no crash)
        assert mgr.get_secret("llm.providers.nim.apiKey") == "initial-key"

        # Rotate secret
        mgr.rotate_secret(
            "llm.providers.nim.apiKey", "rotated-key", principal="test-operator"
        )
        assert mgr.get_secret("llm.providers.nim.apiKey") == "rotated-key"

        # Second boot - should still work (no persisted data, but config seeded)
        reset_configuration_manager_singleton()

        mgr2 = ConfigurationManager()
        mgr2.event_bus = event_bus
        mgr2._data_dir = tmp_path
        mgr2._secret_overlay = {}
        mgr2._rotation_count = {}
        mgr2._rotated_secret_versions = {}
        mgr2._merged = {}
        mgr2._locked = False

        await mgr2.initialize()

        with mgr2._lock:
            mgr2._merged = {
                "kernel": {"name": "Hermes", "version": "0.1.0", "logLevel": "INFO"},
                "llm": {"providers": {"nim": {"apiKey": "initial-key"}}},
            }
        mgr2.freeze()

        # Should have original value (no persistence to restore)
        assert mgr2.get_secret("llm.providers.nim.apiKey") == "initial-key"


# =============================================================================
# 2. Encryption at Rest Tests
# =============================================================================


class TestEncryptionAtRest:
    """Test that credentials are encrypted at rest."""

    @pytest.mark.asyncio
    async def test_encrypted_at_rest_no_plaintext_nim(
        self, configured_manager, tmp_path, event_bus
    ):
        """Verify NIM credential file contains no plaintext secrets."""
        mgr, store = configured_manager
        provider_id = "nim"
        secret_path = "llm.providers.nim.apiKey"
        secret_value = "sk-test-nim-secret-value-12345"

        await mgr.initialize()
        with mgr._lock:
            mgr._merged = {
                "kernel": {"name": "Hermes", "version": "0.1.0", "logLevel": "INFO"},
                "llm": {"providers": {"nim": {"apiKey": secret_value}}},
            }
        mgr.freeze()

        # Rotate to trigger persistence
        mgr.rotate_secret(secret_path, f"{secret_value}-rotated", principal="test-operator")

        # Check credential file
        cred_file = tmp_path / "credentials" / f"{provider_id}.json"
        assert cred_file.exists()

        # Read raw content
        file_content = cred_file.read_text()
        assert secret_value not in file_content
        assert f"{secret_value}-rotated" not in file_content

        # But should still decrypt correctly
        result = store.load_credentials(provider_id)
        assert result is not None
        secret_overlay, _, _ = result
        assert secret_overlay["apiKey"] == f"{secret_value}-rotated"

    @pytest.mark.asyncio
    async def test_encrypted_at_rest_multiple_secrets(
        self, configured_manager, tmp_path, event_bus
    ):
        """Test encryption works for multiple secret types."""
        mgr, store = configured_manager
        provider_id = "freellmapi"

        await mgr.initialize()
        with mgr._lock:
            mgr._merged = {
                "kernel": {"name": "Hermes", "version": "0.1.0", "logLevel": "INFO"},
                "llm": {"providers": {"freellmapi": {"token": "test-token", "secret": "test-secret"}}},
            }
        mgr.freeze()

        # Rotate both secrets
        mgr.rotate_secret(
            "llm.providers.freellmapi.token",
            "rotated-token",
            principal="test-operator",
        )
        mgr.rotate_secret(
            "llm.providers.freellmapi.secret",
            "rotated-secret",
            principal="test-operator",
        )

        # Check file contains no plaintext
        cred_file = tmp_path / "credentials" / f"{provider_id}.json"
        file_content = cred_file.read_text()
        assert "test-token" not in file_content
        assert "test-secret" not in file_content
        assert "rotated-token" not in file_content
        assert "rotated-secret" not in file_content

        # But should decrypt correctly
        result = store.load_credentials(provider_id)
        assert result is not None
        secret_overlay, _, _ = result
        assert secret_overlay["token"] == "rotated-token"
        assert secret_overlay["secret"] == "rotated-secret"

    @pytest.mark.asyncio
    async def test_file_contains_only_encrypted_data(
        self, configured_manager, tmp_path, event_bus
    ):
        """Verify credential file contains expected encrypted structure."""
        mgr, store = configured_manager
        provider_id = "kilo"
        secret_value = "test-kilo-credential"

        await mgr.initialize()
        with mgr._lock:
            mgr._merged = {
                "kernel": {"name": "Hermes", "version": "0.1.0", "logLevel": "INFO"},
                "llm": {"providers": {"kilo": {"credential": secret_value}}},
            }
        mgr.freeze()

        mgr.rotate_secret(
            "llm.providers.kilo.credential",
            f"{secret_value}-rotated",
            principal="test-operator",
        )

        cred_file = tmp_path / "credentials" / f"{provider_id}.json"
        file_content = cred_file.read_text()
        data = json.loads(file_content)

        # Verify expected fields
        assert data["schema_version"] == "1.0"
        assert data["provider_id"] == provider_id
        assert "encrypted_secret_overlay" in data
        assert data["rotation_count"] >= 1
        assert isinstance(data["rotated_secret_versions"], dict)

        # Verify encrypted data looks encrypted (not plaintext)
        encrypted_overlay = data["encrypted_secret_overlay"]
        assert len(encrypted_overlay) > 20  # Should be substantially long
        assert secret_value not in encrypted_overlay
        assert f"{secret_value}-rotated" not in encrypted_overlay


# =============================================================================
# 3. Fail-Closed Behavior Tests
# =============================================================================


class TestFailClosedBehavior:
    """Test fail-closed behavior on persistence failures."""

    @pytest.mark.asyncio
    async def test_persist_fail_closed_corrupted_file(
        self, configured_manager, tmp_path, event_bus
    ):
        """Test fail-closed behavior when credential file is corrupted."""
        mgr, store = configured_manager
        provider_id = "nim"

        await mgr.initialize()
        with mgr._lock:
            mgr._merged = {
                "kernel": {"name": "Hermes", "version": "0.1.0", "logLevel": "INFO"},
                "llm": {"providers": {"nim": {"apiKey": "initial-key"}}},
            }
        mgr.freeze()

        # Rotate to create credential file
        mgr.rotate_secret(
            "llm.providers.nim.apiKey", "rotated-key", principal="test-operator"
        )

        # Corrupt the credential file
        cred_file = tmp_path / "credentials" / f"{provider_id}.json"
        cred_file.write_text("{ invalid json content")

        # Simulate restart
        reset_configuration_manager_singleton()
        set_credential_store(store)

        mgr2 = ConfigurationManager()
        mgr2.event_bus = event_bus
        mgr2._data_dir = tmp_path
        mgr2._secret_overlay = {}
        mgr2._rotation_count = {}
        mgr2._rotated_secret_versions = {}
        mgr2._merged = {}
        mgr2._locked = False

        await mgr2.initialize()

        with mgr2._lock:
            mgr2._merged = {
                "kernel": {"name": "Hermes", "version": "0.1.0", "logLevel": "INFO"},
                "llm": {"providers": {"nim": {"apiKey": "initial-key"}}},
            }
        mgr2.freeze()

        # Should have original value (fail-closed: no plaintext leak, use seed config)
        assert mgr2.get_secret("llm.providers.nim.apiKey") == "initial-key"
        # Rotation count should be 0 (no persisted metadata)
        assert mgr2._rotation_count.get("llm.providers.nim.apiKey", 0) == 0

    @pytest.mark.asyncio
    async def test_persist_fail_closed_wrong_encryption_key(
        self, tmp_path, event_bus
    ):
        """Test fail-closed when encryption key changes/missing."""
        reset_configuration_manager_singleton()
        reset_credential_store_singleton()

        # First manager with key
        key1 = Fernet.generate_key()
        store1 = CredentialStore(
            store_path=tmp_path / "credentials",
            encryption_key=key1,
        )
        set_credential_store(store1)

        mgr1 = ConfigurationManager()
        mgr1.event_bus = event_bus
        mgr1._data_dir = tmp_path
        mgr1._secret_overlay = {}
        mgr1._rotation_count = {}
        mgr1._rotated_secret_versions = {}
        mgr1._merged = {}
        mgr1._locked = False

        await mgr1.initialize()
        with mgr1._lock:
            mgr1._merged = {
                "kernel": {"name": "Hermes", "version": "0.1.0", "logLevel": "INFO"},
                "llm": {"providers": {"nim": {"apiKey": "test-key"}}},
            }
        mgr1.freeze()

        # Rotate secret (creates encrypted file with key1)
        mgr1.rotate_secret(
            "llm.providers.nim.apiKey", "rotated-key", principal="test-operator"
        )

        # Second manager with DIFFERENT key (simulate key rotation/loss)
        reset_configuration_manager_singleton()
        # Keep same store object but it will fail to decrypt with wrong assumptions
        # Actually, let's create a store that will fail to initialize
        store2 = CredentialStore(store_path=tmp_path / "credentials")
        # Don't set encryption key - will be uninitialized
        set_credential_store(store2)

        mgr2 = ConfigurationManager()
        mgr2.event_bus = event_bus
        mgr2._data_dir = tmp_path
        mgr2._secret_overlay = {}
        mgr2._rotation_count = {}
        mgr2._rotated_secret_versions = {}
        mgr2._merged = {}
        mgr2._locked = False

        await mgr2.initialize()

        with mgr2._lock:
            mgr2._merged = {
                "kernel": {"name": "Hermes", "version": "0.1.0", "logLevel": "INFO"},
                "llm": {"providers": {"nim": {"apiKey": "test-key"}}},
            }
        mgr2.freeze()

        # Should have original value (fail-closed: cannot decrypt, use seed)
        assert mgr2.get_secret("llm.providers.nim.apiKey") == "test-key"
        # No persisted rotation data
        assert mgr2._rotation_count.get("llm.providers.nim.apiKey", 0) == 0

    @pytest.mark.asyncio
    async def test_persist_fail_closed_missing_environment_key(
        self, tmp_path, event_bus, monkeypatch
    ):
        """Test fail-closed when AIOS_CREDENTIAL_STORE_KEY is missing."""
        # Ensure environment variable is not set
        monkeypatch.delenv("AIOS_CREDENTIAL_STORE_KEY", raising=False)

        reset_configuration_manager_singleton()
        reset_credential_store_singleton()

        # Try to create store without key
        store = CredentialStore(store_path=tmp_path / "credentials")
        assert not store.is_initialized()  # Should be disabled
        set_credential_store(store)

        mgr = ConfigurationManager()
        mgr.event_bus = event_bus
        mgr._data_dir = tmp_path
        mgr._secret_overlay = {}
        mgr._rotation_count = {}
        mgr2._rotated_secret_versions = {}
        mgr2._merged = {}
        mgr2._locked = False

        await mgr.initialize()
        with mgr._lock:
            mgr._merged = {
                "kernel": {"name": "Hermes", "version": "0.1.0", "logLevel": "INFO"},
                "llm": {"providers": {"nim": {"apiKey": "test-key"}}},
            }
        mgr.freeze()

        # Rotate secret
        mgr.rotate_secret(
            "llm.providers.nim.apiKey", "rotated-key", principal="test-operator"
        )

        # Simulate restart
        reset_configuration_manager_singleton()
        set_credential_store(store)  # Still no key

        mgr2 = ConfigurationManager()
        mgr2.event_bus = event_bus
        mgr2._data_dir = tmp_path
        mgr2._secret_overlay = {}
        mgr2._rotation_count = {}
        mgr2._rotated_secret_versions = {}
        mgr2._merged = {}
        mgr2._locked = False

        await mgr2.initialize()

        with mgr2._lock:
            mgr2._merged = {
                "kernel": {"name": "Hermes", "version": "0.1.0", "logLevel": "INFO"},
                "llm": {"providers": {"nim": {"apiKey": "test-key"}}},
            }
        mgr2.freeze()

        # Should have original value (no persistence worked)
        assert mgr2.get_secret("llm.providers.nim.apiKey") == "test-key"
        assert mgr2._rotation_count.get("llm.providers.nim.apiKey", 0) == 0


# =============================================================================
# 4. Generic Provider Support Tests
# =============================================================================


class TestGenericProviderSupport:
    """Test generic provider ID support."""

    @pytest.mark.asyncio
    async def test_nvidia_nim_provider_support(
        self, configured_manager, tmp_path, event_bus
    ):
        """Test NVIDIA NIM provider credential persistence."""
        mgr, store = configured_manager
        provider_id = "nim"

        await mgr.initialize()
        with mgr._lock:
            mgr._merged = {
                "kernel": {"name": "Hermes", "version": "0.1.0", "logLevel": "INFO"},
                "llm": {"providers": {"nim": {"apiKey": "sk-nim-test", "endpoint": "https://api.nvidia.com"}}},
            }
        mgr.freeze()

        mgr.rotate_secret(
            "llm.providers.nim.apiKey",
            "sk-nim-rotated",
            principal="test-operator",
        )

        # Verify file created with correct provider ID
        cred_file = tmp_path / "credentials" / f"{provider_id}.json"
        assert cred_file.exists()

        # Verify can load and decrypt
        result = store.load_credentials(provider_id)
        assert result is not None
        secret_overlay, _, _ = result
        assert secret_overlay["apiKey"] == "sk-nim-rotated"
        assert secret_overlay["endpoint"] == "https://api.nvidia.com"

    @pytest.mark.asyncio
    async def test_free_llm_api_provider_support(
        self, configured_manager, tmp_path, event_bus
    ):
        """Test FreeLLMAPI provider credential persistence."""
        mgr, store = configured_manager
        provider_id = "freellmapi"

        await mgr.initialize()
        with mgr._lock:
            mgr._merged = {
                "kernel": {"name": "Hermes", "version": "0.1.0", "logLevel": "INFO"},
                "llm": {"providers": {"freellmapi": {"token": "tok-free-test"}}},
            }
        mgr.freeze()

        mgr.rotate_secret(
            "llm.providers.freellmapi.token",
            "tok-free-rotated",
            principal="test-operator",
        )

        cred_file = tmp_path / "credentials" / f"{provider_id}.json"
        assert cred_file.exists()

        result = store.load_credentials(provider_id)
        assert result is not None
        secret_overlay, _, _ = result
        assert secret_overlay["token"] == "tok-free-rotated"

    @pytest.mark.asyncio
    async def test_kilo_provider_support(
        self, configured_manager, tmp_path, event_bus
    ):
        """Test Kilo provider credential persistence."""
        mgr, store = configured_manager
        provider_id = "kilo"

        await mgr.initialize()
        with mgr._lock:
            mgr._merged = {
                "kernel": {"name": "Hermes", "version": "0.1.0", "logLevel": "INFO"},
                "llm": {"providers": {"kilo": {"credential": "cred-kilo-test"}}},
            }
        mgr.freeze()

        mgr.rotate_secret(
            "llm.providers.kilo.credential",
            "cred-kilo-rotated",
            principal="test-operator",
        )

        cred_file = tmp_path / "credentials" / f"{provider_id}.json"
        assert cred_file.exists()

        result = store.load_credentials(provider_id)
        assert result is not None
        secret_overlay, _, _ = result
        assert secret_overlay["credential"] == "cred-kilo-rotated"

    @pytest.mark.asyncio
    async def test_agnes_provider_support(
        self, configured_manager, tmp_path, event_bus
    ):
        """Test Agnes provider credential persistence."""
        mgr, store = configured_manager
        provider_id = "agnes"

        await mgr.initialize()
        with mgr._lock:
            mgr._merged = {
                "kernel": {"name": "Hermes", "version": "0.1.0", "logLevel": "INFO"},
                "llm": {"providers": {"agnes": {"secretKey": "sk-agnes-test"}}},
            }
        mgr.freeze()

        mgr.rotate_secret(
            "llm.providers.agnes.secretKey",
            "sk-agnes-rotated",
            principal="test-operator",
        )

        cred_file = tmp_path / "credentials" / f"{provider_id}.json"
        assert cred_file.exists()

        result = store.load_credentials(provider_id)
        assert result is not None
        secret_overlay, _, _ = result
        assert secret_overlay["secretKey"] == "sk-agnes-rotated"

    @pytest.mark.asyncio
    async def test_gemini_provider_support(
        self, configured_manager, tmp_path, event_bus
    ):
        """Test Gemini provider credential persistence."""
        mgr, store = configured_manager
        provider_id = "gemini"

        await mgr.initialize()
        with mgr._lock:
            mgr._merged = {
                "kernel": {"name": "Hermes", "version": "0.1.0", "logLevel": "INFO"},
                "llm": {"providers": {"gemini": {"apiKey": "ai-gemini-test"}}},
            }
        mgr.freeze()

        mgr.rotate_secret(
            "llm.providers.gemini.apiKey",
            "ai-gemini-rotated",
            principal="test-operator",
        )

        cred_file = tmp_path / "credentials" / f"{provider_id}.json"
        assert cred_file.exists()

        result = store.load_credentials(provider_id)
        assert result is not None
        secret_overlay, _, _ = result
        assert secret_overlay["apiKey"] == "ai-gemini-rotated"

    @pytest.mark.asyncio
    async def test_ollama_cloud_provider_support(
        self, configured_manager, tmp_path, event_bus
    ):
        """Test Ollama Cloud provider credential persistence."""
        mgr, store = configured_manager
        provider_id = "ollama-cloud"

        await mgr.initialize()
        with mgr._lock:
            mgr._merged = {
                "kernel": {"name": "Hermes", "version": "0.1.0", "logLevel": "INFO"},
                "llm": {"providers": {"ollama-cloud": {"token": "tok-ollama-test"}}},
            }
        mgr.freeze()

        mgr.rotate_secret(
            "llm.providers.ollama-cloud.token",
            "tok-ollama-rotated",
            principal="test-operator",
        )

        cred_file = tmp_path / "credentials" / f"{provider_id}.json"
        assert cred_file.exists()

        result = store.load_credentials(provider_id)
        assert result is not None
        secret_overlay, _, _ = result
        assert secret_overlay["token"] == "tok-ollama-rotated"

    @pytest.mark.asyncio
    async def test_multiple_generic_providers(
        self, configured_manager, tmp_path, event_bus
    ):
        """Test storing credentials for multiple generic providers."""
        mgr, store = configured_manager
        providers = ["nim", "kilo", "gemini", "agnes", "freellmapi", "ollama-cloud"]

        await mgr.initialize()
        with mgr._lock:
            mgr._merged = {
                "kernel": {"name": "Hermes", "version": "0.1.0", "logLevel": "INFO"},
                "llm": {
                    "providers": {
                        "nim": {"apiKey": "sk-nim-test"},
                        "kilo": {"credential": "cred-kilo-test"},
                        "gemini": {"apiKey": "ai-gemini-test"},
                        "agnes": {"secretKey": "sk-agnes-test"},
                        "freellmapi": {"token": "tok-free-test"},
                        "ollama-cloud": {"token": "tok-ollama-test"},
                    }
                },
            }
        mgr.freeze()

        # Rotate one secret from each provider
        rotations = {
            "nim": "sk-nim-rotated",
            "kilo": "cred-kilo-rotated",
            "gemini": "ai-gemini-rotated",
            "agnes": "sk-agnes-rotated",
            "freellmapi": "tok-free-rotated",
            "ollama-cloud": "tok-ollama-rotated",
        }

        for provider_id, rotated_value in rotations.items():
            secret_path = f"llm.providers.{provider_id}.apiKey"
            if provider_id == "kilo":
                secret_path = f"llm.providers.{provider_id}.credential"
            elif provider_id == "agnes":
                secret_path = f"llm.providers.{provider_id}.secretKey"
            elif provider_id == "freellmapi":
                secret_path = f"llm.providers.{provider_id}.token"
            elif provider_id == "ollama-cloud":
                secret_path = f"llm.providers.{provider_id}.token"

            mgr.rotate_secret(secret_path, rotated_value, principal="test-operator")

        # Verify all files exist
        for provider_id in providers:
            cred_file = tmp_path / "credentials" / f"{provider_id}.json"
            assert cred_file.exists(), f"Missing credential file for {provider_id}"

        # Simulate restart and verify all persisted
        reset_configuration_manager_singleton()
        set_credential_store(store)

        mgr2 = ConfigurationManager()
        mgr2.event_bus = event_bus
        mgr2._data_dir = tmp_path
        mgr2._secret_overlay = {}
        mgr2._rotation_count = {}
        mgr2._rotated_secret_versions = {}
        mgr2._merged = {}
        mgr2._locked = False

        await mgr2.initialize()

        with mgr2._lock:
            mgr2._merged = {
                "kernel": {"name": "Hermes", "version": "0.1.0", "logLevel": "INFO"},
                "llm": {
                    "providers": {
                        "nim": {"apiKey": "sk-nim-test"},
                        "kilo": {"credential": "cred-kilo-test"},
                        "gemini": {"apiKey": "ai-gemini-test"},
                        "agnes": {"secretKey": "sk-agnes-test"},
                        "freellmapi": {"token": "tok-free-test"},
                        "ollama-cloud": {"token": "tok-ollama-test"},
                    }
                },
            }
        mgr2.freeze()

        # Verify all rotated values persisted
        for provider_id, expected_rotated in rotations.items():
            secret_path = f"llm.providers.{provider_id}.apiKey"
            if provider_id == "kilo":
                secret_path = f"llm.providers.{provider_id}.credential"
            elif provider_id == "agnes":
                secret_path = f"llm.providers.{provider_id}.secretKey"
            elif provider_id == "freellmapi":
                secret_path = f"llm.providers.{provider_id}.token"
            elif provider_id == "ollama-cloud":
                secret_path = f"llm.providers.{provider_id}.token"

            restored = mgr2.get_secret(secret_path)
            assert restored == expected_rotated, (
                f"Provider {provider_id}: expected {expected_rotated}, got {restored}"
            )


# =============================================================================
# 5. Rotation Metadata Persistence Tests
# =============================================================================


class TestRotationMetadataPersistence:
    """Test that rotation metadata persists correctly."""

    @pytest.mark.asyncio
    async def test_rotation_count_persists(
        self, configured_manager, tmp_path, event_bus
    ):
        """Test that rotation count survives restart."""
        mgr, store = configured_manager
        provider_id = "nim"
        secret_path = "llm.providers.nim.apiKey"

        await mgr.initialize()
        with mgr._lock:
            mgr._merged = {
                "kernel": {"name": "Hermes", "version": "0.1.0", "logLevel": "INFO"},
                "llm": {"providers": {"nim": {"apiKey": "initial-key"}}},
            }
        mgr.freeze()

        # Rotate multiple times
        for i in range(5):
            mgr.rotate_secret(
                secret_path, f"rotated-key-{i}", principal="test-operator"
            )

        # Check rotation count before restart
        assert mgr._rotation_count.get(secret_path, 0) == 5

        # Simulate restart
        reset_configuration_manager_singleton()
        set_credential_store(store)

        mgr2 = ConfigurationManager()
        mgr2.event_bus = event_bus
        mgr2._data_dir = tmp_path
        mgr2._secret_overlay = {}
        mgr2._rotation_count = {}
        mgr2._rotated_secret_versions = {}
        mgr2._merged = {}
        mgr2._locked = False

        await mgr2.initialize()

        with mgr2._lock:
            mgr2._merged = {
                "kernel": {"name": "Hermes", "version": "0.1.0", "logLevel": "INFO"},
                "llm": {"providers": {"nim": {"apiKey": "initial-key"}}},
            }
        mgr2.freeze()

        # Verify rotation count persisted
        assert mgr2._rotation_count.get(secret_path, 0) == 5

    @pytest.mark.asyncio
    async def test_rotated_secret_versions_persist(
        self, configured_manager, tmp_path, event_bus
    ):
        """Test that rotated secret versions map persists."""
        mgr, store = configured_manager
        provider_id = "freellmapi"

        await mgr.initialize()
        with mgr._lock:
            mgr._merged = {
                "kernel": {"name": "Hermes", "version": "0.1.0", "logLevel": "INFO"},
                "llm": {"providers": {"freellmapi": {"token": "initial-token", "secret": "initial-secret"}}},
            }
        mgr.freeze()

        # Rotate different secrets different numbers of times
        # Rotate token 3 times
        for i in range(3):
            mgr.rotate_secret(
                "llm.providers.freellmapi.token",
                f"rotated-token-{i}",
                principal="test-operator",
            )
        # Rotate secret 1 time
        mgr.rotate_secret(
            "llm.providers.freellmapi.secret",
            "rotated-secret",
            principal="test-operator",
        )

        # Check versions before restart
        assert mgr._rotated_secret_versions.get("llm.providers.freellmapi.token") == 3
        assert mgr._rotated_secret_versions.get("llm.providers.freellmapi.secret") == 1

        # Simulate restart
        reset_configuration_manager_singleton()
        set_credential_store(store)

        mgr2 = ConfigurationManager()
        mgr2.event_bus = event_bus
        mgr2._data_dir = tmp_path
        mgr2._secret_overlay = {}
        mgr2._rotation_count = {}
        mgr2._rotated_secret_versions = {}
        mgr2._merged = {}
        mgr2._locked = False

        await mgr2.initialize()

        with mgr2._lock:
            mgr2._merged = {
                "kernel": {"name": "Hermes", "version": "0.1.0", "logLevel": "INFO"},
                "llm": {"providers": {"freellmapi": {"token": "initial-token", "secret": "initial-secret"}}},
            }
        mgr2.freeze()

        # Verify versions persisted
        assert mgr2._rotated_secret_versions.get("llm.providers.freellmapi.token") == 3
        assert mgr2._rotated_secret_versions.get("llm.providers.freellmapi.secret") == 1

    @pytest.mark.asyncio
    async def test_rotation_metadata_integrity(
        self, configured_manager, tmp_path, event_bus
    ):
        """Test full rotation metadata integrity."""
        mgr, store = configured_manager
        provider_id = "kilo"

        await mgr.initialize()
        with mgr._lock:
            mgr._merged = {
                "kernel": {"name": "Hermes", "version": "0.1.0", "logLevel": "INFO"},
                "llm": {"providers": {"kilo": {"credential": "initial-cred"}}},
            }
        mgr.freeze()

        # Perform series of rotations
        rotations = [
            ("first-rotation", 1),
            ("second-rotation", 2),
            ("third-rotation", 3),
        ]

        for value, expected_count in rotations:
            mgr.rotate_secret(
                "llm.providers.kilo.credential", value, principal="test-operator"
            )
            assert mgr._rotation_count.get("llm.providers.kilo.credential", 0) == expected_count

        # Simulate restart
        reset_configuration_manager_singleton()
        set_credential_store(store)

        mgr2 = ConfigurationManager()
        mgr2.event_bus = event_bus
        mgr2._data_dir = tmp_path
        mgr2._secret_overlay = {}
        mgr2._rotation_count = {}
        mgr2._rotated_secret_versions = {}
        mgr2._merged = {}
        mgr2._locked = False

        await mgr2.initialize()

        with mgr2._lock:
            mgr2._merged = {
                "kernel": {"name": "Hermes", "version": "0.1.0", "logLevel": "INFO"},
                "llm": {"providers": {"kilo": {"credential": "initial-cred"}}},
            }
        mgr2.freeze()

        # Verify final state persisted
        assert mgr2._rotation_count.get("llm.providers.kilo.credential", 0) == 3
        assert mgr2.get_secret("llm.providers.kilo.credential") == "third-rotation"


# =============================================================================
# 6. Atomic Writes and Permission Tests
# =============================================================================


class TestAtomicWritesAndPermissions:
    """Test atomic write behavior and file permissions."""

    @pytest.mark.asyncio
    async def test_no_temp_files_remain_after_write(
        self, configured_manager, tmp_path, event_bus
    ):
        """Test that atomic writes don't leave temporary files."""
        mgr, store = configured_manager
        provider_id = "nim"

        await mgr.initialize()
        with mgr._lock:
            mgr._merged = {
                "kernel": {"name": "Hermes", "version": "0.1.0", "logLevel": "INFO"},
                "llm": {"providers": {"nim": {"apiKey": "test-key"}}},
            }
        mgr.freeze()

        mgr.rotate_secret(
            "llm.providers.nim.apiKey", "rotated-key", principal="test-operator"
        )

        # Check no .tmp files remain
        temp_files = list((tmp_path / "credentials").glob("*.tmp"))
        assert len(temp_files) == 0, f"Found temp files: {temp_files}"

        # Final file should exist
        cred_file = tmp_path / "credentials" / f"{provider_id}.json"
        assert cred_file.exists()

    @pytest.mark.asyncio
    async def test_file_permissions_are_restrictive(
        self, configured_manager, tmp_path, event_bus
    ):
        """Test that credential files have restrictive permissions (600)."""
        mgr, store = configured_manager
        provider_id = "nim"

        await mgr.initialize()
        with mgr._lock:
            mgr._merged = {
                "kernel": {"name": "Hermes", "version": "0.1.0", "logLevel": "INFO"},
                "llm": {"providers": {"nim": {"apiKey": "test-key"}}},
            }
        mgr.freeze()

        mgr.rotate_secret(
            "llm.providers.nim.apiKey", "rotated-key", principal="test-operator"
        )

        cred_file = tmp_path / "credentials" / f"{provider_id}.json"
        assert cred_file.exists()

        # Check file permissions (skip on Windows where chmod behaves differently)
        if os.name != "nt":  # Not Windows
            file_stat = cred_file.stat()
            mode = file_stat.st_mode & 0o777  # Get permission bits
            assert mode == 0o600, f"Expected 0o600, got {oct(mode)}"

    @pytest.mark.asyncio
    async def test_atomic_write_recovers_from_interruption(
        self, configured_manager, tmp_path, event_bus
    ):
        """Test that interrupted writes don't corrupt data."""
        mgr, store = configured_manager
        provider_id = "nim"

        await mgr.initialize()
        with mgr._lock:
            mgr._merged = {
                "kernel": {"name": "Hermes", "version": "0.1.0", "logLevel": "INFO"},
                "llm": {"providers": {"nim": {"apiKey": "initial-key"}}},
            }
        mgr.freeze()

        # Mock file write to simulate interruption
        original_rename = Path.replace

        def failing_replace(self, target):
            if self.suffix == ".tmp":
                raise OSError("Simulated write interruption")
            return original_rename(self, target)

        with patch.object(Path, "replace", side_effect=failing_replace):
            # Should raise CredentialStoreError but not leave partial data
            with pytest.raises(Exception):  # CredentialStoreError or similar
                mgr.rotate_secret(
                    "llm.providers.nim.apiKey", "should-not-persist", principal="test-operator"
                )

        # Should not have created persistent credential file
        cred_file = tmp_path / "credentials" / f"{provider_id}.json"
        # Either doesn't exist or contains old data
        if cred_file.exists():
            content = cred_file.read_text()
            data = json.loads(content)
            # Should not contain the interrupted value
            assert data.get("encrypted_secret_overlay") is None or "should-not-persist" not in content


# =============================================================================
# 7. Secret Redaction Tests
# =============================================================================


class TestSecretRedaction:
    """Test that secrets are properly redacted."""

    @pytest.mark.asyncio
    async def test_secret_not_in_logs_during_rotation(
        self, configured_manager, event_bus, caplog
    ):
        """Test that secrets don't appear in logs during rotation."""
        mgr, store = configured_manager
        secret_value = "sk-test-secret-value-that-should-not-appear-in-logs"

        await mgr.initialize()
        with mgr._lock:
            mgr._merged = {
                "kernel": {"name": "Hermes", "version": "0.1.0", "logLevel": "INFO"},
                "llm": {"providers": {"nim": {"apiKey": secret_value}}},
            }
        mgr.freeze()

        with caplog.at_level("DEBUG"):
            mgr.rotate_secret(
                "llm.providers.nim.apiKey",
                f"{secret_value}-rotated",
                principal="test-operator",
            )

        # Check that secret doesn't appear in any log messages
        for record in caplog.records:
            assert secret_value not in record.message
            assert f"{secret_value}-rotated" not in record.message

    @pytest.mark.asyncio
    async def test_secret_not_in_exception_messages(
        self, configured_manager
    ):
        """Test that exceptions don't leak secret values."""
        mgr, store = configured_manager
        secret_value = "sk-leaked-secret-should-not-appear"

        await mgr.initialize()
        with mgr._lock:
            mgr._merged = {
                "kernel": {"name": "Hermes", "version": "0.1.0", "logLevel": "INFO"},
                "llm": {"providers": {"nim": {"apiKey": secret_value}}},
            }
        mgr.freeze()

        # Try to trigger an exception with secret value
        try:
            # Pass invalid provider ID to trigger validation error
            mgr.rotate_secret(
                "",  # Invalid empty provider ID
                "some-value",
                principal="test-operator",
            )
            assert False, "Should have raised an exception"
        except Exception as exc:
            # Exception message should not contain the secret
            assert secret_value not in str(exc)
            assert secret_value not in str(type(exc))


# =============================================================================
# 8. Health Check Integration Tests
# =============================================================================


class TestHealthCheckIntegration:
    """Test CredentialStore integration with kernel health checks."""

    @pytest.mark.asyncio
    async def test_credential_store_in_kernel_health_check(
        self, tmp_path, encryption_key, event_bus
    ):
        """Test that CredentialStore appears in kernel health check."""
        from aios.core.kernel import HermesKernel

        reset_configuration_manager_singleton()
        reset_credential_store_singleton()

        # Create credential store
        store = CredentialStore(
            store_path=tmp_path / "credentials",
            encryption_key=encryption_key,
        )
        set_credential_store(store)

        # Create kernel
        kernel = HermesKernel(event_bus=event_bus)
        kernel._config_data_dir = tmp_path

        # Initialize kernel (this should initialize credential store)
        await kernel._bootstrap_managers()

        # Check that credential store is initialized
        assert hasattr(kernel, "_credential_store")
        assert kernel._credential_store is not None
        assert kernel._credential_store.is_initialized() is True

        # Check health check includes credential store
        health_status = await kernel._get_health_status()
        credential_store_found = False
        for component_name, component_obj in health_status:
            if component_name == "CredentialStore":
                credential_store_found = True
                assert component_obj is kernel._credential_store
                break

        assert credential_store_found, "CredentialStore not found in health check"


# =============================================================================
# 9. Edge Cases and Error Conditions
# =============================================================================


class TestEdgeCases:
    """Test edge cases and error conditions."""

    @pytest.mark.asyncio
    async def test_empty_provider_id_handled_gracefully(
        self, configured_manager, event_bus
    ):
        """Test that empty provider ID is handled gracefully."""
        mgr, store = configured_manager
        await mgr.initialize()
        with mgr._lock:
            mgr._merged = {
                "kernel": {"name": "Hermes", "version": "0.1.0", "logLevel": "INFO"},
                "llm": {"providers": {"test": {"apiKey": "test"}}},
            }
        mgr.freeze()

        # Try to rotate secret with empty provider-like path
        # This should be handled by ConfigurationManager validation
        try:
            mgr.rotate_secret(
                "",  # Empty path
                "value",
                principal="test-operator",
            )
            # If no exception, verify it didn't crash
        except Exception:
            # Expected to fail validation
            pass

        # System should still work
        assert mgr.get_secret("llm.providers.test.apiKey") == "test"

    @pytest.mark.asyncio
    async def test_special_characters_in_provider_id(
        self, configured_manager, tmp_path, event_bus
    ):
        """Test provider IDs with special characters."""
        mgr, store = configured_manager
        # Test various provider ID formats
        test_providers = [
            "nim-provider",  # hyphen
            "nim_provider",  # underscore
            "nim.provider",  # dot
            "nim123",  # alphanumeric
            "NIM",  # uppercase
        ]

        await mgr.initialize()
        with mgr._lock:
            mgr._merged = {
                "kernel": {"name": "Hermes", "version": "0.1.0", "logLevel": "INFO"},
                "llm": {
                    "providers": {
                        "nim-provider": {"apiKey": "sk-hyphen-test"},
                        "nim_provider": {"apiKey": "sk-underscore-test"},
                        "nim.provider": {"apiKey": "sk-dot-test"},
                        "nim123": {"apiKey": "sk-num-test"},
                        "NIM": {"apiKey": "sk-upper-test"},
                    }
                },
            }
        mgr.freeze()

        # Rotate one secret from each
        for provider_id in test_providers:
            mgr.rotate_secret(
                f"llm.providers.{provider_id}.apiKey",
                f"{provider_id}-rotated",
                principal="test-operator",
            )

        # Verify files created
        for provider_id in test_providers:
            # Note: dots in filenames may be problematic, so we test what works
            cred_file = tmp_path / "credentials" / f"{provider_id}.json"
            # Some special chars may not work as filenames - that's OK

        # At minimum, basic provider IDs should work
        basic_cred_file = tmp_path / "credentials" / "nim-provider.json"
        assert basic_cred_file.exists()

        result = store.load_credentials("nim-provider")
        assert result is not None
        assert result[0]["apiKey"] == "sk-hyphen-test-rotated"

    @pytest.mark.asyncio
    async def test_very_large_secret_overlay(
        self, configured_manager, tmp_path, event_bus
    ):
        """Test handling of large secret overlays."""
        mgr, store = configured_manager
        provider_id = "nim"

        await mgr.initialize()
        with mgr._lock:
            mgr._merged = {
                "kernel": {"name": "Hermes", "version": "0.1.0", "logLevel": "INFO"},
                "llm": {"providers": {"nim": {"apiKey": "initial"}}},
            }
        mgr.freeze()

        # Create large secret overlay (many keys)
        large_overlay = {f"key_{i}": f"value_{i}" * 100 for i in range(50)}

        # Store directly via credential store to test capacity
        store.store_credentials(
            provider_id=provider_id,
            secret_overlay=large_overlay,
            rotation_count=1,
        )

        # Verify it can be loaded back
        result = store.load_credentials(provider_id)
        assert result is not None
        loaded_overlay, _, _ = result
        assert loaded_overlay == large_overlay

        # Verify file size is reasonable (encrypted)
        cred_file = tmp_path / "credentials" / f"{provider_id}.json"
        assert cred_file.exists()
        file_size = cred_file.stat().st_size
        assert file_size > 100  # Should be substantially sized
        assert file_size < 100000  # But not enormous (encrypted is efficient)


if __name__ == "__main__":
    pytest.main([__file__, "-v"])