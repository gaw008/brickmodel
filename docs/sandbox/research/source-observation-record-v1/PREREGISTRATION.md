# Source observation installation and saved-input exercise

Baseline ac04d8b; passive observation persistence only. No new physical evolution,
model/provider construction, EOS evaluation, tolerance change or run resume.

After codec/service review and freezing the final source/tests, run the new codec
and CLI tests plus existing exact_record and run_service regressions in source
and the same noneditable offline installation. Inspect the actual XML counts and
all package file bytes. Do not rerun the previous numerical transition experiment.

Run `exercise_saved.py` once with the installed package and frozen inputs:

- N3 liquid transport, 32 captures, 45,527,737 bytes,
  SHA 2660d33ec0e832e006d5adcccd8ddcf38cc314ac5e65a17830cdf2f73cbdc51d.
- N1 wet/dry, 32 captures, 14,524,919 bytes,
  SHA a9d2d658a259e72f871e4f96c8d3e0172def2720a2901bc91c06e78e5a97d4dc.
- Programmed liquid transport, 47 captures, 6,476,290 bytes,
  SHA 033dccd09ed268eeb2ce9570a37d52f66d4eb5da18b68f2f44a89bd01054c4f2.

Import all 111 complete observations through the explicit Python codec, save each
canonical record, reread/check it and independently project all dataclass fields
back to the original legacy representation. Require exact JSON numeric/type
equality of state/evaluation/time; no discarded fields, recomputed EOS or numeric
tolerance. Every record retains original input SHA/path/index/ordinal and modes
when saved. The 47 older captures lack outer identities/phase/modes: use their
actual nested operator/energy identities, explicitly declare the import role as
`legacy_programmed_observation`, and leave modes unknown. This adapter is recorded
in the runner and is not implicit file-format guessing by the service.

For each record use installed inspect and require the preserved numerical values,
original cell indices, source labels, no material qualification, no resume and no
source-asset authentication. Inspect is not full-run validation. Re-encoding with
the same context/provenance must reproduce canonical bytes. Save all outputs and
the first failure, including a partial count, without automatic retry. Soft total
budget 60 s; hard 90 s signal alarm. The fixed 111 records cap scope independently
of time. The runner input hashes and execution file are frozen before execution.

Separately invoke the installed CLI to import N3 capture 16 and inspect original
cell 1. Retain stdout/status and compare it with the Python service for that same
saved file. A single CLI import is file I/O/decoding, not a repeated simulation.

Original numerical pressure failures and material=false remain unchanged. The
independent wet-pressure budget analysis may identify a next derivation, but it
does not certify a new joint wet-pressure bound.
