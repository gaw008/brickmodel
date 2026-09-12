# Independent source and extraction review

Scope: the Arlabosse 2005 original Figure 1/2 GIFs and the extraction candidate in this scratch directory. No production/module changes, material fitting, interpolation, simulation, additional agents, or new material constants. This is an agent review, not external expert certification or an independent experiment.

Candidate frozen by:

- `extraction/facts.json`: SHA-256 `543d55918db7df6d0cc0f695c5dceadbdebda82b83f4fdde206266bcd12f2f16`.
- `extraction/extract_pixels.py`: SHA-256 `4ce0b2fe4f51b6e30ad6f76b37d5a6d868f89b1c0f62548f3cc020398c60faf9`.
- `extraction/PROTOCOL.md`: SHA-256 `d802a3ab0bcbe53f5359af724ddfd02e94367e65cc7d85a4cd7e9e6dbd7bfcc9`.

## Actual original-image and source reading

Both original GIFs were actually opened with `view_image`, not inferred from prose. Figure 1 visibly has water activity on x, dry-basis moisture on y, and 95°C in its caption. Figure 2 visibly has dry-basis moisture on x, total desorption heat (J/kg) on y, and 95°C in its caption. Both depict a continuous raster trace; none of the nine chosen W values is an identifiable original experimental marker. The observed tick labels agree with the declared linear scales and directions. Axis limits do not establish a supported curve domain.

The exact Arlabosse publisher URL returned a tool access error. The existing publisher HTML at `/Users/wanggaoying/Desktop/brickmodel-github/.tools/source-cache/arlabosse2005/article.html` was then directly read, and its 115329-byte content independently hashed to `7dc682647cc70503820e6738b806b052ddccc9f1bc14650178e8813c7e203816`. Lines 1078–1087 establish characterized activated sludge from a biological plant receiving 85% industrial and 15% municipal wastewater, with dissolved-air flotation and centrifugation before drying. These are wastewater-origin proportions, not an 85/15 dry-solid blend. This supports the stated unincinerated-sludge source identity, not MIA3 identity. Lines 1135/1145 tie the displayed sorption and total-heat graphs to that characterization and explicitly cite Ferrasse/Lecomte 2004; line 1300 identifies the referenced paper. Lines 1485–1502 point to the exact supplied original GIF URLs. The specific article-license section at lines 1332–1334 says CC BY-NC 4.0; the generic site footer has a different license and was not substituted for the article license. The common paper/material identity is verified; same aliquot, same measurement run, independent validation, and uncertainty for this sludge remain unverified.

The [Ferrasse and Lecomte 2004 author-uploaded full text](https://www.researchgate.net/publication/223808349_Simultaneous_heat-flow_differential_calorimetry_and_thermogravimetry_for_fast_determination_of_sorption_isotherms_and_heat_of_sorption_in_environmental_or_food_engineering) was directly read, including printed 1366 Eq. 4 and printed 1368–1369 Eqs. 21–24 and §3.2. Eq. 4 adds latent vaporization heat to isosteric sorption heat. Eqs. 21/23 relate total desorption heat to corrected heat flow divided by mass-loss rate during water removal, supporting J/kg removed water, rather than J/kg dry solids. §3.2 derives activity from the same dynamic measurement with transfer assumptions. The method reports sample-average temperature/moisture and distinguishes actual sample temperature from furnace setting. This supports the candidate's conditional interpretation and its refusal to add latent heat again; it does not validate this sludge's numerical accuracy. Read mode was HTML-rendered author-uploaded text, not original PDF page images. No MCC/kaolin values or uncertainty ranges were transferred.

## Independent reconstruction and distinct replay

`independent_check.py` does not import the author's script. It independently reads RGB values with Pillow, groups tick strokes from the original image strips, uses manually verified original label order, and clips an initial rectangle by exact rational half-planes. The clipping algorithm differs from the author's pairwise line-intersection enumeration. Both follow the explicitly declared full-pixel-footprint interpretation; therefore this is an independent implementation/reconstruction of that convention, not an independent measurement model or blind digitization.

`INDEPENDENT_CHECK.json` records:

- All 34 printed tick groups and all four complete feasible axis polygons agree exactly.
- Figure 1 x/y have 3/4 vertices and Figure 2 x/y have 4/4 vertices. Every polygon vertex obeys its tick constraints; the nominal vertex mean lies in the same feasible convex set.
- A stricter test requiring every pixel across all 405 interior columns to be nonwhite gives the same Figure 2 grid-row mask as the author's 401-column threshold.
- All 119 retained RGB pixels across the 18 target readings match the original GIFs exactly, including pale antialiasing pixels. Pixel selection bands, footprint component counts, nominal values, and all 15 exact rational bound pairs agree.
- Figure 2 W=0.10/0.60 touch grid footprints. W=0.50 has no independently visible off-grid trace. All three retain null main values and null main bounds.
- Nine Figure 1 and six Figure 2 values remain readable. The common discrete W values are 0.15, 0.20, 0.30, 0.40, 0.70, 0.80 kg water/kg dry matter.

The separately executed original script produced `facts.reviewer_replay.json`, byte-identical to `facts.json`. This is script replay and is not labeled as independent extraction.

Bounds are conservative for the declared raster-stroke and affine-axis convention. Taking inverse-map extrema at feasible vertices is appropriate: the axis orientation stays fixed, so each linear-fractional inverse map has its extrema on polygon vertices. The target-axis band and output-axis extremum handling may overinclude raster footprints, which widens bounds rather than falsely narrowing them. This does not bound experimental uncertainty, unidentified curve behavior between pixels, or values at unextracted W.

## Code review and conclusion

The extraction code was read in full and syntax compilation succeeded. `ruff`, `mypy`, `pylint`, and `black` were checked on PATH and in the existing `.venv`; none is available. No packages were installed, so no static-linter success is claimed. `git diff -- '*.py'` was inspected at review start; its integrator changes belong to another agent and are outside this source-extraction review.

No CRITICAL/HIGH defect was found that invalidates the current discrete extraction. The script verifies original-image hashes, rejects color-channel mismatch and infeasible/reversed calibration, preserves unreadable values as null, and exclusively creates its output file. The scratch script is not being approved as a general-purpose/public extraction API.

Raster-node verdict: **PASS for these 15 bounded candidate readings and 3 explicit unknowns**. Source identity and heat-unit interpretation: **verified to the stated paper/material/method level**. Overall approval is limited to discrete source-derived node-data validity. Continuous-domain admission remains null. Interpolation, the gap across W=0.50/0.60, thermodynamic reference bridging, dynamic drying, material qualification, and full-cycle qualification are not approved.

The prior-to-extraction ordering of protocol preparation is an author process statement; this review verifies the protocol's content and hash, not an independently time-stamped preregistration.
