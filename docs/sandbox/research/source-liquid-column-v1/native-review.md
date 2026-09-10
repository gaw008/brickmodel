# Installed native liquid-column saved-data audit

166 independent offline assertions passed. The final installed-step JSON was opened only after root confirmed terminal exit 0. No EOS, scientific package or model code was imported or run by the audit. No repository/native result files were changed. Root's runner audit count was not used as proof.

Input installed-step SHA256: `9644aa69ee7ddc150184f91b35961df8bd8d1988afc44acf2a12c49b4b9ccca3`.
Source-probe SHA256: `5dfcebbb685c7e96e78728c2511687be64b995520ff1d912cfe47afc417b1361`.
Actual mobility.json SHA256: `d11dfbbd25ca0dfb9e5cc53880fb5f16a5abe9b385dbb605bb101d49b8f056d1`.

The saved run is completed with three completed/attempted evaluations, one accepted ledger, initial/final state snapshots, midpoint state snapshot and endpoint observation. Stage states exactly match initial/midpoint/final states at 0, 1/2048 and 1/1024 s. The terminal source probe's initial state and full first observation equal the installed first stage exactly. Run elapsed_seconds is 22.167228167003486 s; root's outer wall duration includes surrounding work and is a distinct metric.

## Independent rate reconstruction

For all three stages, the audit independently checks decoded liquid temperature, total planar pressure and inventory against the actual inverse/mechanical state, and pressure_error against the full SourceWetPoint bound. Saturation equals mechanical liquid volume / available fluid volume. All actual mobility T/P/S arguments lie inside the saved table domains. Manufactured table contents and hashes match the real mobility.json asset.

Using saved geometry and liquid states, the audit independently reconstructs Fraction Darcy resistance, Q=A*(pL-pR)/(dL/ML+dR/MR), then J=Q/v_donor and H=J*h_donor, followed by binary64 conversion. It checks the direction, summed pressure error with outward rounding, fixed-decoded-temperature qualifier, and explicit liquid enthalpy projection discrepancy. It does not recompute liquid v/h from EOS: those are saved, source-labelled primitive inputs.

| Stage | Face 1 liquid mol/s | Face 2 liquid mol/s | Face 1 liquid enthalpy W | Face 2 liquid enthalpy W |
|---|---:|---:|---:|---:|
| initial | -9.865265596812799e-5 | -8.125013908878981e-5 | 27.94196112233345 | 23.00516741623395 |
| midpoint | -9.864106592089179e-5 | -8.120019678887855e-5 | 27.938678427393867 | 22.991027911388926 |
| endpoint | -9.86294685465475e-5 | -8.119627745266071e-5 | 27.935393657165168 | 22.9899182934773 |

Both liquid faces flow from the right donor at all stages. Positive liquid enthalpy power with negative molar flow reflects the declared negative water enthalpy reference; it is not a sign error. Liquid flow at both external boundaries is exactly zero. The gas/thermal right boundary remains open.

## Exact integrated balances

Every face gas, liquid, conduction, diffusive/advective enthalpy, liquid enthalpy and liquid enthalpy projection integral equals exact dt times its saved midpoint rate. Each face energy decomposition includes the physical liquid enthalpy separately from decomposition roundoff. Every cell's liquid, all gas species, total water and U change equals its face/phase increment plus accepted signed projection correction. Global internal exchanges cancel exactly.

| Global quantity | Stored change | External/phase contribution | Accepted signed roundoff | Exact residual |
|---|---:|---:|---:|---:|
| U (J) | +0.0894194447027985 | +0.08941944470570316 | -2.9046626215389892e-12 | 0 |
| liquid (mol) | +6.755537962366276e-9 | +6.755537967109106e-9 from phase redistribution | -4.742829880023365e-18 | 0 |
| O2 (mol) | -7.538848329019521e-6 | -7.538848329013260e-6 | -6.260420513156534e-18 | 0 |
| N2 (mol) | -9.914417761547334e-6 | -9.914417761581156e-6 | +3.382202558386421e-17 | 0 |
| total water (mol) | -4.4595132260225046e-7 | -4.4595132259739304e-7 | -4.857416315148192e-18 | 0 |

Exact rational values are in RESULT.json; table values are rounded. Predictor correction is excluded from accepted conservation balances. The accepted surface conduction has the correct opposite outward-face sign; its signed convective/radiative balance defect and reported residual tolerance both pass. Surface heat is not added twice.

Artifacts: audit_saved.py, actual stdout AUDIT.log, RESULT.json. No failed assertion was suppressed. This is an independent arithmetic/assembly audit of saved native outputs and a source-probe/installed equality check, not independent EOS verification, physical mobility evidence, full-inverse direction proof, material validation or time-integration accuracy certification. Material qualification stays false.
