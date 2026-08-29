"""M8-T7 DEF-01 remediation — pre-fix reproduction of the stock-boot MCP transport defect.

QA EVIDENCE ONLY — not part of the test suite. Read-only with respect to production code.
Run:  python architecture/Part15/M8/evidence/m8_t7_def01_repro.py
"""

from __future__ import annotations

import asyncio
import json
import sys
import tempfile
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[3]
sys.path.insert(0, str(REPO_ROOT))

from aios.core.mcp_manager import MCPManager, MCPServerConfig, MCPTransport  # noqa: E402
from aios.core.security_manager import get_security_manager  # noqa: E402

FAILURES: list[str] = []


def check(label: str, ok: bool, detail: str) -> None:
    mark = "PASS" if ok else "FAIL"
    print(f"[{mark}] {label}: {detail}")
    if not ok:
        FAILURES.append(label)


print("=== REPRO 1: stock JSON -> MCPServerConfig.transport type ===")
with tempfile.TemporaryDirectory(prefix="m8t7_def01_") as tmp:
    tmp_path = Path(tmp)
    # Exact representation used by config/mcp/*.json in this repository.
    (tmp_path / "probe.json").write_text(json.dumps({
        "server_id": "probe",
        "name": "Probe",
        "transport": "stdio",
        "command": ["python", "-c", "print('x')"],
        "url": None,
        "env": {},
        "headers": {},
        "timeout_seconds": 30,
        "auto_reconnect": True,
        "max_retries": 3,
        "metadata": {"description": "probe"},
    }))
    mgr = MCPManager(tmp_path)
    cfg = mgr._servers.get("probe")
    if cfg is None:
        check("R1 load", False, "config failed to load (loader swallowed an error)")
        raise SystemExit(1)
    print(f"       transport repr={cfg.transport!r} type={type(cfg.transport).__name__}")
    is_enum = isinstance(cfg.transport, MCPTransport)
    check("R1 JSON 'stdio' -> MCPTransport.STDIO", is_enum and cfg.transport == MCPTransport.STDIO,
          f"got {type(cfg.transport).__name__}")
    try:
        v = cfg.transport.value  # type: ignore[union-attr]
        check("R1 .value access", True, f"OK ({v!r})")
    except AttributeError as e:
        check("R1 .value access", False, f"AttributeError: {e}")

print()
print("=== REPRO 2: security gate on string-transport vs enum-transport config ===")
from aios.core.kernel import HermesKernel, KernelConfig  # noqa: E402


async def _boot_kernel() -> HermesKernel:
    kernel = HermesKernel(config=KernelConfig(data_dir=Path(tempfile.mkdtemp(prefix="m8t7_def01_kernel_"))))
    await kernel.start()  # boots canonical EventBus + SecurityManager (stock path)
    return kernel


kernel = asyncio.run(_boot_kernel())
sm = get_security_manager()

cfg_str = MCPServerConfig(server_id="s", name="S", transport="stdio")  # type: ignore[arg-type]
cfg_enum = MCPServerConfig(
    server_id="s", name="S", transport=MCPTransport.STDIO, command=["python", "-c", "pass"]
)
try:
    sm.validate_mcp_server_before_connect(cfg_str)
    check("R2 gate on string-transport config", True, "no crash")
except AttributeError as e:
    check("R2 gate on string-transport config", False, f"AttributeError: {e} (the DEF-01 crash)")
except Exception as e:
    check("R2 gate on string-transport config", False, f"{type(e).__name__}: {e}")

try:
    sm.validate_mcp_server_before_connect(cfg_enum)
    check("R2 gate on enum config", True, "no crash")
except AttributeError as e:
    check("R2 gate on enum config", False, f"AttributeError: {e}")
except Exception as e:
    check("R2 gate on enum config", True, f"non-crash outcome: {type(e).__name__}: {e}")

print()
print("=== REPRO 3: full connect() through the production chain ===")


async def _connect_probe() -> None:
    with tempfile.TemporaryDirectory(prefix="m8t7_def01_conn_") as tmp:
        cfg_dir = Path(tmp) / "config" / "mcp"
        cfg_dir.mkdir(parents=True)
        # Real in-repo MCP mock server (same module the integration harness uses),
        # launched exactly as a stock JSON config would specify it.
        (cfg_dir / "probe_conn.json").write_text(json.dumps({
            "server_id": "probe_conn",
            "name": "ProbeConn",
            "transport": "stdio",
            "command": [sys.executable, "-m", "aios.adapters.mock_graphify_server"],
            "url": None,
            "env": {},
            "headers": {},
            "timeout_seconds": 15,
            "auto_reconnect": True,
            "max_retries": 3,
            "metadata": {},
        }))
        mgr = MCPManager(cfg_dir)
        try:
            connected = await asyncio.wait_for(mgr.connect("probe_conn"), timeout=30)
            status = mgr._status["probe_conn"]
            check("R3 connect() via stock JSON", bool(connected),
                  f"connected={connected}, last_error={status.last_error!r}")
        except AttributeError as e:
            check("R3 connect() via stock JSON", False, f"AttributeError: {e} (DEF-01)")
        except asyncio.TimeoutError:
            check("R3 connect() via stock JSON", False, "timeout — possible hang variant of DEF-01")
        except Exception as e:
            check("R3 connect() via stock JSON", False, f"{type(e).__name__}: {e}")
        finally:
            try:
                await mgr.disconnect_all()
            except Exception:
                pass


asyncio.run(_connect_probe())

print()
if FAILURES:
    print(f"PRE-FIX REPRODUCTION RESULT: {len(FAILURES)} failing probe(s): {', '.join(FAILURES)}")
    print("This matches DEF-01 as reported by M8_T7_INDEPENDENT_QA_REPORT.md.")
else:
    print("PRE-FIX REPRODUCTION RESULT: all probes passed — DEF-01 NOT reproduced.")
