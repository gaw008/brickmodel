# Independent Nylen Figure8 extraction review

Read PLAN.md, complete extract.py, selection.json, source.json, output CSV and extraction audit. Original native I16 image and selected overlay both viewed. Original PDF SHA and embedded image SHA independently verified through pypdf; exact raster exported only to reviewer temp directory. No author files changed, fitting or EOS calls performed.

Visual source check: selected points are filled temperature symbols, not hollow MR observations. Gray squares MSJ2cm, red circles MSJ4cm, blue upward triangles CB2cm, green downward triangles CB4cm agree with actual legend. Manual gray square (400,390) is visible under intersecting hollow red MR and its3pixel center allowance is defensible. Right ordinate temperature ticks use0°C at y843 and140°C at y49; left MR axis is not used. Time is0–160min from x133 to1125. Interior ticks agree within stated1pixel calibration allowance. The partial readable subset is honestly reported: connected plateaus and upper clusters remain unresolved, no fabricated regularly spaced grid or inferred count.

Independent execution in readback.py uses SciPy binary_erosion with explicit5x5 structure and zero boundary, then ndimage label with3x3 connectivity. This differs from author's rolled masks plus BFS. Every retained component area, bounding box, center, selected43 observations and manual center match saved audit/CSV. Pixel mask wraparound has no consequence inside the cropped region. Counts are MSJ2=8, MSJ4=12, CB2=15, CB4=8.

Independent exact Fraction arithmetic reconstructs all43 central temperatures/times and all calibration endpoint combinations, matching CSV9decimal rounding. Seconds correctly equal60 times minutes within saved rounding. Source IDs and run/material/size conditions match metadata. Blank plotted_sd_degC is preserved as unknown; center-readout bounds are not experimental SD or confidence limits. No upper-temperature clamping or MR normalization appears in code.

Review request sent to root: extraction audit should include source.json hash, and code should consume or explicitly validate selection's calibration values and axis-readout fields rather than silently ignore them in favor of hardcoded equivalents. Current values and numerical output agree. Also public script functions need type annotations for maintainability. Static analysis tools were previously checked absent in isolated runtime; no installation made solely for this extraction script.

Authoritative reviewed hashes and independent result are in RESULT.json. This is source-image transcription verification, not independent physical validation or full material qualification.

## Final correction readback

Root added source_metadata_sha256 from actual metadata bytes, exact validation of all7 recorded calibration fields, and public function annotations. Re-read final code f6e17a241128ecd3fcb1836f4779612f590e943f1d2db326d71e9a2b6d17d73c. Final extraction_audit binds this actual script hash and metadata hash. Independent SciPy/Fraction readback rerun PASS43; CSV remains SHA2561bbac6f79816d457d4e05ceeee8382eb3c50605a9addcb4cf0dbe7379a3f1bc9. Review requests resolved; no current numerical/correctness findings.
