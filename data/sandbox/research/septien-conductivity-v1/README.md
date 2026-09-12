# Septien donor conductivity

`source.json` preserves two measured rows from Septien et al., *Effect of drying
on the physical and chemical properties of faecal sludge for its reuse*,
Journal of Environmental Chemical Engineering 8(1), 103652 (2020),
[DOI 10.1016/j.jece.2019.103652](https://doi.org/10.1016/j.jece.2019.103652).
The original full JATS body and Table 2 were read on 2026-09-12. It identifies
VIP pit-latrine faecal sludge, distinct from the Arlabosse material.

`model.json` declares the exact wet/dry conversion and nominal two-node linear
interpolation, used only as a cross-material exploration. The conductivity
measurement temperature is unknown. Constant k at fixed W across 35–95°C is a
model assumption. Original 90% source intervals remain separate from the
unknown interpolation and transfer errors. Model W domain is .30–.80.

The provider requires the original article XML in an explicit local directory,
plus these two metadata files under the supplied repository root. The original
article declares CC BY 4.0; see the exact license/attribution in `source.json`.
The local cache is ignored by Git and this parameter package does not include
the original article body.

Original acquisition URL:
https://www.ebi.ac.uk/europepmc/webservices/rest/PMC7043394/fullTextXML

Save the original response as `fecal2019-original.xml` without reformatting it.
Required size is 102,289 bytes; SHA256 must be
`cda0a7fba9cea9dc3b20d8a4b68f36ad571dcaf22deaec7386f323dd95714a0f`.
The provider rejects a changed or unavailable original, rather than silently
adopting an updated article version. This workspace cache is
`runs/sandbox/source-cache/septien2020/`; column integration tests also accept an
explicit `SEPTIEN_SOURCE_DIRECTORY`. Leaf unit tests use a declared manufactured
XML seam and do not require network access.

```python
from sludge_sandbox.septien_conductivity import SeptienConductivity

provider = SeptienConductivity(repository_root, source_directory)
point = provider.evaluate(330.0, 0.5)
assert point.k_w_m_k == 0.05805375
trace = point.to_record()
```

`source_points()` exposes original rows and exact conversions. `definition()`
and each point's record separate observed numbers, transformations, model
choices, numerical projection, unknown errors and false material qualification.
The caller must supply independently identified geometry, other transport and
phase relations; this provider alone is not a complete sludge material model.
