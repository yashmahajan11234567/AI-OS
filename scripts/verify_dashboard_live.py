"""Live HTTP verification for M10-T6 dashboard remediation.

Replicates Terminal 3's live verification:
  - start DashboardHTTPServer with real EventBus + DashboardService
  - publish canonical events (KERNEL_READY, SECURITY_ISSUE_FOUND)
  - request GET /api/pages
  - assert recent_events non-empty, correct event visible, security event filtered
"""
from __future__ import annotations

import asyncio
import json
import threading
import time
import urllib.request
import urllib.error

from aios.core.health_manager import (
    HealthManager,
    reset_health_manager_singleton,
    set_health_manager,
)
from aios.core.observability_manager import (
    ObservabilityManager,
    reset_observability_manager_singleton,
    set_observability_manager,
)
from aios.events.core.bus import (
    EventBus,
    EventBusConfig,
    reset_event_bus_singleton,
)
from aios.events.core.event import Event
from aios.events.core.identity import ComponentIdentity, ComponentType
from aios.events.core.types import EventType, SemanticVersion
from aios.services.dashboard_server import DashboardHTTPServer
from aios.services.dashboard_service import DashboardService


def _make_identity(component_name: str = "test_service") -> ComponentIdentity:
    return ComponentIdentity(
        component_type=ComponentType.ENGINEERING_SERVICE,
        component_name=component_name,
        version=SemanticVersion(1, 0, 0),
    )


def main() -> None:
    # 1. Reset singletons
    reset_event_bus_singleton()
    reset_observability_manager_singleton()
    reset_health_manager_singleton()

    # 2. Initialize real EventBus
    bus = EventBus(config=EventBusConfig(auto_start_dispatch_worker=False))
    asyncio.run(bus.initialize())

    # 3. Initialize real ObservabilityManager + HealthManager
    om = ObservabilityManager(service_registry=None, configuration_manager=None, logger=None)
    asyncio.run(om.initialize())
    set_observability_manager(om)

    hm = HealthManager(service_registry=None, configuration_manager=None, logger=None)
    asyncio.run(hm.initialize())
    set_health_manager(hm)

    # 4. Create real DashboardService wired to the real bus
    kernel = None  # no kernel needed for observability/events
    svc = DashboardService(kernel=kernel, event_bus=bus, security_manager=None)

    # 5. Start real DashboardHTTPServer
    server = DashboardHTTPServer(
        dashboard_service=svc,
        kernel=None,
        host="localhost",
        port=19080,
    )
    server.start()

    # 6. Publish canonical events
    identity = _make_identity("verification_service")
    normal_event = Event(
        eventType=EventType.KERNEL_READY,
        source=identity,
        payload={"test": "live_verification"},
    )
    security_event = Event(
        eventType=EventType.SECURITY_ISSUE_FOUND,
        source=identity,
        payload={"violation": "test violation", "severity": "HIGH"},
    )
    asyncio.run(bus.publish(normal_event))
    asyncio.run(bus.publish(security_event))

    time.sleep(0.5)

    try:
        # 7. GET /api/pages
        req = urllib.request.Request("http://localhost:19080/api/pages")
        with urllib.request.urlopen(req, timeout=5) as resp:
            assert resp.status == 200, f"Expected 200, got {resp.status}"
            data = json.loads(resp.read().decode("utf-8"))

        obs = data["pages"]["system_observability"]
        recent = obs["recent_events"]

        # 8. Verify recent_events is non-empty
        assert recent, "recent_events must be non-empty after publishing events"

        # 9. Verify normal event observed
        types = [e["event_type"] for e in recent]
        assert "KERNEL_READY" in types, "KERNEL_READY must appear in recent_events"

        # 10. Verify SECURITY_ISSUE_FOUND is filtered
        assert "SECURITY_ISSUE_FOUND" not in types, "SECURITY_ISSUE_FOUND must be filtered from recent_events"

        # 11. Verify timestamp is correctly serialized
        kr = next(e for e in recent if e["event_type"] == "KERNEL_READY")
        assert isinstance(kr["timestamp"], str)
        assert kr["timestamp"] != "unknown"
        assert "T" in kr["timestamp"] and "Z" in kr["timestamp"]

        print(json.dumps({
            "http_status": resp.status,
            "page_count": len(data["pages"]),
            "recent_events_count": len(recent),
            "normal_event_observed": True,
            "security_event_filtered": True,
            "exception": None,
            "timestamp_sample": kr["timestamp"],
        }, indent=2))
        return 0

    except Exception as exc:
        print(json.dumps({
            "http_status": None,
            "page_count": None,
            "recent_events_count": None,
            "normal_event_observed": False,
            "security_event_filtered": False,
            "exception": str(exc),
            "timestamp_sample": None,
        }, indent=2))
        raise

    finally:
        server.stop()


if __name__ == "__main__":
    raise SystemExit(main())
