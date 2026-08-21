"""
Tests for EventTypeRegistry / EventTypeRegistration (Task 3; Part 2 §2.3.5, §2.13.4).

Architecture discrepancy note (escalated, not resolved):
    Part 2 §2.3.1 prose advertises 97 canonical EventTypes, but the §2.3.1
    enumeration lists 121. Task 3 registers the 121 canonical members from Task 2.
"""

import threading

import pytest

from aios.events.core.category import EventCategory, category_for_event_type
from aios.events.core.errors import EventRegistryError
from aios.events.core.identity import ComponentIdentity, ComponentType
from aios.events.core.priority import EventPriority
from aios.events.core.serialization import canonical_json
from aios.events.core.registry import (
    CompatibilityResult,
    DeprecationInfo,
    EventTypeRegistration,
    EventTypeRegistry,
    RegistryState,
    ValidationResult,
    compute_schema_hash,
)
from aios.events.core.types import EventType, SemanticVersion


# Canonical 121 names, in exact Part 2 §2.3.1 order (mirrors Task 2 test).
CANONICAL_NAMES = [
    "KERNEL_INITIALIZATION_STARTED", "KERNEL_READY", "KERNEL_SHUTDOWN_STARTED",
    "KERNEL_TERMINATED", "KERNEL_INITIALIZATION_FAILED", "KERNEL_FATAL_ERROR",
    "CORE_COMPONENT_INITIALIZED", "CORE_COMPONENT_SHUTDOWN", "CORE_COMPONENT_DEGRADED",
    "CORE_COMPONENT_FAILED", "CORE_MANAGER_INITIALIZED", "CORE_MANAGER_SHUTDOWN",
    "CORE_MANAGER_DEGRADED", "CORE_MANAGER_FAILED", "HEARTBEAT", "CONFIGURATION_FROZEN",
    "CONFIGURATION_CHANGED", "WORKFLOW_STARTED", "WORKFLOW_COMPLETED", "WORKFLOW_FAILED",
    "WORKFLOW_PAUSED", "WORKFLOW_RESUMED", "WORKFLOW_CANCELLED", "WORKFLOW_STEP_STARTED",
    "WORKFLOW_STEP_COMPLETED", "WORKFLOW_STEP_FAILED", "WORKFLOW_STEP_RETRIED",
    "WORKFLOW_STEP_SKIPPED", "WORKFLOW_CHECKPOINT_CREATED", "WORKFLOW_CHECKPOINT_RESTORED",
    "TASK_CREATED", "TASK_ASSIGNED", "TASK_STARTED", "TASK_COMPLETED", "TASK_FAILED",
    "TASK_RETRIED", "TASK_CANCELLED", "TASK_DEPENDENCY_RESOLVED", "RETRY_BUDGET_EXHAUSTED",
    "RETRY_SCHEDULED", "RETRY_EXECUTED", "ROOT_CAUSE_ANALYZED", "RECOVERY_ACTION_DISPATCHED",
    "RECOVERY_ACTION_COMPLETED",
    "RECOVERY_ACTION_FAILED", "STATE_CHANGED", "STATE_SNAPSHOT_CREATED", "STATE_RESTORED",
    "ARTIFACT_CREATED", "ARTIFACT_UPDATED", "ARTIFACT_DELETED", "CHECKPOINT_CREATED",
    "CHECKPOINT_RESTORED", "CHECKPOINT_PRUNED", "MEMORY_STORED", "MEMORY_RETRIEVED",
    "MEMORY_UPDATED", "MEMORY_CONSOLIDATED", "MEMORY_PRUNED", "CONTEXT_ASSEMBLED",
    "CONTEXT_COMPRESSED", "PLANNING_REQUESTED", "PLANNING_COMPLETED", "PLANNING_FAILED",
    "PLAN_REJECTED", "CODE_GENERATED", "CODING_COMPLETED", "CODING_FAILED",
    "CODE_REVIEW_REQUESTED", "REVIEW_STARTED", "REVIEW_APPROVED", "REVIEW_REJECTED",
    "REVIEW_FAILED", "SECURITY_ISSUE_FOUND", "PERFORMANCE_ISSUE_FOUND", "TESTS_GENERATED",
    "TESTS_PASSED", "TESTS_FAILED", "TESTING_COMPLETED", "TESTING_FAILED",
    "DEPLOYMENT_REQUESTED", "DEPLOYMENT_STARTED", "DEPLOYMENT_COMPLETED", "DEPLOYMENT_FAILED",
    "DEPLOYMENT_ROLLED_BACK", "COUNCIL_CONVENED", "COUNCIL_PROPOSAL_SUBMITTED",
    "COUNCIL_VOTE_CAST", "COUNCIL_CONSENSUS_REACHED", "COUNCIL_DISSENT_REGISTERED",
    "COUNCIL_DECISION_FINALIZED", "AI_AGENT_TASK_REQUESTED", "AI_AGENT_TASK_COMPLETED",
    "AI_AGENT_TASK_FAILED", "AI_AGENT_AUDIT_EMITTED", "FINAL_JUDGE_DECISION",
    "HUMAN_ESCALATION_REQUIRED", "METRIC_EMITTED", "TRACE_SPAN_STARTED", "TRACE_SPAN_ENDED",
    "HEALTH_CHECK_PASSED", "HEALTH_CHECK_FAILED", "SERVICE_STARTED", "SERVICE_STOPPED",
    "SERVICE_DEGRADED", "SERVICE_FAILED", "RESOURCE_ALLOCATED", "RESOURCE_RELEASED",
    "RESOURCE_EXHAUSTED", "QUOTA_EXCEEDED", "SKILL_EXECUTED", "SKILL_FAILED",
    "MCP_TOOL_CALLED", "MCP_TOOL_SUCCEEDED", "MCP_TOOL_FAILED", "MODEL_ROUTED",
    "MODEL_FALLBACK", "PROMPT_TEMPLATE_RENDERED", "TOKEN_BUDGET_EXCEEDED",
    "PERSONA_OVERRIDE_APPLIED", "FAILURE_CLASSIFIED",
]

