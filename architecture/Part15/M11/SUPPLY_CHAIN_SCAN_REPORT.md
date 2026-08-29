# M11-T5 Supply-Chain Vulnerability Scan Report

**Date:** 2026-08-27  
**Classification:** M11-T5 Deliverable — Supply-Chain Vulnerability Scan  
**Authority Chain:** Parts 0–14 > Accepted ADRs > Part 15 > Implementation > Tests  
**Generated From:** `tests/security/test_m11_supply_chain.py` — 20 executable tests

---

## 1. Executive Summary

This report documents the supply-chain vulnerability scan for AI-OS Hermes Kernel (M11-T5). The scan covers:

- **Dependency vulnerability scanning** — pyproject.toml parsing, known-bad package list
- **Lockfile integrity** — uv.lock / poetry.lock validation
- **Typosquatting detection** — known malicious package names, suspicious naming patterns
- **Malicious package behavior patterns** — obfuscated imports, suspicious network calls, hardcoded secrets
- **SBOM generation capability** — dependency extraction, uv export
- **CVE correlation** — documented integration patterns for external tools
- **Production gaps** — documented where external tools/services required

**Test Results:** 20/20 tests PASS

---

## 2. Dependency Analysis

### 2.1 pyproject.toml Structure

| Aspect | Status |
|--------|--------|
| Direct dependencies present | ✓ |
| Optional dependencies defined | ✓ |
| Parseable with `tomllib` | ✓ |

### 2.2 Known Vulnerable Package Check

Scanned against curated list of historically compromised / typosquatted packages:

| Package | Status |
|---------|--------|
| `requests` variants | ✓ Not found |
| `urllib3` variants | ✓ Not found |
| `django` variants | ✓ Not found |
| `flask` variants | ✓ Not found |
| `numpy` / `pandas` variants | ✓ Not found |
| `cryptography` / `pyyaml` variants | ✓ Not found |
| Historical compromised (`event-stream`, `eslint-scope`, `crossenv`) | ✓ Not found |

### 2.3 Vulnerable Version Pinning

Heuristic check for known vulnerable version patterns (e.g., `urllib3==1.2[0-5]` for CVE-2023-45803). No matches found.

**Note:** Real CVE correlation requires external database (NVD, OSV). See §7.

---

## 3. Lockfile Integrity

| Lockfile | Status | Notes |
|----------|--------|-------|
| `uv.lock` | ✓ Exists | Valid TOML, parseable |
| `poetry.lock` | — | Not present |
| `requirements.txt` | — | Not present |

Reproducible builds enabled via `uv.lock`.

---

## 4. Typosquatting Detection

### 4.1 Known Typosquat Database Check

Scanned dependencies against known malicious package names from PyPI security advisories. No matches found.

### 4.2 Suspicious Naming Pattern Analysis

| Pattern | Matches | Disposition |
|---------|---------|-------------|
| `*-dev` suffix | None | — |
| `python-` prefix single word | `python-dotenv` | Legitimate exception documented |
| `py-` prefix single word | None | — |
| Long numeric sequences | None | — |

**Exception documented:** `python-dotenv` is a legitimate package.

---

## 5. Malicious Package Behavior Patterns

### 5.1 Obfuscated Import Scan

Scanned all `src/**/*.py` files for:
- `exec(base64...)` / `eval(base64...)` / `__import__(base64...)` / `compile(base64...)`
- `exec("string")` / `eval("string")` patterns

**Result:** No obfuscated imports found in production code (test files excluded).

### 5.2 Suspicious Network Calls

Scanned for:
- Requests to pastebin/raw.githubusercontent.com/gist.github.com (data exfil indicators)
- Raw socket connections
- `curl` / `wget` subprocess calls

**Result:** No suspicious patterns in production code.

### 5.3 Hardcoded Secrets in Config Files

