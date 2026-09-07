# Independent review: Baloi 2025 extraction

Reviewed 2026-09-07 UTC. Scope: `data/sandbox/research/baloi2025/extract_tables.py`, original publisher HTML/JATS XML, source manifest, derived JSON, and `BALOI2025_COVERAGE.md`. No source or core edits. Other worktree changes belong to concurrent tasks.

## Evidence binding

- Extractor SHA-256: `c60e2fade8c0cc1a4f1cd29830ae1785195709638f8f99af81f414f3d3c76da8`.
- Original XML: `4fa1483919916f191830312219665df5c980aca039b7b989a5644612b4bb1f9c`.
- Original HTML: `351b6d1f74ebe392f7322ce42b255fc5f76401ebbe30bee9c14a335cb55fc0f1`.
- Derived JSON: `820eebc721dbf5a475810110eb8003c949b1acf751f53525aeeba6c862b8690b`.

Verified all four manifest sizes and hashes from actual bytes. Read original XML permissions and HTML copyright paragraph: attribution to Baloi et al., 2025, and CC BY 4.0 license URL agree with manifest. Original journal DOI and author metadata support the attribution. No fresh download was necessary for this extraction review.

## Independently verified behavior

Compared every cell of all three original JATS tables against JSON: normalized text, empty cells, en dashes, and all attributes agree; no numeric values were silently supplied in empty uncertainty fields. Actual source tables have no rowspan attributes. The extractor retains arbitrary cell attributes, including rowspan if present, but does not expand or infer merged cells. Its fixed row indexing is appropriate for this pinned source, not a generic table parser.

Read table headers directly: Table 2 density is g/cm³, requiring multiplication by 1000; Table 3 alpha has a displayed factor of 10⁷, requiring multiplication by 10⁻⁷. Matched sample labels in Tables 2 and 3, including `Control brick`. Table 1 uses `CB`; that alias is not silently joined to a dry-mass recipe.

Using 40-digit Decimal arithmetic and manually transcribed original table entries (without invoking the extractor as oracle), independently computed:

| Sample | k = e sqrt(alpha), W/(m K) | apparent cp, J/(kg K) |
|---|---:|---:|
| Control brick | 0.7001914024036571 | 439.9292550915161 |
| N17 | 0.6781004571595568 | 463.9439362065934 |
| N18 | 0.5831668028960496 | 436.3061520993937 |
| N19 | 0.5528456927570297 | 442.91435087087774 |
| N20 | 0.49722813677425776 | 408.63587834833805 |

All five outputs agree at relative tolerance 1e-14. Original reported k remains separately stored: N19/N20 differences are approximately +2.379%/-2.504%, not corrected away. No covariance or derived-cp confidence interval is invented.

Copied this evidence directory into a fresh temporary directory and executed its copied `extract_tables.py`; regenerated JSON was byte-identical. Authoritative evidence was not overwritten.

## Scientific scope and limitations

Original sections 2.1, 2.3, 2.4 and 3.3 support preparation history, thermal measurement identities, argon TG/DSC conditions, and the approximately 26–41°C surface temperature discussion. Coverage correctly distinguishes fired material effective properties from wet/green and high-temperature phase properties. Apparent cp is newly derived under effective homogeneous heat-diffusion identities, not direct calorimetry or a qualified raw-sludge constant.

Volumetric proportions are not converted to dry-mass fractions without component densities. Approximately 20 wt% forming water is not silently interpreted as a complete wet-basis initial condition. The source's argon atmosphere alongside combustion wording is expressly quarantined from air-char kinetics; gas yields are not invented. Missing full-cycle material parameters remain explicit. Five co-reported endpoint rows are evidence extraction, not independent predictive validation.

## Findings

No actionable correctness or security issue above the review confidence threshold. Minor terminology clarification relayed to root: source tables contain no actual rowspan attributes, so wording should describe attribute preservation capability rather than imply a merged uncertainty cell exists. This does not change extracted data or qualification.

## Review Summary

| Severity | Count | Status |
|----------|-------|--------|
| CRITICAL | 0 | pass |
| HIGH | 0 | pass |
| MEDIUM | 0 | pass |
| LOW | 0 | pass |

Verdict: APPROVE — source-bound extraction and limited post-firing derivations at the hashes above; not a complete raw-sludge material pack or full Goal approval.
