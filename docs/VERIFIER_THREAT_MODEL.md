# Verifier threat model

## Scope

This document defines what `sludge-vme verify --strict` does and does not establish for the synthetic research MVP. It is not a production-security certification, a product-quality validation, an emissions/compliance review, or authorization to connect to a kiln, PLC, robot or recipe system.

## Three distinct guarantees

### 1. Hash integrity

`run_manifest.json` records SHA-256 and byte size for every payload artifact. Verification rejects a missing, added, resized or byte-modified payload when the manifest is unchanged.

This is only a self-declared byte-integrity layer. An attacker who rewrites a payload and updates its manifest hash can satisfy hash integrity. The manifest cannot hash itself without an infinite self-reference and records that fact explicitly.

### 2. Semantic replay

The verifier program is trusted in this model.

Forward strict verification rebuilds the model context from the resolved case and parameter provenance. The trajectory semantic contract fixes every strict field's species, unit, basis, conversion, resolved shape, finite requirement and range. The verifier independently recomputes:

- projected extents from raw ODE extents;
- gas mass-to-molar and molar-to-current-pore mappings;
- released-gas cumulative inventories from reaction generation minus internal storage;
- ideal-gas pressure at every time point and cell from molar inventory, temperature, open porosity and current volume ratio;
- cumulative reaction heat from raw extents and declared reaction enthalpies;
- cumulative boundary heat at every time point from stored reduced enthalpy minus independently reconstructed reaction heat;
- total/open porosity, liquid closure, sintering strain and stress trajectories;
- trajectory extrema, CSV projections, summary values and summary metadata;
- mass, bulk-volume, elemental, oxygen and reduced-enthalpy ledgers.

Inverse strict verification for `tiny` and `default` runs reconstructs the design population from `resolved_case + budget + seed + sampler algorithm/version`. It reruns the complete deterministic pipeline: scrambled Sobol designs, bounded design transform, L0 policy samples, robust feasibility, diverse L1 shortlist, grid checks and policy scenarios, ranking and Pareto filtering. It compares:

- ordered design IDs, decision vectors, record count and fidelity order;
- all declared design bounds and resolved design-case hashes;
- speed ratio and replayed residence time;
- policy sample IDs, seeds, algorithms, parameters, case/parameter-pack provenance and forward primary-state hashes (finite floats normalized to 8 significant digits so cross-process solver roundoff is stable but material changes alter the digest);
- sample outcomes, quantiles, failure policy, constraints, slacks, active set and objectives;
- L1 shortlist, feasible/ranked counts, rank stability, observed envelope, Pareto membership and nondominance;
- `all_evaluations.jsonl`, Pareto JSON/CSV, summary, uncertainty, flags and report.

A rehashed artifact that disagrees with these recomputations fails semantic replay even if every manifest hash was updated.

### 3. Cryptographic authenticity

The repository does not sign artifacts or manifests. It has no MAC, public-key signature, transparency log, remote attestation, trusted timestamp or protected signing key. Therefore it does not prove who produced an artifact, that an artifact came from an approved machine, or that the trusted verifier itself was not replaced.

Semantic replay is not cryptographic authenticity.

## Trusted components

- The checked-out verifier source and installed pinned NumPy/SciPy implementation.
- The local parameter/source packs referenced by the trusted code.
- The host process and filesystem while verification executes.
- Deterministic single-worker execution under the declared software environment.

## Attacker capabilities covered

The verifier is designed to reject an attacker who can copy an artifact directory, modify payload JSON/JSONL/CSV/Markdown, and synchronously update all corresponding SHA-256/size records in `run_manifest.json`, including:

- interior cumulative heat and pressure/extrema changes;
- field unit, basis, species, conversion, shape, finite/range or summary metadata changes;
- summary/conservation residual and count rewrites;
- L0/L1 record deletion, insertion or reordering;
- non-Pareto source-record changes;
- coherent Pareto decision/source/case-hash/CSV/envelope changes;
- constraint, objective, membership and nondominance changes.

Structured solver-failure handling also assumes exception text and class names may be attacker-controlled. Durable failure output therefore never serializes exception strings, reprs, args, tracebacks, locals, resolved user input, CLI args or output paths.

## Explicitly out of scope

- An attacker who replaces the verifier program, dependency code and all primary states together.
- Host compromise, debugger/in-memory manipulation, malicious Python import paths or compromised pinned packages.
- Cryptographic attribution, non-repudiation or trusted creation time.
- Proving that synthetic inputs are real plant measurements or that closures are scientifically calibrated.
- Protecting normal successful forward artifacts from secrets deliberately placed in the resolved case; secret-bearing cases must not be used. The credential-safe rule here applies to structured failure output and arbitrary exception text.
- Production recipe, emissions/compliance, certification or control-system approval.

## Strict versus integrity-only claims

Each forward/inverse manifest has a `semantic_verification` section. Fields listed under `strict_semantic_claims` are recomputed or deterministically replayed. Fields under `integrity_only_claims` are hash-checked but are not hard semantic claims.

Current forward integrity-only claims are UQ payload content, report prose, and runtime/platform provenance. Current inverse integrity-only claims are per-record `solver_statistics.wall_time_s` and manifest runtime/platform/transaction provenance. Manufactured test fixtures are labeled self-consistency-only and are not equivalent to a `tiny`/`default` deterministic replay.

## Cost and operational limit

Inverse strict replay intentionally has approximately the cost of another inverse run. It remains single-worker and performs no network or paid-service calls. Resource measurements must report replay wall time and peak RSS rather than hiding this cost.