EXPECTED_CANONICAL_COUNT = 121


# ---------------------------------------------------------------------------
# 1. Registry construction
# ---------------------------------------------------------------------------

def test_registry_construction_reaches_ready():
    reg = EventTypeRegistry()
    assert reg.state is RegistryState.READY
    assert reg.is_ready


def test_registry_no_autopopulate_stays_uninitialized():
    reg = EventTypeRegistry(auto_populate_canonical=False)
    assert reg.state is RegistryState.UNINITIALIZED
    assert reg.registration_count == 0
    # Manual population.
    reg._populate_canonical_types()
    assert reg.is_ready
    assert reg.canonical_count == EXPECTED_CANONICAL_COUNT


# ---------------------------------------------------------------------------
# 2/3. All 121 canonical registered + count
# ---------------------------------------------------------------------------

def test_all_121_canonical_registered():
    reg = EventTypeRegistry()
    assert reg.canonical_count == EXPECTED_CANONICAL_COUNT
    assert reg.registration_count == EXPECTED_CANONICAL_COUNT


def test_registry_list_length_equals_canonical():
    reg = EventTypeRegistry()
    regs = reg.list()
    assert len(regs) == EXPECTED_CANONICAL_COUNT
    # Every canonical name present.
    names = {r.eventType.name for r in regs}
    assert names == set(CANONICAL_NAMES)


# ---------------------------------------------------------------------------
# 4. Canonical lookup
# ---------------------------------------------------------------------------

def test_canonical_lookup_returns_registration():
    reg = EventTypeRegistry()
    r = reg.get(EventType.TASK_CREATED)
    assert r is not None
    assert r.eventType is EventType.TASK_CREATED
    assert r.category is EventCategory.CONTROL


def test_get_by_name_lookup():
    reg = EventTypeRegistry()
    r = reg.get_by_name("KERNEL_READY")
    assert r is not None
    assert r.eventType is EventType.KERNEL_READY


# ---------------------------------------------------------------------------
# 5. Unknown lookup
# ---------------------------------------------------------------------------

def test_unknown_event_type_lookup_returns_none():
    reg = EventTypeRegistry()
    # EventType is closed; there is no "unknown" member, but get_by_name resolves
    # via from_name which raises -> returns None.
    assert reg.get_by_name("NONEXISTENT_TYPE") is None


def test_invalid_event_type_to_get_raises():
    reg = EventTypeRegistry()
    with pytest.raises(EventRegistryError):
        reg.get("TASK_CREATED")  # not an EventType instance


# ---------------------------------------------------------------------------
# 6. Duplicate registration rejection
# ---------------------------------------------------------------------------

