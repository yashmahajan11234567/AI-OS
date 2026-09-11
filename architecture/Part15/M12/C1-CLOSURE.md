# C1 Closure — Hermes Naming Collision

### 1. Closure Metadata

* Conflict: C1 — Hermes Naming Collision
* Status: **RESOLVED**
* Resolution date: **2026-09-10**
* Resolution type: Documentation / terminology clarification
* Governing milestone: M12-T1

This document formally closes the C1 documentation conflict regarding Hermes naming ambiguity.

### 2. Conflict Definition

The documentation distinguishes between:

**HermesKernel / Hermes Kernel**
* AI-OS internal kernel component
* Located at `src/aios/core/kernel.py`
* Internal AI-OS authority/component

**hermes-agent(EXT)**
* External browser-automation worker
* Separate from AI-OS's internal HermesKernel
* Returns observations only
* Has no authority relationship with HermesKernel

### 3. Authoritative Terminology

Per the authoritative source `architecture/Part15/glossary.md §4`, the following terminology is established:
* **Hermes Kernel**: The internal AI-OS kernel component
* **HermesKernel**: The specific class/instance name in source code
* **hermes-agent(EXT)**: The external browser-automation worker

Documentation should use these qualified terms rather than ambiguous standalone references to "Hermes" to preserve the repository's existing terminology distinctions.

### 4. Resolution

C1 is formally resolved because the repository documentation establishes a clear terminological distinction:
* `HermesKernel` = internal AI-OS kernel component
* `hermes-agent(EXT)` = external browser-automation worker

The naming collision represents historical terminology overlap only and does not indicate an authority relationship or component identity collision. No source-code identifiers were renamed as part of this resolution.

### 5. Existing Evidence

The repository already uses disambiguated terminology in:
* `architecture/Part15/glossary.md §4` - Defines the authoritative terminology
* `architecture/Part15/README.md` - Maintains the distinction between internal and external Hermes components
* Various Part15 chapter files that consistently apply the qualified terminology

### 6. Release-Notes Evidence

`CHANGELOG.md` contains the v1.0.0 C1 entry which records C1 as fixed through documentation clarification. The CHANGELOG serves as the official release-notes record and is not being modified as part of M12-T1.

### 7. Scope Boundary

* No source-code changes were required for this closure
* No component renames were performed
* No external repository changes were performed
* C2, C3, and C4 remain separate M12 tasks
* M10 and M11 are unaffected by this closure

C2/C3/C4 are not resolved by this document. M12 completion requires additional tasks beyond C1.

### 8. Closure Statement

**C1 — Hermes Naming Collision is formally resolved and closed as of 2026-09-10 through authoritative terminology clarification and documentation evidence.**