"""
CredentialStore — encrypted credential persistence for ConfigurationManager secret overlays.

Provides secure, encrypted-at-rest persistence for rotated provider credentials,
supporting arbitrary provider IDs (NVIDIA NIM, FreeLLMAPI, Kilo, Agnes, Gemini,
Ollama Cloud, etc.) while keeping credentials encrypted at rest.

Architecture:
  * Generic CredentialStore abstraction (provider-agnostic)
  * Fernet-based encryption for data at rest
  * Secure key management via environment variable (AIOS_CREDENTIAL_STORE_KEY)
  * Atomic writes with safe file permissions (chmod 600)
  * Fail-closed behavior on corruption/decryption failure
  * Integration with ConfigurationManager's secret rotation lifecycle

Security constraints:
  * No hardcoded encryption keys
  * Key never stored beside ciphertext
  * Plaintext credentials never written to disk
  * Credentials NOT placed in ordinary YAML/JSON configuration
  * Credentials NOT exposed through normal configuration snapshots
  * Separate from data/storage/ (uses data/credentials/)
"""

from __future__ import annotations

import asyncio
import base64
import json
import logging
import os
import stat
import threading
from pathlib import Path
from typing import Any

from cryptography.fernet import Fernet, InvalidToken

logger = logging.getLogger(__name__)

# Supported provider credential schemas (generic metadata tracking).
_PROVIDER_SCHEMA_VERSION = "1.0"


class CredentialStoreError(Exception):
    """CredentialStore failure."""

    def __init__(
        self,
        message: str,
        *,
        original_error: BaseException | None = None,
    ) -> None:
        self.original_error = original_error
        super().__init__(message)