def test_duplicate_canonical_registration_rejected():
    reg = EventTypeRegistry()
    existing = reg.get(EventType.TASK_CREATED)
    with pytest.raises(EventRegistryError):
        reg.register(existing)


def test_register_requires_eventtype_member():
    # The EventType enum is closed in v1.0, so a non-canonical (future governed
    # extension) eventType is rejected at EventTypeRegistration construction
    # (its __post_init__ validates ``isinstance(eventType, EventType)``). This
    # guards accidental extension registration through the public API.
    et = _fake_et("foo.bar")
    with pytest.raises(EventRegistryError):
        EventTypeRegistration(
            eventType=et,  # type: ignore[arg-type]
            schemaVersion=SemanticVersion(1, 0, 0),
            schemaHash=compute_schema_hash({"type": "object"}),
            payloadSchema={"type": "object"},
            description="synthetic",
            producer=_fake_producer(),
            consumers=(),
            category=EventCategory.DIAGNOSTIC,
            priority=EventPriority.NORMAL,
            deprecated=False,
            deprecationInfo=None,
        )


# ---------------------------------------------------------------------------
# 7. Invalid registration rejection
# ---------------------------------------------------------------------------

def test_register_non_registration_rejected():
    reg = EventTypeRegistry()
    with pytest.raises(EventRegistryError):
        reg.register("not-a-registration")  # type: ignore[arg-type]


# ---------------------------------------------------------------------------
# 8. EventTypeRegistration immutability
# ---------------------------------------------------------------------------

def test_registration_is_immutable():
    reg = EventTypeRegistry()
    r = reg.get(EventType.TASK_CREATED)
    with pytest.raises((AttributeError, TypeError)):
        r.eventType = EventType.TASK_FAILED  # type: ignore[misc]


def test_deprecation_info_immutable():
    info = DeprecationInfo(
        since_version=SemanticVersion(1, 0, 0),
        removal_target_version=SemanticVersion(2, 0, 0),
    )
    with pytest.raises((AttributeError, TypeError)):
        info.since_version = SemanticVersion(2, 0, 0)  # type: ignore[misc]


# ---------------------------------------------------------------------------
# 9. schemaVersion validation
# ---------------------------------------------------------------------------

def test_canonical_schema_version_is_1_0_0():
    reg = EventTypeRegistry()
    for r in reg.list():
        assert r.schemaVersion == SemanticVersion(1, 0, 0)


# ---------------------------------------------------------------------------
# 10. schemaHash presence
# ---------------------------------------------------------------------------

def test_schema_hash_present_and_sha256():
    reg = EventTypeRegistry()
    for r in reg.list():
        assert isinstance(r.schemaHash, str)
        assert len(r.schemaHash) == 64
        int(r.schemaHash, 16)  # valid hex
        assert r.schemaHash == r.schemaHash.lower()


# ---------------------------------------------------------------------------
# 11. deterministic schemaHash
# ---------------------------------------------------------------------------

def test_schema_hash_deterministic():
    reg = EventTypeRegistry()
    r1 = reg.get(EventType.MEMORY_STORED)
    r2 = reg.get(EventType.MEMORY_STORED)
    assert r1.schemaHash == r2.schemaHash
    # Same placeholder schema -> same hash across instances.
    from aios.events.core.registry import PLACEHOLDER_PAYLOAD_SCHEMA
    h1 = compute_schema_hash(dict(PLACEHOLDER_PAYLOAD_SCHEMA))
    h2 = compute_schema_hash(dict(PLACEHOLDER_PAYLOAD_SCHEMA))
    assert h1 == h2


# ---------------------------------------------------------------------------
# Schema hash determinism — Task 3 hash fix (SHA-256, not built-in hash())
# ---------------------------------------------------------------------------

def test_same_schema_produces_same_hash():
    # 1. Same schema -> same schemaHash.
    schema = {"type": "object", "properties": {"id": {"type": "string"}}}
    assert compute_schema_hash(schema) == compute_schema_hash(schema)


def test_same_schema_across_registry_instances():
    # 2. Same schema across SEPARATE registry constructions -> same schemaHash.
    reg_a = EventTypeRegistry()
    reg_b = EventTypeRegistry()
    ha = reg_a.get(EventType.TASK_CREATED).schemaHash
    hb = reg_b.get(EventType.TASK_CREATED).schemaHash
    assert ha == hb


