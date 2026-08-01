import re
p = r'C:\Development\AI-OS\ARCHITECTURE_SPEC_PART8_STEP3.md'
with open(p, 'r', encoding='utf-8') as f:
    lines = f.readlines()

def setline(i, newtext):
    while len(lines) <= i:
        lines.append('\n')
    lines[i] = newtext if newtext.endswith('\n') else newtext + '\n'

# Find indices
def find(substr):
    for k,l in enumerate(lines):
        if substr in l:
            return k
    return None

# Fix the "source dispatch" intro line
k = find('a capability binding')
if k is not None:
    setline(k, "Within the CIE, the capability **type** (derived from the Capability Manifest, Sect 8.2.7.7, and the `capabilityId` namespace) determines the Facade Service. The plan field `source` denotes the **scope** (Project/Global/External per INV-EXEC-STR-015) and is NOT used for facade dispatch:\n")

# Fix the dispatch table header
k = find('` `binding.source`` | Facade Service`'.replace('`','`'))
k = find('binding.source')
if k is not None:
    setline(k, "| `capabilityType` | Facade Service |\n")

# Fix table rows
for i,l in enumerate(lines):
    if '**`SKILL:` prefix**' in l and 'SkillService' in l:
        setline(i, "| **`SKILL` capabilityId namespace** | SkillService |\n")
    elif '**`MCP:` prefix**' in l and 'MCPService' in l:
        setline(i, "| **`MCP` capabilityId namespace / providerRequirement.type=TOOL** | MCPService |\n")
    elif '**`MEMORY:` prefix**' in l and 'MemoryService' in l:
        setline(i, "| **`MEMORY` capabilityId namespace** | MemoryService |\n")
    elif '**`COUNCIL:` prefix**' in l and 'CouncilService' in l:
        setline(i, "| **`COUNCIL` capabilityId namespace** | CouncilService |\n")
    elif 'No recognized prefix' in l and 'SKillService' in l:
        setline(i, "| Unrecognised type | CIE rejects with `CAPABILITY_TYPE_UNRESOLVED` (no silent default; a missing type is a plan-construction defect from 8.2) |\n")

# Fix Provider Independence rationale paragraph
k = find('Rationale and Provider Independence')
if k is not None:
    setline(k, "**Rationale and Provider Independence:** As specified in 8.1.4 (EXEC-DG-008, Vendor Interchangeability), the CIE MUST work identically across all providers. Should any new Capability Facade Service be introduced, incorporation is a configuration-only operation: register the new type with the dispatcher map and adapter. No change to the CIE runtime is necessary.\n")

# Fix CIE-DISP-001
k = find('All direct Core Manager access from the CIE is prohibited. CIE must invoke')
if k is not None:
    setline(k, "**Invariant CIE-DISP-001:** All direct Core Manager access from the CIE is prohibited. The CIE MUST invoke capabilities ONLY through Capability Facade Services (Part 6). Direct Core Manager access is disallowed via static analysis (no `kernel.<manager>` calls in Layer 4 services) and a runtime guard. A violation is a conformance defect against INV-EXEC-STR-006.\n")

# Fix CIE-PRM-001 garbled text
k = find('Random seed, system time, and any external lookup are explicitly prohibited from the binding process. Determinism')
if k is not None:
    setline(k, "**Invariant CIE-PRM-001:** Parameter binding is deterministic: given the same node params, same journal, and the same environment snapshot, binding MUST produce the same output. Random seed, system time, and any external lookup are explicitly prohibited from the binding process. This enforces EXEC-DG-010 (Deterministic Replay).\n")
elif find('CIE-PRM-001') is None:
    pass

# Fix CIE-PRM-002
k = find('The Loop Engine may then consider a dependency chain rollback')
if k is not None:
    setline(k, "**Invariant CIE-PRM-002:** Parameters referencing a node that FAILED or was SKIPPED MUST result in `PARAMETER_BINDING_FAILED`. A failed/skipped node implies a broken data dependency, and continuing would propagate incorrect data. The Loop Engine (Sect 8.3.3) MAY then consider a dependency-chain rollback.\n")

with open(p, 'w', encoding='utf-8') as f:
    f.writelines(lines)
print("OK fixes applied")