class CredentialStore:
    """
    Generic encrypted credential persistence store.

    Stores provider credential data (secret overlays, rotation metadata)
    encrypted at rest using Fernet symmetric encryption. Supports arbitrary
    provider IDs generically without provider-specific stores.

    Design constraints:
      * No hardcoded encryption keys — loaded from AIOS_CREDENTIAL_STORE_KEY
      * Fail-closed on corruption/decryption failure
      * Atomic file writes with safe permissions (600)
      * Separate from ordinary StorageManager JSON persistence
      * Secret overlay data only (no raw config)
    """

    def __init__(
        self,
        store_path: Path | None = None,
        *,
        encryption_key: bytes | None = None,
    ) -> None:
        """
        Initialize CredentialStore.

        Args:
            store_path: Path to credential storage directory (default: data/credentials/)
            encryption_key: Optional explicit key for testing; production uses env var
        """
        self._store_path = store_path or Path("data/credentials")
        self._store_path.mkdir(parents=True, exist_ok=True)
        self._lock = threading.RLock()
        self._fernet: Fernet | None = None

        # Set encryption key (production: from env var, test: from parameter)
        if encryption_key is not None:
            # Support both raw 32-byte keys and 44-byte base64-encoded keys
            # Normalize to Fernet-compatible format (base64-encoded)
            if len(encryption_key) == 32:
                # Raw 32-byte key: encode to base64 for Fernet
                encryption_key = base64.urlsafe_b64encode(encryption_key)
            elif len(encryption_key) != 44:
                raise CredentialStoreError(
                    "Encryption key must be 32 bytes (raw) or 44 bytes (base64-encoded)",
                    original_error=ValueError("Invalid key length"),
                )
            self._fernet = Fernet(encryption_key)
        else:
            # Load from environment variable (production path)
            self._load_key_from_environment()

    def _load_key_from_environment(self) -> None:
        """Load encryption key from environment variable (fail-closed)."""
        key_env = os.environ.get("AIOS_CREDENTIAL_STORE_KEY")
        if not key_env:
            logger.warning(
                "AIOS_CREDENTIAL_STORE_KEY not set; credential persistence disabled "
                "(fail-closed: no plaintext fallback)"
            )
            return

        try:
            # Environment variable contains URL-safe base64-encoded key
            key_bytes = base64.urlsafe_b64decode(key_env)
            if len(key_bytes) != 32:
                logger.warning(
                    "AIOS_CREDENTIAL_STORE_KEY has invalid length (%d bytes); "
                    "credential persistence disabled",
                    len(key_bytes),
                )
                return
            self._fernet = Fernet(key_bytes)
        except Exception as exc:  # noqa: BLE001
            logger.warning(
                "Failed to decode AIOS_CREDENTIAL_STORE_KEY: %s; "
                "credential persistence disabled (fail-closed)",
                exc,
            )

    def _ensure_fernet(self) -> Fernet:
        """Ensure Fernet instance is available (fail-closed)."""
        if self._fernet is None:
            raise CredentialStoreError(
                "CredentialStore not initialized: no encryption key available. "
                "Set AIOS_CREDENTIAL_STORE_KEY environment variable.",
                original_error=RuntimeError("No encryption key"),
            )
        return self._fernet

    # ------------------------------------------------------------------
    # Public API — generic provider credential operations
    # ------------------------------------------------------------------

    def store_credentials(
        self,
        provider_id: str,
        secret_overlay: dict[str, Any],
        rotation_count: int = 0,
        rotated_secret_versions: dict[str, int] | None = None,
    ) -> None:
        """
        Store encrypted credential data for a provider.

        Args:
            provider_id: Generic provider identifier (e.g., 'nim', 'freellmapi', 'kilo')
            secret_overlay: Dict of secret paths to values (e.g., {'apiKey': 'sk-...'})
            rotation_count: Current rotation count
            rotated_secret_versions: Dict mapping secret paths to rotation versions

        Raises:
            CredentialStoreError: If encryption/key unavailable or write fails
        """
        if not provider_id or not isinstance(provider_id, str):
            raise CredentialStoreError("provider_id must be a non-empty string")

        fernet = self._ensure_fernet()

        # Build credential payload (metadata + encrypted secrets)
        payload = {
            "schema_version": _PROVIDER_SCHEMA_VERSION,
            "provider_id": provider_id,
            "encrypted_at": asyncio.get_event_loop().time() if asyncio.get_event_loop().is_running() else 0.0,
            "rotation_count": rotation_count,
            "rotated_secret_versions": rotated_secret_versions or {},
            # Encrypt the secret overlay
            "encrypted_secret_overlay": self._encrypt_secret_overlay(
                fernet, secret_overlay
            ),
        }

        # Atomic write to provider-specific file
        file_path = self._store_path / f"{provider_id}.json"
        self._atomic_write(file_path, payload)

        logger.debug(
            "Stored encrypted credentials for provider '%s' "
            "(rotation_count=%d)",
            provider_id,
            rotation_count,
        )

    def load_credentials(
        self, provider_id: str
    ) -> tuple[dict[str, Any], int, dict[str, int]] | None:
        """
        Load and decrypt credential data for a provider.

        Args:
            provider_id: Generic provider identifier

        Returns:
            Tuple of (secret_overlay, rotation_count, rotated_secret_versions)
            or None if no credentials exist or load fails (fail-closed)
        """
        if not provider_id or not isinstance(provider_id, str):
            return None

        file_path = self._store_path / f"{provider_id}.json"
        if not file_path.exists():
            logger.debug("No credential file found for provider '%s'", provider_id)
            return None

        try:
            fernet = self._ensure_fernet()
            payload = self._atomic_read(file_path)

            # Validate schema version
            if payload.get("schema_version") != _PROVIDER_SCHEMA_VERSION:
                logger.warning(
                    "Credential file for '%s' has incompatible schema version %s",
                    provider_id,
                    payload.get("schema_version"),
                )
                return None

            # Decrypt secret overlay
            secret_overlay = self._decrypt_secret_overlay(
                fernet, payload.get("encrypted_secret_overlay")
            )

            rotation_count = payload.get("rotation_count", 0)
            rotated_secret_versions = payload.get("rotated_secret_versions", {})

            logger.debug(
                "Loaded encrypted credentials for provider '%s' "
                "(rotation_count=%d)",
                provider_id,
                rotation_count,
            )

            return (secret_overlay, rotation_count, rotated_secret_versions)

        except CredentialStoreError as exc:
            # Fail-closed: don't leak plaintext, don't fabricate credentials
            logger.error("Failed to load credentials for '%s': %s", provider_id, exc)
            return None
        except Exception as exc:  # noqa: BLE001
            # Catch all other failures (corruption, invalid format, etc.)
            logger.error(
                "Unexpected error loading credentials for '%s': %s",
                provider_id,
                exc,
            )
            return None

    def delete_credentials(self, provider_id: str) -> bool:
        """
        Delete credential file for a provider.

        Args:
            provider_id: Generic provider identifier

        Returns:
            True if deleted, False if file didn't exist
        """
        file_path = self._store_path / f"{provider_id}.json"
        if not file_path.exists():
            return False

        try:
            file_path.unlink()
            logger.debug("Deleted credential file for provider '%s'", provider_id)
            return True
        except OSError as exc:
            logger.warning(
                "Failed to delete credential file for '%s': %s", provider_id, exc
            )
            return False

    # ------------------------------------------------------------------
    # Internal methods — encryption/decryption
    # ------------------------------------------------------------------

    def _encrypt_secret_overlay(
        self, fernet: Fernet, secret_overlay: dict[str, Any]
    ) -> str:
        """Encrypt secret overlay dictionary."""
        if not secret_overlay:
            # Encrypt empty dict to maintain structure
            return base64.urlsafe_b64encode(
                fernet.encrypt(json.dumps({}).encode())
            ).decode()

        # Serialize and encrypt
        plaintext = json.dumps(secret_overlay, sort_keys=True).encode()
        ciphertext = fernet.encrypt(plaintext)
        return base64.urlsafe_b64encode(ciphertext).decode()

    def _decrypt_secret_overlay(
        self, fernet: Fernet, encrypted_overlay: str
    ) -> dict[str, Any]:
        """Decrypt secret overlay dictionary."""
        if not encrypted_overlay:
            return {}

        try:
            ciphertext = base64.urlsafe_b64decode(encrypted_overlay)
            plaintext = fernet.decrypt(ciphertext)
            return json.loads(plaintext)
        except InvalidToken:
            raise CredentialStoreError(
                "Decryption failed: invalid token (key mismatch or corruption)",
                original_error=InvalidToken(),
            )
        except Exception as exc:  # noqa: BLE001
            raise CredentialStoreError(
                f"Failed to decrypt secret overlay: {exc}",
                original_error=exc,
            )

    # ------------------------------------------------------------------
    # Internal methods — atomic file operations
    # ------------------------------------------------------------------

    def _atomic_write(self, file_path: Path, payload: dict[str, Any]) -> None:
        """Atomic write with safe permissions."""
        tmp_path = file_path.with_suffix(".tmp")
        try:
            # Write to temp file first
            with open(tmp_path, "w", encoding="utf-8") as f:
                json.dump(payload, f, indent=2, sort_keys=True)

            # Set restrictive permissions (owner-only: 600)
            tmp_path.chmod(stat.S_IRUSR | stat.S_IWUSR)

            # Atomic rename
            tmp_path.replace(file_path)

            # Ensure final permissions are correct
            file_path.chmod(stat.S_IRUSR | stat.S_IWUSR)

        except OSError as exc:
            # Clean up temp file on failure
            if tmp_path.exists():
                tmp_path.unlink(missing_ok=True)
            raise CredentialStoreError(
                f"Failed to write credential file: {exc}",
                original_error=exc,
            )

    def _atomic_read(self, file_path: Path) -> dict[str, Any]:
        """Safe read from credential file."""
        if not file_path.exists():
            raise CredentialStoreError(f"Credential file not found: {file_path}")

        try:
            with open(file_path, "r", encoding="utf-8") as f:
                return json.load(f)
        except json.JSONDecodeError as exc:
            raise CredentialStoreError(
                f"Corrupted credential file (invalid JSON): {exc}",
                original_error=exc,
            )
        except OSError as exc:
            raise CredentialStoreError(
                f"Failed to read credential file: {exc}",
                original_error=exc,
            )

    # ------------------------------------------------------------------
    # Health and verification
    # ------------------------------------------------------------------

    def is_initialized(self) -> bool:
        """Check if CredentialStore is properly initialized."""
        return self._fernet is not None

    def verify_integrity(self, provider_id: str) -> bool:
        """
        Verify credential integrity (reload without exposing secrets).

        Args:
            provider_id: Generic provider identifier

        Returns:
            True if credentials can be loaded and decrypted successfully
        """
        result = self.load_credentials(provider_id)
        if result is None:
            return False

        secret_overlay, rotation_count, rotated_secret_versions = result
        # Verify metadata consistency
        if not isinstance(secret_overlay, dict):
            return False
        if not isinstance(rotation_count, int) or rotation_count < 0:
            return False
        if not isinstance(rotated_secret_versions, dict):
            return False

        return True

    def list_providers(self) -> list[str]:
        """List all providers with stored credentials."""
        providers = []
        for file_path in self._store_path.glob("*.json"):
            if file_path.suffix == ".json" and file_path.stem != ".tmp":
                providers.append(file_path.stem)
        return sorted(providers)


# ---------------------------------------------------------------------------
# Singleton pattern (process-wide)
# ---------------------------------------------------------------------------

_global_credential_store: CredentialStore | None = None
_singleton_lock = threading.Lock()


def get_credential_store(store_path: Path | None = None) -> CredentialStore | None:
    """Get or create the global CredentialStore singleton."""
    global _global_credential_store
    with _singleton_lock:
        if _global_credential_store is None:
            try:
                _global_credential_store = CredentialStore(store_path=store_path)
            except Exception as exc:  # noqa: BLE001
                logger.warning("Failed to initialize CredentialStore: %s", exc)
                return None
        return _global_credential_store


def set_credential_store(store: CredentialStore) -> None:
    """Set the global CredentialStore singleton (tests only)."""
    global _global_credential_store
    with _singleton_lock:
        _global_credential_store = store


def reset_credential_store_singleton() -> None:
    """Reset the process-wide CredentialStore singleton (tests only)."""
    global _global_credential_store
    with _singleton_lock:
        _global_credential_store = None


__all__ = [
    "CredentialStore",
    "CredentialStoreError",
    "get_credential_store",
    "set_credential_store",
    "reset_credential_store_singleton",
]