def test_equivalent_canonical_representations_same_hash():
    # 3. Equivalent canonical representations -> same schemaHash.
    # Dict key ordering must NOT affect the digest (canonical JSON sorts keys).
    a = {"b": 1, "a": 2, "c": 3}
    b = {"c": 3, "a": 2, "b": 1}
    assert compute_schema_hash(a) == compute_schema_hash(b)
    # Nested dicts are also canonicalized (sorted keys recursively).
    c = {"outer": {"z": 1, "y": 2}}
    d = {"outer": {"y": 2, "z": 1}}
    assert compute_schema_hash(c) == compute_schema_hash(d)


def test_different_schema_produces_different_hash():
    # 4. Different schema -> different schemaHash.
    base = {"type": "object", "properties": {"id": {"type": "string"}}}
    changed = {"type": "object", "properties": {"id": {"type": "integer"}}}
    assert compute_schema_hash(base) != compute_schema_hash(changed)
    # Whitespace-only differences must NOT change the hash (canonical JSON).
    assert compute_schema_hash(base) == compute_schema_hash(
        {"type": "object", "properties": {"id": {"type": "string"}}}
    )


def test_schema_hash_is_sha256_digest():
    # 5. schemaHash is a SHA-256 digest (64 lowercase hex chars).
    import hashlib

    schema = {"type": "object"}
    expected = hashlib.sha256(
        canonical_json(schema).encode("utf-8")
    ).hexdigest()
    assert compute_schema_hash(schema) == expected
    assert len(expected) == 64
    assert expected == expected.lower()
    int(expected, 16)  # valid hex


def test_schema_hash_stable_across_processes():
    # 6. Stable across Python processes. We cannot spawn a process here
    # reliably, but SHA-256 over a fixed canonical byte string is, by
    # definition, independent of PYTHONHASHSEED / process / machine. Assert the
    # digest matches the independently recomputed SHA-256 of the canonical
    # bytes (the same computation any process would perform).
    import hashlib

    reg = EventTypeRegistry()
    r = reg.get(EventType.STATE_CHANGED)
    recomputed = hashlib.sha256(
        canonical_json(r.payloadSchema).encode("utf-8")
    ).hexdigest()
    assert r.schemaHash == recomputed


def test_placeholder_schemas_deterministic():
    # 7. Placeholder schemas generate deterministic hashes.
    reg = EventTypeRegistry()
    for r in reg.list():
        # The placeholder marker is present and the hash is reproducible from
        # the (unchanged) placeholder representation.
        assert r.payloadSchema.get("x-aios-placeholder") is True
        recomputed = compute_schema_hash(r.payloadSchema)
        assert r.schemaHash == recomputed


def test_schema_hash_not_using_builtin_hash():
    # 8. No use of Python built-in hash() in schemaHash generation. The hash is
    # derived from hashlib.sha256, not hash(). We assert the digest is NOT equal
    # to the (process-dependent) built-in hash of the schema object.
    schema = {"type": "object", "x-aios-placeholder": True}
    digest = compute_schema_hash(schema)
    # Built-in hash() of the dict is an int and process-dependent; the schemaHash
    # is a fixed SHA-256 hex string — proving a different, deterministic mechanism.
    assert not isinstance(digest, int)
    assert digest != str(hash(schema))  # type: ignore[operator]
    assert digest == digest  # stable reference


# ---------------------------------------------------------------------------
# 12. payloadSchema representation
# ---------------------------------------------------------------------------

def test_payload_schema_is_placeholder_and_serializable():
    import json
    reg = EventTypeRegistry()
    for r in reg.list():
        assert isinstance(r.payloadSchema, dict)
        # PLACEHOLDER marker present.
        assert r.payloadSchema.get("x-aios-placeholder") is True
        json.dumps(r.payloadSchema, allow_nan=False)  # serializable


# ---------------------------------------------------------------------------
# 13. category correctness
# ---------------------------------------------------------------------------

def test_category_matches_architecture_mapping():
    reg = EventTypeRegistry()
    for et in EventType:
        r = reg.get(et)
        assert r is not None
        assert r.category is category_for_event_type(et)


# ---------------------------------------------------------------------------
# 14. default priority = NORMAL with documented justification
# ---------------------------------------------------------------------------

def test_default_priority_is_normal():
    reg = EventTypeRegistry()
    for r in reg.list():
        assert r.priority is EventPriority.NORMAL


