# Independent source dry-mass caloric implementation review

Read full source_mass_caloric.py and its test file, existing ArlabosseDryCaloric source interface and InversePolicy, initial RED/GREEN records and final runtime-binding diff. Final sourceSHA2565c922d6bde3f91b466448532deed400e1c4fc32056bbdbe51f4f6a4f89c588c4; formaltest396613115da097f737388ae96206462ecebd0c28ccb9098e2765502cb6db8d46. Exact files captured in FINAL_FREEZE.json. No repository edits by reviewer.

## Numeric and source scope

ArlabosseMassCaloric reuses pinned source cp/delta_h with exactFraction temperatures; binaryfloat inputs become Fraction.from_float before calling source, preserving explicitly different binary-state semantics. Domain35–105°C, original drymixedfeed applicability and unknown fitted physicalerror remain. No molecular mass, wet volume, density, formationenergy, reaction network or newPDE invented. ΔU=Δh is explicitly the selected incompressible temperature-independent-volume approximation, not an experimental measurement ofCv. Separate source reviewer addresses scientific applicability.

FixedMassCaloricStorage binds positive fixedmass, exactdomain referenceT with u(T0)=0, assumption/sourceidentity and explicit ReactionDisabled component layout. Target is model-identity specific; differentmass/reference cannot silently reuse energy coordinates. Disabled chemistry returns zero chemical conversion only, with phase_transfer_includedFalse and no oxygen/A/B reference construction. Unknown specificvolume isNone rather than zero.

Energy, temperature, residual and Cp are returned as exact rationals, so stated zero numerical energy arithmetic error does not conceal a float-output conversion. Whole original source-domain minimumCp is positive and used for |residual|/minimum_mass_Cp inverse temperature certificate; numerical fit arithmetic error remains distinct from unknown physical fiterror. Exact endpoint targets return endpoint/zeroerror; outside-energy targets reject even if within caller numerical tolerance. Final bracket contains nominal root. Failure at iterationcap raises explicit error without fabricated result. Registry trace records cp→delta_h→massstorage with separate assumption/anchor/mass/disabled-chemistry nodes; rational value_encoding is explicit.

## Found and repaired issue

[HIGH, resolved] Initial binding trusted collaborator methods after construction without runtime exacttype checks. Independently replaced caloric.provider with a SimpleNamespace returning fakecp/delta_h; evaluation succeeded under unchanged source identity. RED test1failed0.09s preserved. The analogous parentcaloric substitution could similarly return an oldbinding while changing values.

Root added exactprovider type before callback in ArlabosseMassCaloric.binding, plus assumption and exactdomain reference checks. FixedMassCaloricStorage.binding now checks exactcaloric/chemistry types, positive exactmass and matching drylayout before callbacks. Reviewed finaldiff: these binding validations and trace value-encoding metadata are the only production changes from pre-repair file; no caloric formula, inverse threshold or scientific domain changed. New formal negative tests include callback-forbidden substitutions. Both independent actual substitution negatives now pass.

## Actual independent verification

Final independent4tests passed0.78s, independent-GREEN.log: leafprovider and parentcaloric runtime substitutions reject; independent published-coefficient polynomial evaluated at6temperatures including close endpoints agrees exactly, with true nominaltemperature inside inverse certificate/finalbracket; targets1e−200J beyond endpoints reject despite large tolerances. Prior2numeric-only tests passed0.93s before binding fix, supporting unchanged numeric behavior. Root separately reports19formal source tests; reviewer does not claim that as its own run or as installedpackage evidence. Static tools were unavailable in isolated runtime; no lint/typecheckpass claimed.

No unresolved implementation defect found after repair. Approved for parent's frozen noneditable installation verification. Scope is source-specific fixeddrymass point storage, not coupledwet-cell closure, Nylen parameter transfer, fullmaterial validation or completebrick Goal.
