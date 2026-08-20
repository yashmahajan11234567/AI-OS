# Task 9 Migration Map — Split-Brain Resolution

**Status:** PHASE 3 — Migration Map Complete
**QA Verdict:** Previous "migration midpoint" REJECTED — dual instances violate singleton invariants
**Goal:** Exactly ONE EventBus authority and ONE ServiceRegistry authority per process

---

## 1. Current Split-Brain Architecture (Rejected)

| Component | Kernel Holds | Canonical Stack (C1/C2/C3/C4/LM) Holds | Instance Count |
|-----------|--------------|----------------------------------------|----------------|
| **EventBus** | `self._event_bus` = `aios.events.bus.EventBus` (legacy, 337 lines, pub/sub, history, stats) | `core_bus` = `aios.events.core.bus.EventBus` (canonical, 1127 lines, Task 5, INV-EB-001) | **2** ❌ |
| **ServiceRegistry** | `self._service_registry` = `aios.services.registry.ServiceRegistry` (legacy, 191 lines, engineering services lifecycle) | `core_sr` = `aios.core.service_registry.ServiceRegistry` (canonical, 1230 lines, Task 6, INV-SR-STR-001) | **2** ❌ |
| **ConfigurationManager** | `self._configuration` = canonical only | Same instance (get_configuration_manager) | 1 ✅ |
| **StructuredLogger** | `self._structured_logger` = canonical only | Same instance (get_logger) | 1 ✅ |
| **LifecycleManager** | `self._lifecycle` = canonical only | Same instance (get_lifecycle_manager) | 1 ✅ |

### Kernel Methods Depending on Split-Brain Objects

| Kernel Method | Current Depends On | Legacy API Used | Canonical Replacement | Compatibility Concern | Proposed Minimal Change |
|---------------|-------------------|-----------------|----------------------|----------------------|------------------------|
| `event_bus` property | `self._event_bus` (legacy) | — | Canonical `CoreEventBus` | External code accesses `kernel.event_bus` | Make `kernel.event_bus` return canonical, add legacy compat methods to canonical |
| `service_registry` property | `self._service_registry` (legacy) | — | Canonical `ServiceRegistry` | External code accesses `kernel.service_registry` | Make `kernel.service_registry` return canonical, add legacy compat methods to canonical |
| `register_service()` | `self._service_registry.register()` | `service.name`, returns service | `canonical_sr.register()` | Legacy expects `BaseService` with `.name` | Canonical `register()` accepts duck-typed service with `name` attr |
| `get_service(name)` | `self._service_registry.get()` | Returns `BaseService` | `canonical_sr.get_registration(name)` | Returns different type | Add `get(name)` alias to canonical `ServiceRegistration.service` |
| `stop()` → `_shutdown_structured_logger()` | `self._event_bus.shutdown()` | Legacy `shutdown()` | Canonical has `shutdown()` ✅ | Different signature (legacy sync, canonical async) | Canonical `shutdown()` is async — await it |
| `stop()` → `_stop_event_bus()` | `self._event_bus.shutdown()` | Legacy sync `shutdown()` | Canonical async `shutdown()` | Must await | `await canonical_bus.shutdown()` |
| `get_stats()` | `self._event_bus.get_stats()` | Returns dict with `total_events_published`, `active_subscriptions`, etc. | Canonical has `get_stats()` ✅ | Different fields | Add legacy-compat fields to canonical `get_stats()` |
| `get_stats()` | `self._service_registry.get_stats()` | Legacy returns `total`, `running`, `services` | Canonical has `get_stats()` ✅ | Different fields | Add legacy-compat fields to canonical `get_stats()` |
| `_start_services()` → `service_registry.start_all()` | Legacy `start_all()` | Starts `BaseService` instances | Canonical doesn't manage engineering services | **Architecture boundary** — canonical C2 is for Core services only | Keep legacy registry for engineering services ONLY; don't merge |
| `_stop_services()` → `service_registry.stop_all()` | Legacy `stop_all()` | Stops `BaseService` instances | Canonical doesn't manage engineering services | **Architecture boundary** | Same as above |

---

## 2. Target Architecture (Required)

| Authority | Single Instance | Singleton Invariant |
|-----------|-----------------|---------------------|
| **EventBus** | `aios.events.core.bus.CoreEventBus` (Task 5) | INV-EB-001: Exactly one per process |
| **ServiceRegistry (C2)** | `aios.core.service_registry.ServiceRegistry` (Task 6) | INV-SR-STR-001: Exactly one per process |
| **ConfigurationManager (C3)** | `aios.core.configuration_manager.ConfigurationManager` (Task 7) | Already single |
| **StructuredLogger (C4)** | `aios.core.structured_logger.StructuredLogger` (Task 8) | Already single |
| **LifecycleManager** | `aios.core.lifecycle_manager.LifecycleManager` (Task 9) | Already single |