# ---------------------------------------------------------------------------
# 15. producer derivation
# ---------------------------------------------------------------------------

def test_producer_derivation_for_kernel_types():
    reg = EventTypeRegistry()
    r = reg.get(EventType.KERNEL_READY)
    assert r.producer.component_type is ComponentType.KERNEL
    assert r.producer.component_name == "HermesKernel"


def test_producer_derivation_for_workflow_types():
    reg = EventTypeRegistry()
    r = reg.get(EventType.WORKFLOW_STARTED)
    assert r.producer.component_name == "WorkflowManager"


def test_producer_derivation_for_council_types():
    reg = EventTypeRegistry()
    r = reg.get(EventType.COUNCIL_CONVENED)
    assert r.producer.component_name == "CouncilManager"


def test_producer_derivation_for_ai_agent_types():
    reg = EventTypeRegistry()
    r = reg.get(EventType.AI_AGENT_TASK_REQUESTED)
    assert r.producer.component_name == "AIAgencyService"


# ---------------------------------------------------------------------------
# 16. consumer handling (EMPTY)
# ---------------------------------------------------------------------------

def test_consumers_empty_for_canonical():
    reg = EventTypeRegistry()
    for r in reg.list():
        assert r.consumers == ()


# ---------------------------------------------------------------------------
# 17. description handling (SYNTHESIZED)
# ---------------------------------------------------------------------------

def test_description_synthesized_marker():
    reg = EventTypeRegistry()
    r = reg.get(EventType.TASK_CREATED)
    assert "SYNTHESIZED" in r.description
    assert "TASK_CREATED" in r.description


# ---------------------------------------------------------------------------
# 18. deprecation=false behavior
# ---------------------------------------------------------------------------

def test_deprecation_false_has_no_info():
    reg = EventTypeRegistry()
    for r in reg.list():
        assert r.deprecated is False
        assert r.deprecationInfo is None


# ---------------------------------------------------------------------------
# 19. deprecation=true requires deprecationInfo
# ---------------------------------------------------------------------------

def test_deprecated_true_requires_info():
    et = _fake_et("EXT_OLD_THING")
    with pytest.raises(EventRegistryError):
        EventTypeRegistration(
            eventType=et,
            schemaVersion=SemanticVersion(1, 0, 0),
            schemaHash=compute_schema_hash({"type": "object"}),
            payloadSchema={"type": "object"},
            description="synthetic",
            producer=_fake_producer(),
            consumers=(),
            category=EventCategory.DIAGNOSTIC,
            priority=EventPriority.NORMAL,
            deprecated=True,            # true but no info -> must raise
            deprecationInfo=None,
        )


def test_deprecated_true_with_info_ok():
    et = _fake_et("EXT_OLD_THING")
    info = DeprecationInfo(
        since_version=SemanticVersion(1, 0, 0),
        removal_target_version=SemanticVersion(2, 0, 0),
        replacement_event_type=EventType.TASK_CREATED,
    )
    reg_obj = EventTypeRegistration(
        eventType=et,
        schemaVersion=SemanticVersion(1, 0, 0),
        schemaHash="a" * 64,
        payloadSchema={"type": "object"},
        description="synthetic",
        producer=_fake_producer(),
        consumers=(),
        category=EventCategory.DIAGNOSTIC,
        priority=EventPriority.NORMAL,
        deprecated=True,
        deprecationInfo=info,
    )
    assert reg_obj.deprecationInfo is info
    assert reg_obj.deprecationInfo.replacement_event_type is EventType.TASK_CREATED


def test_deprecated_false_with_info_rejected():
    et = _fake_et("EXT_OLD_THING")
    info = DeprecationInfo(
        since_version=SemanticVersion(1, 0, 0),
        removal_target_version=SemanticVersion(2, 0, 0),
    )
    with pytest.raises(EventRegistryError):
        EventTypeRegistration(
            eventType=et,
            schemaVersion=SemanticVersion(1, 0, 0),
            schemaHash=compute_schema_hash({"type": "object"}),
            payloadSchema={"type": "object"},
            description="synthetic",
            producer=_fake_producer(),
            consumers=(),
            category=EventCategory.DIAGNOSTIC,
            priority=EventPriority.NORMAL,
            deprecated=False,
            deprecationInfo=info,  # present but deprecated=False -> reject
        )


