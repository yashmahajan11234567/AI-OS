#!/usr/bin/env python3
import asyncio
import tempfile
import shutil
from pathlib import Path
from uuid import uuid4

from aios.core import HermesKernel, KernelConfig
from aios.core.kernel_management import run_kernel, stop_kernel, create_kernel
from aios.events.core.bus import get_core_event_bus, reset_event_bus_singleton
from aios.events.core.types import EventType
from aios.events.core.manager import SubscribeOptions
from aios.events.core.identity import ComponentIdentity, ComponentType
from aios.events.core.types import SemanticVersion
from aios.events.core.event import Event as CoreEvent
from aios.events.core.payload import EventPayload
from aios.events.core.priority import EventPriority
from aios.events.core.category import category_for_event_type

async def test_event_system():
    print("DEBUG: Starting test")

    # Reset singletons
    reset_event_bus_singleton()

    # Create kernel
    temp_dir = Path(tempfile.mkdtemp())
    print(f"DEBUG: Using temp dir: {temp_dir}")
    config = KernelConfig(data_dir=temp_dir)

    kernel = await run_kernel(config)
    print(f"DEBUG: Kernel created and started: {kernel._running}")

    try:
        # Get event bus
        event_bus = get_core_event_bus()
        print(f"DEBUG: Event bus: {event_bus}")

        # Set up event tracking
        captured_events = []

        async def capture_event(event):
            print(f"DEBUG: Captured event: {event.eventType}")
            captured_events.append({
                "eventType": event.eventType,
                "source": event.source.component_name if event.source else None,
                "correlationId": str(event.correlationId) if event.correlationId else None,
                "payload": dict(event.payload) if event.payload else {},
            })

        # Subscribe to all events
        event_bus.subscribe(SubscribeOptions(
            subscriber=ComponentIdentity(
                component_type=ComponentType.ENGINEERING_SERVICE,
                component_name="test_tracker",
                version=SemanticVersion.parse("1.0.0"),
            ),
            event_types=list(EventType),
            handler=capture_event,
            priority=EventPriority.NORMAL,
        ))
        print("DEBUG: Subscribed to events")

        # Emit a test event
        test_event = CoreEvent(
            eventType=EventType.WORKFLOW_STARTED,
            source=ComponentIdentity(
                component_type=ComponentType.ENGINEERING_SERVICE,
                component_name="test",
                version=SemanticVersion.parse("1.0.0"),
            ),
            correlationId=uuid4(),
            payload=EventPayload({
                "task_id": "test_task",
                "goal": "test goal",
            }),
            priority=EventPriority.NORMAL,
            category=category_for_event_type(EventType.WORKFLOW_STARTED),
        )

        print("DEBUG: Publishing test event")
        result = event_bus.publish(test_event)
        print(f"DEBUG: Publish result: {result}")

        # Drain the event bus
        print("DEBUG: Draining event bus")
        await event_bus.drain()
        print(f"DEBUG: Captured {len(captured_events)} events")

        for i, evt in enumerate(captured_events):
            print(f"DEBUG: Event {i}: {evt['eventType']}")

    finally:
        await kernel.stop()
        await stop_kernel()
        shutil.rmtree(temp_dir, ignore_errors=True)

if __name__ == "__main__":
    asyncio.run(test_event_system())