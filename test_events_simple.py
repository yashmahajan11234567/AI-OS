print("DEBUG: Starting events test")

import asyncio
import tempfile
import shutil
from pathlib import Path
from uuid import uuid4

try:
    from aios.core import HermesKernel, KernelConfig
    from aios.core.kernel_management import run_kernel, stop_kernel
    from aios.events.core.bus import get_core_event_bus, reset_event_bus_singleton
    from aios.events.core.types import EventType
    from aios.events.core.manager import SubscribeOptions
    from aios.events.core.subscription import HandlerPriority
    from aios.events.core.identity import ComponentIdentity, ComponentType
    from aios.events.core.types import SemanticVersion
    from aios.events.core.event import Event as CoreEvent
    from aios.events.core.payload import EventPayload
    from aios.events.core.priority import EventPriority
    from aios.events.core.category import category_for_event_type

    print("DEBUG: Imports successful")
except Exception as e:
    print(f"DEBUG: Import error: {e}")
    import traceback
    traceback.print_exc()
    exit(1)

async def test_event_system():
    print("DEBUG: Starting event system test")

    try:
        # Reset singletons
        print("DEBUG: Resetting event bus singleton")
        reset_event_bus_singleton()
        print("DEBUG: Event bus singleton reset")

        # Create kernel
        temp_dir = Path(tempfile.mkdtemp())
        print(f"DEBUG: Using temp dir: {temp_dir}")
        config = KernelConfig(data_dir=temp_dir)
        print("DEBUG: Kernel config created")

        print("DEBUG: About to run kernel")
        kernel = await run_kernel(config)
        print(f"DEBUG: Kernel created and started: {kernel._running}")

        try:
            # Get event bus
            print("DEBUG: Getting core event bus")
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
            print("DEBUG: Creating subscriber identity")
            subscriber_id = ComponentIdentity(
                component_type=ComponentType.ENGINEERING_SERVICE,
                component_name="test_tracker",
                version=SemanticVersion.parse("1.0.0"),
            )
            print(f"DEBUG: Subscriber ID: {subscriber_id}")

            print("DEBUG: Creating subscribe options")
            options = SubscribeOptions(
                subscriber=subscriber_id,
                event_types=list(EventType),
                handler=capture_event,
                priority=HandlerPriority.NORMAL,
            )
            print(f"DEBUG: Subscribe options: {options}")

            print("DEBUG: Subscribing to events")
            event_bus.subscribe(options)
            print("DEBUG: Subscribed to events")

            # Emit a test event
            print("DEBUG: Creating test event")
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
            print(f"DEBUG: Test event created: {test_event.eventType}")

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
            print("DEBUG: Stopping kernel")
            await kernel.stop()
            await stop_kernel()
            print("DEBUG: Kernel stopped")
            shutil.rmtree(temp_dir, ignore_errors=True)
            print("DEBUG: Temp dir cleaned up")

    except Exception as e:
        print(f"DEBUG: Error in test: {e}")
        import traceback
        traceback.print_exc()

if __name__ == "__main__":
    print("DEBUG: About to run asyncio")
    asyncio.run(test_event_system())
    print("DEBUG: Test completed")