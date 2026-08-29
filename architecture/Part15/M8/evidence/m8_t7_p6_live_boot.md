# M8-T7 — P6 Checkpoint: Live-Kernel-Boot Production-Path Verification (IND-4)

**Terminal**: 2 · **Date**: 2026-08-26
**Method**: `run_kernel(KernelConfig(data_dir=<tmp>))` — real boot, NO fixture injection, NO harness workaround. Evidence scripts preserved at `evidence/m8_t7_live_boot_check.py` (+ `.results.json`) and `evidence/m8_t7_transport_repro.py`.

---

## DEF-01 (NEW, Terminal 2): Production MCP connection path crashes on ALL servers

### Severity: **P1 — NO-GO condition per spec §12**

Spec §12 lists as P0/P1 blockers: *"Broken production execution path"* and *"MCP/ACP transport fundamentally disconnected."* This defect is precisely that: with a stock boot, **no MCP server can ever be connected through the production path**, because the SecurityManager gate-before-connect (C18) crashes before any subprocess launches.

### Root cause (source-level, file:line)

1. `mcp_manager.py:126-139` `_load_configs()` constructs `MCPServerConfig(**data)` directly from JSON. `data["transport"]` is the plain string `"stdio"`. The dataclass performs **no enum coercion** — even though `MCPTransport(str, Enum)` makes `'stdio' == MCPTransport.STDIO` true, it is NOT an enum instance (`isinstance('stdio', MCPTransport) == False`).
2. `security_manager.py:665` (`validate_mcp_server_config`) builds the scan_id string via `server_config.transport.value if server_config.transport else ''` → plain str has no `.value` → **AttributeError: 'str' object has no attribute 'value'**.
3. `security_manager.py:1478` (`validate_mcp_server_before_connect`) does not catch it.
4. `mcp_manager.py:214` (`connect`) calls the gate; the exception propagates out of `MCPManager.connect()`.

### Blast radius (measured live, v2 script output)

| Probe | Outcome | Error |
|---|---|---|
| D-01a/b/c kernel wiring + singleton + 5 adapters | ✅ PASS | manager assigned, canonical, shared by graphify/notion/obsidian/claude_mem/playwright |
| D-02a UserSimulationAgent→bridge→kernel manager | ✅ PASS | no `_create_session_id` marker |
| FORENSIC config type | EVIDENCE | `graphify.transport is str`; `.value` crashes |
| PROBE-HERMES create_worker_session | ❌ CRASH | AttributeError @ security_manager.py:665 via mcp_manager.py:214 |
| PROBE-GRAPHIFY connect+store_node | ❌ CRASH | GraphifyUnavailableError wrapping same AttributeError (graphify_adapter.py:248) |
| PROBE-NOTION connect+search_pages | ❌ CRASH | NotionUnavailableError, same root cause (notion_adapter.py:226) |
| PROBE-OBSIDIAN connect | ❌ CRASH | ObsidianUnavailableError, same root cause (obsidian_adapter.py:238) |
| PROBE-CLAUDE_MEM connect | ❌ CRASH | ClaudeMemUnavailableError, same root cause (claude_mem_adapter.py:226) |

Boot itself succeeds and all 5 capability manifests auto-load — but every adapter's first `connect()` fails. **The entire MCP execution surface is unreachable in production mode.**

### The masking mechanism (IND-6 trap confirmed)

`tests/integration/conftest.py:229-271` (`RealMCPManagerHarness._build_config`) documents the workaround verbatim:

> "Uses the ``MCPTransport`` enum directly (not a JSON string) so the security gate's ``transport.value`` access resolves. Registering via ``MCPManager.add_server`` avoids the JSON-loader path. This is the M8-T6 **D-01/D-11 workaround**: it exercises the *real* MCPManager … without tripping the **D-11 crash that the string-transport JSON config path would hit**."

The fixture then injects this connected manager into every adapter and force-flips `adapter._connected = True` (conftest.py:345-355). Consequently every M8-T6 "production_paths" test passes without ever touching the broken JSON-loader path. The prior QA report's warning ("fixtures paper over production defects") was correct and remains unaddressed.

### Relationship to T6 defect register

- The remediation report marks **D-11 ("MCP config transport loading") as "✅ VERIFIED"** citing only `class MCPTransport(str, Enum)` at mcp_manager.py:32. That verification checked the enum *declaration*, not the JSON *loading path*. The live-boot evidence proves D-11 is **NOT resolved in behavior**: configs loaded from JSON crash the gate. The remediation claim for D-11 is contradicted by runtime evidence.
- This also re-contextualizes the T6 independent QA's observed "hanging issues" — connection attempts against string-transport configs raise inside gate-before-connect; depending on caller error handling this manifests as hangs/failures in suites that do not use the harness workaround.

### Why this is NOT silently fixed by Terminal 2

Spec §13 hard constraint: "DO NOT modify production source (src/aios/**)" / "DO NOT silently fix or 'repair' anything discovered". The one-line candidate fix (coerce transport in `_load_configs`, e.g. `transport=MCPTransport(data.get("transport","stdio"))`) is an M8-T6-scope production change outside M8-T7's QA mandate. **Recorded as DEF-01 with full RCA for Terminal 3 disposition** (fix-and-retest vs. return to T6 remediation owner).

---

## Verified-good items from this phase (positive evidence)

1. D-01 remediation is REAL at the wiring level: kernel owns the canonical MCPManager; all 5 adapters + Hermes bridge hold the same instance (live-boot asserted, not fixture-injected).
2. D-02 remediation is REAL: UserSimulationAgent drives a genuine bridge; the defective `_create_session_id` symbol no longer exists anywhere on agent/bridge.
3. Kernel boot completes cleanly; 5 capability manifests auto-load from `config/capabilities/`; MemoryManager GraphifyBackend wires via MCPManager.
4. ACP fallback behaves correctly when ACP cwd is absent: logs "ACP unavailable, falling back to MCP" (hermes_bridge) — honest degradation.

— P6 checkpoint complete. Proceeding to P2–P5 staged suites.
