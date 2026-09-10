# Independent Table2 and source.json check

Input JSON: `data/sandbox/research/nylen2024-drying/source.json`, SHA256 `786f0403d7567ae17866dfe818eb85c4fab00f7c0d72351ddd1fa7e5cee3c1ed`.
Original: `.tools/source-cache/nylen2024/paper.pdf`, SHA256 `d62e8a552b7dd90051fe498d9a28a1eef6e39642b328e9dbcdcf2c719982b70f`, 2351898 bytes. Both JSON asset claims independently match actual bytes.

Read extracted original pp2046–2048 and rendered original p2048 Table2. Every row's material, diameter, temperature, gas velocity and three repetition counts matches the JSON. The materials/preparation follow §2.1 and Table1 rather than the contradictory abstract. The separate mass/temperature experiment statement follows §2.3. All three count totals independently recomputed: 22 internal temperature, 18 surface temperature, 22 mass. The 44 reported trials are consistent with internal plus mass counts; surface observations must not be added as 18 distinct independent experiments. Raw repeat pairing is not proven by the totals.

One provenance correction is needed: Table2's first row has a **blank printed Run cell**, confirmed visually. JSON `run:1` is a reasonable assigned row-order identifier, but not an exact printed source label. Retain the working identifier while explicitly recording `source_run_label:null` for that row and that 1 is inferred from row order; rows2–10 are printed labels. No numerical condition correction is required.

No curve extraction, parameter fitting, new external search or code modification occurred. Source registration does not establish constitutive/material admission, and this check does not validate downstream models.