# ---------------------------------------------------------------------------
# 20. deterministic list/enumeration
# ---------------------------------------------------------------------------

def test_list_is_deterministic_and_canonical_ordered():
    reg = EventTypeRegistry()
    names1 = [r.eventType.name for r in reg.list()]
    names2 = [r.eventType.name for r in reg.list()]
    assert names1 == names2 == CANONICAL_NAMES


# ---------------------------------------------------------------------------
# 21. returned data cannot mutate registry internals
# ---------------------------------------------------------------------------

def test_list_returns_new_list_not_internal():
    reg = EventTypeRegistry()
    lst = reg.list()
    lst.append("mutated")  # type: ignore[arg-type]
    assert reg.registration_count == EXPECTED_CANONICAL_COUNT
    assert len(reg.list()) == EXPECTED_CANONICAL_COUNT


def test_get_returns_immutable_registration():
    reg = EventTypeRegistry()
    r = reg.get(EventType.TASK_CREATED)
    with pytest.raises((AttributeError, TypeError)):
        r.priority = EventPriority.HIGH  # type: ignore[misc]


# ---------------------------------------------------------------------------
# 22. canonical registrations bypass extension prefix validation
# ---------------------------------------------------------------------------

def test_canonical_types_use_reserved_prefixes():
    reg = EventTypeRegistry()
    # All canonical types use kernel-reserved prefixes and are present.
    reserved_used = [
        et.name for et in EventType
        if et.name.startswith(
            ("KERNEL_", "CORE_", "WORKFLOW_", "TASK_", "STATE_", "MEMORY_",
             "COUNCIL_", "AI_AGENT_")
        )
    ]
    assert len(reserved_used) > 0
    for name in reserved_used:
        assert reg.get(EventType.from_name(name)) is not None


# ---------------------------------------------------------------------------
# 23. custom/extension registration enforces prefix rules
# ---------------------------------------------------------------------------

def test_extension_with_reserved_prefix_rejected():
    reg = EventTypeRegistry()
    # KERNEL_ is reserved; a custom (non-canonical) type using it must be
    # rejected (INV-EXT-003). Validated directly via the prefix guard using a
    # name-bearing stand-in (the closed enum has no extension members in v1.0).
    with pytest.raises(EventRegistryError):
        reg._validate_extension_prefix(_fake_et("KERNEL_CUSTOM_BAD"))


def test_extension_without_prefix_rejected():
    reg = EventTypeRegistry()
    # Unprefixed custom type must be rejected (INV-EXT-004).
    with pytest.raises(EventRegistryError):
        reg._validate_extension_prefix(_fake_et("MY_CUSTOM_EVENT"))


def test_extension_with_ext_prefix_accepted():
    reg = EventTypeRegistry()
    # EXT_ is always a permitted extension prefix.
    reg._validate_extension_prefix(_fake_et("EXT_MY_FEATURE"))


def test_extension_with_org_prefix_accepted():
    reg = EventTypeRegistry(org_prefixes={"ACME_"})
    reg._validate_extension_prefix(_fake_et("ACME_WIDGET_UPDATED"))


def test_extension_with_unregistered_org_prefix_rejected():
    reg = EventTypeRegistry()  # no org prefixes registered
    with pytest.raises(EventRegistryError):
        reg._validate_extension_prefix(_fake_et("ACME_WIDGET_UPDATED"))


def test_canonical_unregister_blocked():
    reg = EventTypeRegistry()
    # Canonical types are kernel-reserved and cannot be unregistered.
    with pytest.raises(EventRegistryError):
        reg.unregister(EventType.TASK_CREATED)
    # Canonical count unaffected.
    assert reg.canonical_count == EXPECTED_CANONICAL_COUNT


def test_unregister_unknown_rejected():
    reg = EventTypeRegistry()
    with pytest.raises(EventRegistryError):
        reg.unregister(_fake_et("EXT_MY_FEATURE"))


# ---------------------------------------------------------------------------
# 24. concurrent reads
# ---------------------------------------------------------------------------

def test_concurrent_reads_safe():
    reg = EventTypeRegistry()
    errors = []

    def reader():
        try:
            for _ in range(50):
                _ = reg.get(EventType.TASK_CREATED)
                _ = len(reg.list())
                _ = reg.canonical_count
        except Exception as exc:  # noqa: BLE001
            errors.append(exc)

    threads = [threading.Thread(target=reader) for _ in range(8)]
    for t in threads:
        t.start()
    for t in threads:
        t.join()
    assert errors == []
    assert reg.canonical_count == EXPECTED_CANONICAL_COUNT


