# Figure8 internal-temperature digitization plan

Source: Nylen2024 DOI10.1080/07373937.2024.2407959, original articlep2052, PDFpage10 (zero-based9), asset bound by ../source.json. No numerical marker extraction or fitting has occurred before this plan.

Extract the four filled-marker internal-temperature series only: gray squares MSJ2cm (working run1), red circles MSJ4cm(run6), blue upward triangles CB2cm(run7), green downward triangles CB4cm(run10). All use138°C drying gas and2.4m/s. Legend mapping must be read from Figure8. Time unit minutes, temperature unit°C, with time in seconds also supplied.

The PDF contains embedded raster images for this page, so first extract the original Figure8 image bytes through pypdf/Pillow; do not inflate precision through rendering/resampling. Record image dimensions/hash and top-left pixel-coordinate convention. Calibrate time from labeled major ticks and temperature from the right-hand axis, preserving calibration coordinates.

Preserve every independently readable filled-marker center. Use reproducible color/shape segmentation with an explicit reviewed-selection list if needed; connected/overlapping markers that cannot be separated defensibly must remain unresolved regions rather than invented samples. Hollow MR markers and error bars are not temperature observations. Record original center coordinates and conservative pixel-readout intervals separately from unknown plotted experimental SD. Do not infer zero SD when bars are absent or inseparable. Do not clamp observations to gas temperature, infer missing integer-minute points, smooth, fit or replace ambiguous markers with a modeled curve.

Outputs: extraction script, numeric observations, calibration/selection record, explicit unreadable regions and methods/limitations. Curves have already been inspected for source qualification; this is a descriptive extraction, with no new independent-holdout or calibration claim. Figure9 and MR values are out of scope.