### Canonical Stack Wiring (Must Be Identical)

```
Kernel creates:
  1. CoreEventBus (canonical C1) → set as global singleton for canonical stack
  2. Core ServiceRegistry (canonical C2) wired to canonical C1
  3. ConfigurationManager (C3) wired to canonical C1
  4. StructuredLogger (C4) wired to canonical C1 + canonical C2 (lazy) + C3
  5. LifecycleManager (LM) wired to canonical C1 + canonical C2 + C3 + C4

Kernel ALSO creates (for engineering services):
  - Legacy EventBus (aios.events.bus.EventBus) — ONLY for KernelStarted/KernelStopped events
  - Legacy ServiceRegistry (aios.services.registry.ServiceRegistry) — ONLY for engineering services lifecycle

KEY: Kernel.properties event_bus and service_registry MUST return canonical instances
```

---

## 3. Minimal Compatibility Surface (Add to Canonical Implementations)

### Canonical EventBus (`src/aios/events/core/bus.py`) — Add:

```python
# Legacy-compatibility methods (non-breaking, additive)

def get_history(
    self,
    event_type: str | None = None,
    correlation_id: str | None = None,
    limit: int = 100,
) -> list[Event]:
    """Legacy-compatible event history accessor."""
    # Canonical uses getRecentEvents(limit) + filter by eventType
    events = self.getRecentEvents(limit=limit)
    if event_type:
        # Handle both EventType enum and string
        target = event_type.value if hasattr(event_type, 'value') else event_type
        events = [e for e in events if e.eventType == target]
    if correlation_id:
        events = [e for e in events if e.correlationId == correlation_id]
    return events

def get_stats(self) -> dict[str, Any]:
    """Legacy-compatible statistics (merge with existing get_stats)."""
    base = self.get_stats()  # Existing canonical stats
    base.update({
        "total_events_published": base.get("total_published", 0),
        "active_subscriptions": base.get("subscription_count", 0),
        "history_size": len(self._history),
        "max_history": getattr(self._config, "max_history", 10000),
    })
    return base

# Note: shutdown() already exists as async — kernel must await it
```

### Canonical ServiceRegistry (`src/aios/core/service_registry.py`) — Add:

```python
# Legacy-compatibility methods for kernel integration

def register(self, service: BaseService) -> BaseService:
    """
    Legacy-compatible register accepting BaseService (engineering service).
    
    Delegates to canonical register() with service_id=service.name,
    service_type=ServiceType.ENGINEERING, and extracts capabilities/depends_on.
    """
    return asyncio.run(self._register_legacy(service))

async def _register_legacy(self, service: BaseService) -> BaseService:
    service_id = getattr(service, "name", None)
    if not service_id:
        raise ValueError("BaseService must have a 'name' attribute")
    
    depends_on = getattr(service, "depends_on", [])
    capabilities = []  # Could extract from service if needed
    
    reg = await self.register(
        service=service,
        service_id=service_id,
        service_type=ServiceType.ENGINEERING,
        depends_on=depends_on,
        capabilities=capabilities,
    )
    return reg.service  # Return the original service instance

def get(self, name: str) -> Any:
    """Legacy-compatible get returning the service instance."""
    reg = self.get_registration(name)
    if reg is None:
        raise ServiceNotFoundError(name)
    return reg.service

def get_stats(self) -> dict[str, Any]:
    """Legacy-compatible statistics."""
    base = self.get_stats()  # Existing canonical stats
    base.update({
        "total": base.get("total_services", 0),
        "running": base.get("running_services", 0),
        "services": {
            sid: {"name": r.service_id, "status": r.lifecycle_state.value}
            for sid, r in self._registrations.items()
        },
    })
    return base

# Note: start_all/stop_all/health_check are ENGINEERING SERVICE methods
# — Canonical C2 does NOT implement these (architecture boundary)
# — Kernel MUST continue using legacy registry for engineering services
```

---

## 4. Kernel Changes Required

### File: `src/aios/core/kernel.py`

| Change | Location | Description |
|--------|----------|-------------|
| **1.** | Imports | Remove legacy `EventBus`, `get_event_bus`, `set_event_bus`; import canonical `CoreEventBus` directly |
| **2.** | Imports | Remove legacy `ServiceRegistry`, `get_service_registry`, `set_service_registry`; import canonical `get_core_service_registry` directly |
| **3.** | `_init_core_components()` | Create `CoreEventBus` as `self._event_bus` (not legacy). Call `await core_bus.initialize()` before setting as global. |
| **4.** | `_init_core_components()` | Create `Core ServiceRegistry` as `self._service_registry` (not legacy). Wire to canonical `core_bus`. |
| **5.** | `_init_service_registry()` | **DELETE** — legacy registry creation moved to separate engineering-only init |
| **6.** | New method `_init_engineering_services()` | Create legacy `EventBus` and legacy `ServiceRegistry` ONLY for engineering services |
| **7.** | `stop()` → `_shutdown_structured_logger()` | `await self._event_bus.shutdown()` (canonical is async) |
| **8.** | `stop()` → delete `_stop_event_bus()` | Canonical bus shutdown handled in structured logger shutdown or new method |
| **9.** | `get_stats()` | Update to use canonical `get_stats()` (now legacy-compatible) |
| **10.** | Properties | `event_bus` and `service_registry` properties return canonical instances |