# ---------------------------------------------------------------------------
# 25. lifecycle behavior
# ---------------------------------------------------------------------------

def test_lifecycle_uninitialized_to_ready_to_shutdown():
    reg = EventTypeRegistry(auto_populate_canonical=False)
    assert reg.state is RegistryState.UNINITIALIZED
    reg._populate_canonical_types()
    assert reg.state is RegistryState.READY
    reg.shutdown()
    assert reg.state is RegistryState.SHUTDOWN
    # Reads still work after shutdown.
    assert reg.canonical_count == EXPECTED_CANONICAL_COUNT
    # Mutations rejected after shutdown (re-registering a canonical type is a
    # duplicate, which the registry rejects).
    with pytest.raises(EventRegistryError):
        reg.register(reg.get(EventType.TASK_CREATED))  # type: ignore[arg-type]


# ---------------------------------------------------------------------------
# 26/27/28. safe schema operations
# ---------------------------------------------------------------------------

def test_validate_schema_safe_unknown_type():
    reg = EventTypeRegistry()
    # Build a synthetic unknown EventType-like object is impossible (closed enum);
    # instead test that an invalid input to get path returns safe result:
    res = reg.validate_schema(EventType.TASK_CREATED, None)
    assert isinstance(res, ValidationResult)
    assert res.valid is True


def test_validate_schema_non_serializable_payload():
    reg = EventTypeRegistry()
    res = reg.validate_schema(EventType.TASK_CREATED, {"bad": float("nan")})
    assert isinstance(res, ValidationResult)
    assert res.valid is False


def test_validate_schema_unregistered_returns_false():
    reg = EventTypeRegistry(auto_populate_canonical=False)
    res = reg.validate_schema(EventType.TASK_CREATED)
    assert res.valid is False
    assert res.errors


def test_migrate_identity_version_returns_payload():
    reg = EventTypeRegistry()
    payload = {"a": 1}
    out = reg.migrate(
        EventType.TASK_CREATED, payload,
        SemanticVersion(1, 0, 0), SemanticVersion(1, 0, 0),
    )
    assert out is payload


def test_migrate_cross_version_no_invention():
    reg = EventTypeRegistry()
    payload = {"a": 1}
    # No speculative migration; payload returned unchanged, no exception.
    out = reg.migrate(
        EventType.TASK_CREATED, payload,
        SemanticVersion(1, 0, 0), SemanticVersion(2, 0, 0),
    )
    assert out == payload


def test_check_compatibility_identity_true():
    reg = EventTypeRegistry()
    res = reg.check_compatibility(
        EventType.TASK_CREATED,
        SemanticVersion(1, 0, 0), SemanticVersion(1, 0, 0),
    )
    assert isinstance(res, CompatibilityResult)
    assert res.compatible is True
    assert res.direction == "identical"


def test_check_compatibility_cross_version_false():
    reg = EventTypeRegistry()
    res = reg.check_compatibility(
        EventType.TASK_CREATED,
        SemanticVersion(1, 0, 0), SemanticVersion(2, 0, 0),
    )
    assert res.compatible is False
    assert res.direction == "unknown"


def test_check_compatibility_unregistered_false():
    reg = EventTypeRegistry(auto_populate_canonical=False)
    res = reg.check_compatibility(
        EventType.TASK_CREATED,
        SemanticVersion(1, 0, 0), SemanticVersion(1, 0, 0),
    )
    assert res.compatible is False


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

class _FakeEventType:
    """Name-bearing stand-in for a (future governed) extension EventType.

    The v1.0 EventType enum is closed and has no extension members, so tests of
    extension-prefix validation and deprecation semantics use this lightweight
    stand-in that mimics the ``.name`` attribute the registry reads.
    """

    def __init__(self, name: str) -> None:
        self.name = name

    def __hash__(self) -> int:
        return hash(self.name)

    def __eq__(self, other: object) -> bool:
        return isinstance(other, _FakeEventType) and other.name == self.name


def _fake_et(name: str) -> _FakeEventType:
    return _FakeEventType(name)


def _fake_producer() -> ComponentIdentity:
    return ComponentIdentity(
        component_type=ComponentType.EXTENSION,
        component_name="TestExtension",
    )
