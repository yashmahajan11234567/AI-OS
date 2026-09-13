#!/usr/bin/env python3
"""QA verification: prove child process lifecycle."""
import asyncio, os, tempfile, textwrap, sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent / "src"))

from aios.adapters.acp_adapter import AcPAdapter
from aios.events.core.bus import EventBus, set_event_bus
import aios.events.core.bus as busmod

# Enable debug logging to capture AcPAdapter's _read_stderr child output
import logging
logging.basicConfig(level=logging.DEBUG, format="ACPD_LOG: %(message)s")

busmod._INSTANCE = None
set_event_bus(EventBus())

async def main():
    with tempfile.TemporaryDirectory(prefix="acp_test_") as tmp:
        tmp_path = Path(tmp)
        acp_dir = tmp_path / "acp_adapter"
        acp_dir.mkdir()
        (acp_dir / "__init__.py").touch()

        src_abs = str(Path(__file__).parent / "src")
        entry_code = textwrap.dedent(f'''
import asyncio, json, sys, threading
def dbg(msg): print(msg, file=sys.stderr, flush=True)
_SRC = r"{src_abs}"
if _SRC not in sys.path: sys.path.insert(0, _SRC)
from aios.adapters.mock_hermes_acp_server import MockACPServer
def run_server(loop):
    dbg("child: creating server")
    server = MockACPServer()
    asyncio.set_event_loop(loop)
    dbg("child: entering stdin loop")
    for raw_line in sys.stdin.buffer:
        line = raw_line.decode().strip()
        if not line: continue
        try:
            request = json.loads(line)
            future = asyncio.run_coroutine_threadsafe(server.handle_request(request), loop)
            response = future.result(timeout=30)
            if response is not None:
                sys.stdout.write(json.dumps(response) + "\\n")
                sys.stdout.flush()
                dbg("child: wrote response")
        except json.JSONDecodeError: continue
        except Exception as exc: dbg(f"child: error: {{exc}}")
loop = asyncio.new_event_loop()
thread = threading.Thread(target=run_server, args=(loop,), daemon=True)
thread.start()
try: loop.run_forever()
except KeyboardInterrupt: pass
finally:
    loop.call_soon_threadsafe(loop.stop)
    thread.join(timeout=2)
dbg("child: exiting")
''')
        (acp_dir / "entry.py").write_text(entry_code)

        adapter = AcPAdapter(cwd=str(tmp_path), timeout_seconds=30)
        try:
            connected = await adapter.connect()
            child_pid = adapter._process.pid
            parent_pid = os.getpid()
            print(f"VERIFY: connect() = {connected}")
            print(f"VERIFY: child_pid = {child_pid}, parent_pid = {parent_pid}")
            print(f"VERIFY: PIDs differ = {child_pid != parent_pid}")

            session_id = await adapter.new_session(cwd=str(tmp_path))
            print(f"VERIFY: new_session() returned ID length = {len(session_id)}")

            prompt_result = await adapter.prompt(session_id, "Navigate to https://example.com", timeout=20)
            print(f"VERIFY: prompt() stopReason = {prompt_result.get('stopReason')}")
            print(f"VERIFY: prompt() text sample = {prompt_result.get('text', '')[:50]}")
            print(f"VERIFY: prompt() has sessionId = {'sessionId' in prompt_result}")

            await adapter.cancel(session_id)
            print("VERIFY: cancel() completed")
            await adapter.close_session(session_id)
            print("VERIFY: close_session() completed")
        finally:
            await adapter.disconnect()
            print("VERIFY: disconnect() completed")

asyncio.run(main())