---

## 5. Test Assertions to Update

| Test File | Current Test | Expected After Migration |
|-----------|--------------|--------------------------|
| `tests/integration/test_lifecycle_manager_phase.py` | `assert integrated._event_bus is core_stack["bus"]` | PASSES (both canonical) |
| `tests/integration/test_lifecycle_manager_phase.py` | `assert integrated._service_registry is core_stack["service_registry"]` | PASSES (both canonical) |
| `tests/integration/test_structured_logger_phase.py` | `assert kernel.logger._event_bus is kernel.event_bus` | Kernel.event_bus = canonical; passes |
| `tests/unit/test_event_bus.py` | Tests canonical EventBus | No change |
| `tests/unit/test_service_registry.py` | Tests canonical ServiceRegistry | No change |
| Any test accessing `kernel.event_bus.get_history()` | Works (legacy) | Works (canonical with compat) |
| Any test accessing `kernel.event_bus.get_stats()` | Works (legacy) | Works (canonical with compat) |
| Any test accessing `kernel.service_registry.start_all()` | Works (legacy) | **FAIL** — canonical C2 has no `start_all` → keep legacy for engineering |

---

## 6. Stop Conditions (QA Acceptance)

- [ ] `kernel.event_bus is get_event_bus()` returns **canonical** EventBus (identity check)
- [ ] `kernel.service_registry is get_core_service_registry()` returns **canonical** ServiceRegistry (identity check)
- [ ] LifecycleManager uses same canonical instances (test: `test_uses_existing_eventbus`, `test_uses_existing_service_registry`)
- [ ] StructuredLogger receives canonical EventBus (test: `test_event_bus_initialized_before_logger`)
- [ ] All Task 1-8 tests pass (regression guard)
- [ ] No process contains two `CoreEventBus` instances (INV-EB-001)
- [ ] No process contains two canonical `ServiceRegistry` instances (INV-SR-STR-001)
- [ ] Engineering services still start/stop via legacy registry (`start_all`/`stop_all` preserved)

---

## 7. Dependency Graph

```
BEFORE (Split-Brain):
┌─────────────────────────────────────────────────────────────────┐
│ Kernel                                                          │
│  ├─ _event_bus ──────────→ Legacy EventBus (bus.py)            │
│  ├─ _service_registry ──→ Legacy ServiceRegistry (services)    │
│  ├─ _configuration ────→ Canonical C3                          │
│  ├─ _structured_logger ─→ Canonical C4                         │
│  └─ _lifecycle ─────────→ Canonical LM                         │
│                                                                  │
│ Canonical Stack (C1/C2/LM):                                     │
│  ├─ core_bus ────────────→ Canonical EventBus (core/bus.py)    │
│  ├─ core_sr ─────────────→ Canonical ServiceRegistry (core)    │
│  └─ lifecycle ───────────→ Canonical LM                        │
└─────────────────────────────────────────────────────────────────┘

AFTER (Single Authority):
┌─────────────────────────────────────────────────────────────────┐
│ Kernel                                                          │
│  ├─ _event_bus ──────────→ Canonical CoreEventBus (C1)         │  ← KERNEL PROPERTY
│  ├─ _service_registry ──→ Canonical ServiceRegistry (C2)       │  ← KERNEL PROPERTY
│  ├─ _configuration ────→ Canonical C3                          │
│  ├─ _structured_logger ─→ Canonical C4                         │
│  ├─ _lifecycle ─────────→ Canonical LM                         │
│  └─ _engineering_services:                                      │
│        ├─ _legacy_bus ─────→ Legacy EventBus (bus.py)          │  ← INTERNAL ONLY
│        └─ _legacy_sr ──────→ Legacy ServiceRegistry (services) │  ← INTERNAL ONLY
└─────────────────────────────────────────────────────────────────┘
```

---

## 8. Implementation Order

1. **Add compatibility methods** to canonical EventBus (`get_history`, `get_stats` with legacy fields)
2. **Add compatibility methods** to canonical ServiceRegistry (`register`, `get`, `get_stats` with legacy fields)
3. **Rewrite `kernel.py`** — wire canonical instances to kernel properties, create legacy instances for engineering only
4. **Update tests** that assert on split-brain behavior (remove dual-instance assertions)
5. **Run all test suites** — ensure zero regressions
6. **Runtime verification** — assert identity checks in test setup

---

**Next:** Phase 4 — Implement minimal migration in `kernel.py` and canonical files