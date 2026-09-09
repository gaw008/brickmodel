# Complete exact ordered packet: original four-cell case

Baseline `be2f48d`. New production module `exact_depletion_integration.py` SHA256 `be323c820fe9f0c0981bb3bc7b4db817c8931c2501e704e394ae85a4c815a16b`, tests SHA256 `3e96e5a57c69076183daf74da2c4d80bd713c860d1ed698fc43f42312bb790f2`. Author and independent code/numerical reviews are retained in the archive.

## Actual complete run

Original case SHA256 `a614d4b1f1e493dea86b86e1d6fab57139e355541447527ed5c4106c3afe73db`, initial state, physical operator and original policies were checked against the retained failed four-cell experiment. The explicit ordered opt-in matches that earlier run. Exact start/end adopt the original binary64 .5/.50032 values without changing the horizon. The original 512-panel/800-second limits and all scientific gates remain; external watchdog 840 seconds.

Supervised attempt01/session39872 terminated exit0 after 172.102407875 seconds. Runner elapsed171.777573084 seconds, core170.176692625 seconds. Core completed:32 accepted steps,2 committed packets,4 depletion events in order3→2→1→0, all four final modes depleted_no_nucleation. Final exact time4506481931132013/9007199254740992. All76 runtime modules were unchanged before/after and matched the actual noneditable installation.

Costs:717 attempted/completed evaluations,71 ordinary trial/accepted speculative panels,0 rejected ordinary trials,16 predictors and terminal attempts/panels,120 paired-pressure endpoint attempts/completions,0 stage replans. These include speculative comparison paths;32 committed steps are not the total work. Each packet retained level0 coarse_reference, levels1/2 comparison_pass, then a separate independent comparison_pass.

The explicit new strategy is `independent_halved_controls_no_spine_reuse`: both approach paths are computed and charged even though the inherited policy contains reuse_ordinary_spine=true. This is a declared numerical implementation choice; the old cache optimization was not used. Exactly-zero affine polynomial roots receive zero localization remainder; other roots retain the full certified interval. This fixes the prior absolute-clock precision failure through a complete exact-time path, without relaxing correction or comparison gates. The historical failed legacy run remains unchanged.

## Verification and limits

Source test command used PYTHONDONTWRITEBYTECODE=1, PYTHONPATH=src:tests/sandbox and the frozen water venv Python with pytest on test_exact_depletion_integration, test_exact_terminal_executor, test_exact_root_order, test_exact_terminal_panel, test_exact_integration and test_exact_free_host:76 passed11.33s. After `uv sync --frozen --no-editable --inexact --extra dev --extra water --offline --reinstall-package sludge-vme`, installed testing from /private/tmp without PYTHONPATH covered the first three modules:46 passed6.59s.76 actual installed modules match source. These are relevant targeted suites, not a newly run entire sandbox suite.

Independent saved-data Fraction prefix audit passes every accepted prefix against original N/E and mechanical state, components, paired correction and once-only totals. Max N residual1.8568610656e-16mol, E4.5417706603e-11J, represented stretch4.2449313899e-16, exact stretch4.2449251662e-16, accumulated absolute stretch quadrature1.3138625143e-21, component absolute cumulative2.9468627441e-20J. Original gates retained. Independent comparison audit checks2 packets,6 comparison records, every event/common endpoint six gates,96 pure pressure certificates,120 endpoint calls and static original source/domain bindings. Review files describe the exact boundaries.

The17,654,698-byte core capture retains full exact states, ledgers, events, terminal attempts, paths, comparisons and used numerical observations. It intentionally omits duplicated live provider/current-host inverse trees. The full original operator canonical input and original source identity are saved separately. Audits of captured arithmetic do not re-run EOS or reconstruct omitted inversions, nor independently prove the true nonlinear event root. This is actual water EOS plus manufactured solid/transport parameters, not raw-sludge material validation.

The new result is an explicitly versioned research core, not an admitted legacy record/checkpoint. Strict record/audit/restore/resume and CLI/UI integration remain next work. Larger-grid spatial convergence, supported original-sludge closure, public three-mechanism and heldout prediction, full wet-firing-cooling and multigeneration application acceptance remain mandatory and incomplete. Goal remains active.

Independent closed-system audit additionally checks every one of32 prefixes using Fraction geometry: max |sumE−sumE0+peΔV|6.166833498764901e-11J, cumulative absolute cross-cell constraint2.3107070843279913e-20J, both below original2e-8J. Original closed boundaries and every accepted outer species/energy and body integral are explicitly zero. This is separate from state-versus-ledger accounting.

## Preserved evidence

The archive includes the candidate, original failures and intermediate test logs, reviewer records, frozen run.py, original input snapshots, complete core capture, runtime identities, supervisor terminal status, independent scripts/reports and source/installed test outputs. The manifest records each member hash and archive hash. No water-data assets are copied into this archive; original operator snapshots retain their source bindings and the existing water preparation evidence supplies those inputs.