Scanned `*.toml`, `*.txt`, `*.yaml` for:
- API keys / tokens / passwords (20+ char values)
- AWS credentials
- GitHub tokens

**Result:** No hardcoded secrets found (test/example files excluded).

---

## 6. SBOM Generation Capability

| Capability | Status | Notes |
|------------|--------|-------|
| Direct dependency extraction | ✓ | From pyproject.toml |
| `uv export --format=requirements-txt` | ✓ | Works if uv available |
| SPDX/CycloneDX generation | **Gap** | Requires `cyclonedx-py`, `syft` |

---

## 7. CVE Correlation

### 7.1 External Tool Integration Patterns

| Tool | Command Pattern | Output |
|------|-----------------|--------|
| `osv-scanner` | `osv-scanner --lockfile=uv.lock` | JSON vulnerability list |
| `pip-audit` | `pip-audit --format=json` | JSON vulnerability list |
| `trivy` | `trivy fs --format=json .` | JSON vulnerability list |

### 7.2 GitHub Dependabot

**Recommended:** Add `.github/dependabot.yml` for automated CVE alerts and PR creation.

---

## 8. Production Vulnerability Scanning Gaps (Documented)

| Gap ID | Description | Severity | Mitigation |
|--------|-------------|----------|------------|
| GAP-SC-01 | No built-in CVE database | HIGH | Use `osv-scanner` / `pip-audit` in CI |
| GAP-SC-02 | No real-time vulnerability feed | HIGH | Schedule daily `osv-scanner` runs |
| GAP-SC-03 | No automated remediation workflow | MEDIUM | Enable Dependabot / Renovate |
| GAP-SC-04 | No SPDX/CycloneDX SBOM generation | MEDIUM | Add `cyclonedx-py` to CI pipeline |
| GAP-SC-05 | No license compliance scanning | LOW | Add `pip-licenses` or `licensecheck` |

**Per M11 Authority Constraints:** These are documented as GAPs, not implemented. M11 MUST NOT become an authoritative decision-maker or add new architectural dependencies for vulnerability scanning.

---

## 9. Test Inventory (20 Tests)

| Class | Tests | Status |
|-------|-------|--------|
| `TestDependencyVulnerabilityScan` | 4 | ✓ All PASS |
| `TestLockfileIntegrity` | 2 | ✓ All PASS |
| `TestTyposquattingDetection` | 2 | ✓ All PASS |
| `TestMaliciousPackagePatterns` | 3 | ✓ All PASS |
| `TestSBOMGeneration` | 2 | ✓ All PASS |
| `TestCVECorrelation` | 2 | ✓ All PASS |
| `TestProductionVulnerabilityScanningGaps` | 4 | ✓ All PASS (documentation) |
| `test_supply_chain_test_count` | 1 | ✓ PASS |

**Total: 20 tests, 100% pass rate**

---

## 10. Document Control

- **Status:** COMPLETE — M11-T5 Deliverable
- **Generated By:** Terminal 2 (Implementation Engineer) per M11-IMPLEMENTATION-SPEC.md
- **Source of Truth:** `tests/security/test_m11_supply_chain.py`
- **Review Cycle:** M11 Independent QA (Terminal 3) → GO/NO-GO

---

## Appendix A: Related Documents

- `M11-IMPLEMENTATION-SPEC.md` — M11 authoritative specification
- `tests/security/test_m11_supply_chain.py` — Executable test suite (source of truth)
- `architecture/Part15/15.9-Security-and-Governance-Implementation.md` — Part 15 Security Chapter
- `architecture/Part15/M11/SECRETS_AUDIT_REPORT.md` — M11-T4 Secrets Audit Report

---

## Appendix B: Architecture References

- Part 3 §3.5 (ConfigurationManager) — Dependency management
- M8-T5 — CapabilityManifestLoader supply chain for capabilities
- M10 — SecurityAbacExtensionService autonomous operations
- ADR #10 — Bounds on autonomous operations (max_depth=5)