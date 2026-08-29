"""M8-T7 Terminal 2 — minimal repro: JSON-loaded transport crashes security gate.

QA EVIDENCE ONLY — not part of the test suite. Modifies nothing.
"""
import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parents[3]))

from aios.core.mcp_manager import MCPManager, MCPServerConfig, MCPTransport

print("=== REPRO 1: config-from-JSON type ===")
import tempfile, json as jsonlib
tmp = Path(tempfile.mkdtemp(prefix="m8t7_repro_"))
(tmp / "probe.json").write_text(jsonlib.dumps({
    "server_id": "probe", "name": "Probe", "transport": "stdio",
    "command": ["python", "-c", "print('x')"], "url": None,
    "env": {}, "headers": {}, "timeout_seconds": 30,
    "auto_reconnect": True, "max_retries": 3, "metadata": {},
}))
mgr = MCPManager(tmp)
cfg = mgr._servers["probe"]
print(f"config.transport repr = {cfg.transport!r}")
print(f"type                  = {type(cfg.transport).__name__}")
print(f"is MCPTransport enum? = {isinstance(cfg.transport, MCPTransport)}")
try:
    v = cfg.transport.value
    print(f".value access         = OK ({v!r})")
except AttributeError as e:
    print(f".value access         = CRASH: {e}")

print()
print("=== REPRO 2: programmatic add_server with proper enum ===")
cfg2 = MCPServerConfig(
    server_id="probe2", name="Probe2", transport=MCPTransport.STDIO,
    command=["python", "-c", "print('x')"],
)
print(f"type = {type(cfg2.transport).__name__}; .value = {cfg2.transport.value!r}")

print()
print("=== REPRO 3: does (str, Enum) comparison mask the difference? ===")
print(f"'stdio' == MCPTransport.STDIO -> {'stdio' == MCPTransport.STDIO}")
print(f"isinstance('stdio', MCPTransport) -> {isinstance('stdio', MCPTransport)}")

print()
print("=== REPRO 4: security gate on JSON-loaded config ===")
import asyncio
from aios.core.security_manager import get_security_manager

async def main():
    sm = get_security_manager()
    try:
        result = sm.validate_mcp_server_before_connect(cfg)
        print(f"gate(JSON cfg)   -> returned {result}")
    except AttributeError as e:
        print(f"gate(JSON cfg)   -> AttributeError CRASH: {e}")
    except Exception as e:
        print(f"gate(JSON cfg)   -> {type(e).__name__}: {e}")
    try:
        result = sm.validate_mcp_server_before_connect(cfg2)
        print(f"gate(enum cfg)   -> returned (no crash)")
    except Exception as e:
        print(f"gate(enum cfg)   -> {type(e).__name__}: {e}")

asyncio.run(main())
