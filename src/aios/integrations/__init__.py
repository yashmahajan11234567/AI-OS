"""
Final External Ecosystem Integration — configuration framework (PHASE 2).

Distinguishes MOCK (simulated) execution from REAL (live external) execution on
a per-integration basis, and enforces fail-closed semantics:

- The default integration mode is ``mock``.
- A REAL connection to an external system is only permitted when the user has
  explicitly set ``mode: real`` for that integration in ``config/integrations.yaml``
  AND the corresponding pytest env gate is satisfied (PHASE 6) where applicable.
- No code path may silently promote a mock to a real external connection.

This module is the single source of truth for "is integration X allowed to make
a REAL external call right now?" Adapters/councils consult ``resolve_mode()`` or
``assert_real_allowed()`` before touching any live endpoint.
"""

from __future__ import annotations

import os
from dataclasses import dataclass, field
from datetime import datetime
from enum import Enum
from pathlib import Path
from typing import Any

from aios.integrations.config import (
    IntegrationConfig,
    IntegrationConfigRegistry,
    load_integrations_config,
    CANONICAL_INTEGRATIONS,
    IntegrationMode,
    REAL_OPERATION_ENV,
    assert_real_allowed,
)
from aios.integrations.state import (
    IntegrationState,
    IntegrationStatusReport,
    ValidationResult,
    HealthCheckResult,
    ConnectionResult,
    can_transition,
)
from aios.integrations.validation import ValidationRegistry, ResourceValidator
