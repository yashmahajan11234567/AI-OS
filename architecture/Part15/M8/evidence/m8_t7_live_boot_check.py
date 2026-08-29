"""M8-T7 Terminal 2 — IND-4 live-kernel-boot production-path verification (v2).

Boots the REAL kernel via run_kernel() (no fixture injection, no harness
workaround) and probes every production integration path INDEPENDENTLY,
capturing failures as evidence instead of aborting.

QA EVIDENCE ONLY — not part of the test suite. Modifies nothing.
"""

import asyncio
import json
import sys
import tempfile
import traceback
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[3]))

from aios.core.kernel_management import run_kernel, stop_kernel
from aios.core import KernelConfig

RESULTS = []  # (check, outcome, evidence)


def record(check: str, outcome: str, evidence: str) -> None:
    RESULTS.append((check, outcome, evidence))


async def probe(name: str, coro_factory, timeout: float):
    """Run one probe, converting any exception into recorded evidence."""
    try:
        detail = await asyncio.wait_for(coro_factory(), timeout=timeout)
        return detail
    except Exception as e:
        tb = traceback.format_exc().strip().splitlines()
        last_frames = [l.strip() for l in tb if l.strip().startswith("File ")][-3:]
        record(name, "CRASH",
               f"{type(e).__name__}: {e} | frames: {' <- '.join(last_frames)}")
        return None


async def main() -> int:
    tmp = Path(tempfile.mkdtemp(prefix="m8t7_boot_"))
    await stop_kernel()
    kernel = None
    try:
        kernel = await asyncio.wait_for(
            run_kernel(KernelConfig(data_dir=tmp / "data")),
            timeout=120,
        )

        # ---------------- D-01 wiring checks (no network needed) ----------
        mm = kernel.mcp_manager
        ok = mm is not None
        record("D-01a kernel.mcp_manager assigned after live boot",
               "PASS" if ok else "FAIL", f"type={type(mm).__name__}")
        from aios.core.mcp_manager import get_mcp_manager, MCPTransport
        record("D-01b kernel.mcp_manager is canonical singleton",
               "PASS" if mm is get_mcp_manager() else "FAIL", f"id={id(mm):#x}")

        adapters = {
            "graphify": kernel.graphify_adapter,
            "notion": kernel.notion_adapter,
            "obsidian": kernel.obsidian_adapter,
            "claude_mem": kernel.claude_mem_adapter,
            "playwright": kernel.playwright_adapter,
        }
        same = all(ad is not None and getattr(ad, "_mcp_manager", None) is mm
                   for ad in adapters.values())
        record("D-01c all 5 adapters hold SAME canonical MCPManager",
               "PASS" if same else "FAIL",
               "; ".join(f"{k}={'wired' if v and getattr(v,'_mcp_manager',None) is mm else 'NOT-WIRED'}"
                         for k, v in adapters.items()))

        usa = kernel.user_simulation_agent
        bridge = getattr(usa, "_bridge", None) if usa else None
        d02wired = bridge is not None and getattr(bridge, "_mcp_manager", None) is mm
        sig = [a for a in (dir(usa) if usa else []) + (dir(bridge) if bridge else [])
               if "_create_session_id" in a]
        record("D-02a UserSimulationAgent -> real bridge -> kernel MCPManager",
               "PASS" if d02wired and not sig else "FAIL",
               f"wired={d02wired} stale_markers={sig}")

        # Config-type forensics: what did the JSON loader actually store?
        gcfg = mm._servers.get("graphify")
        ttype = type(gcfg.transport).__name__ if gcfg else "?"
        try:
            _ = gcfg.transport.value
            tv = ".value OK"
        except AttributeError:
            tv = ".value CRASHES (AttributeError)"
        record("FORENSIC JSON-loaded config transport type",
               "EVIDENCE", f"graphify.transport is {ttype}; {tv}; "
                           f"isinstance-enum={isinstance(gcfg.transport, MCPTransport)}")

        # ---------------- live execution probes (Tier B subprocess path) --
        # Each probe goes through SecurityManager gate-before-connect with the
        # JSON-loaded (string transport) config — the true production path.

        sid_holder = {}

        async def hermes_session():
            sid = await bridge.create_worker_session(environment={"app_url": "https://example.com"})
            sid_holder["sid"] = sid
            return f"session={sid}"

        await probe("PROBE-HERMES create_worker_session (production MCP path)",
                    hermes_session, 60)

        async def graphify_flow():
            ga = adapters["graphify"]
            okc = await ga.connect()
            if not okc:
                raise RuntimeError("connect() returned False")
            r = await ga.store_node("m8t7_probe", "Probe", {"purpose": "boot-check"})
            prov = (r.raw or {}).get("provenance", {})
            return f"connected; store_node authority={prov.get('authority')!r} advisory={prov.get('advisory')!r}"

        await probe("PROBE-GRAPHIFY connect+store_node (production MCP path)",
                    graphify_flow, 60)

        async def notion_flow():
            na = adapters["notion"]
            okc = await na.connect()
            if not okc:
                raise RuntimeError("connect() returned False")
            r = await na.search_pages("*")
            return f"connected; search returned {len((r.raw or {}).get('pages', []))} pages"

        await probe("PROBE-NOTION connect+search_pages (production MCP path)",
                    notion_flow, 60)

        async def obsidian_flow():
            oa = adapters["obsidian"]
            okc = await oa.connect()
            if not okc:
                raise RuntimeError("connect() returned False")
            return "connected"

        await probe("PROBE-OBSIDIAN connect (production MCP path)",
                    obsidian_flow, 60)

        async def claude_mem_flow():
            ca = adapters["claude_mem"]
            okc = await ca.connect()
            if not okc:
                raise RuntimeError("connect() returned False")
            return "connected"

        await probe("PROBE-CLAUDE_MEM connect (production MCP path)",
                    claude_mem_flow, 60)

        # Cleanup whatever succeeded
        if sid_holder.get("sid"):
            try:
                await bridge.close_worker_session(sid_holder["sid"])
                record("CLEANUP hermes session closed", "PASS", sid_holder["sid"])
            except Exception as e:
                record("CLEANUP hermes session close", "FAIL", str(e))

    finally:
        try:
            await stop_kernel()
        except Exception:
            pass

    print("\n" + "=" * 100)
    print("M8-T7 LIVE BOOT VERIFICATION (v2, resilient) — RESULTS")
    print("=" * 100)
    fails = 0
    for check, outcome, ev in RESULTS:
        print(f"[{outcome:>10}] {check}\n             {ev[:400]}")
        if outcome in ("FAIL", "CRASH"):
            fails += 1
    print("=" * 100)
    print(f"RESULT: {fails} FAIL/CRASH outcomes")
    Path(__file__).with_suffix(".results.json").write_text(
        json.dumps([{"check": c, "outcome": o, "evidence": e} for c, o, e in RESULTS],
                   indent=2), encoding="utf-8")
    return 1 if fails else 0


if __name__ == "__main__":
    sys.exit(asyncio.run(main()))
