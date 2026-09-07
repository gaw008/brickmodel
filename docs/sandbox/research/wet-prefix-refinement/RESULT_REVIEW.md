# Independent wet-prefix refinement result review

**APPROVE the recorded four-step partial result under its original numerical gates.** No unresolved finding from this bounded audit. This is neither a full one-second/10% wet trajectory nor strict same-source convergence evidence. Reviewed 2026-09-07 using only file reads, AST/hash checks and standard-library arithmetic; no EOS, test or experiment was rerun.

## Execution and binding

The reviewed supervisor recorded complete/exit 0, 25.56964670799789 s, unchanged inputs, leader reaped and no signaling error. Child status is completed_partial_smoke. Integration itself took 23.664395624989993 s, below its unchanged 25 s limit; child setup/postprocessing totals 25.025048334005987 s, with supervisor total below the separate 30 s wait budget. Both retained logs are empty, consistent with this quiet successful child.

All **115 declared size/before-hash/after-hash triples** match current inputs. previous-result.json is byte-identical to the earlier failed partial result; entropy_reference.py is byte-identical to the prior reviewed oracle. PLAN.json is a frozen preregistration, not a retrospective success record. The supervisor command selects current repository src, repository test helpers and this directory via explicit PYTHONPATH.

The prior assertion ASTs are all retained. Source diff confirms only initial/max step 1/128→1/256 changes temporal discretization; output identity, saving native operands and asserting exact prior initial state are the other script changes. Inventories, original motion, endpoint, inverse policy, accuracy gates and resource caps remain unchanged. The initial saved N/E/model tag matches exactly. Underlying source now includes the reviewed current-pore fix at ecfb3e9, so reduction versus the prior source revision is not a controlled same-code convergence-order measurement.

## Accepted-prefix reconstruction

Saved times are `[0,1/256,2/256,3/256,4/256]`, with four accepted step ledgers, five states, 29 evaluations and zero rejected trials. Each state retains 1 mol liquid, .01 mol carrier gas and 2 mol solid and its energy-model tag. Face energy/species, reaction species, body work and dissipation are zero.

Independent exact Fraction reconstruction reproduces every saved component prefix and inventory/energy residual. Inventory residuals are exactly zero; energy residuals are 2.0684324478909e-12, -1.3302694666303405e-11, 2.11307497107599e-11 and 4.754181054909823e-11 J, all within 1e-6 J. Each step's component-sum residual also recomputes; cumulative absolute component roundoff is 1.5113715241653028e-18 J. These checks verify all-prefix bookkeeping against recorded ledgers, not independent physical component accuracy at every prefix.

## Native-operand and endpoint checks

The saved native liquid internal energies independently reproduce the reference pore work exactly:

`Nl*M*(uf-ui) + (Ng*(Cp_g-Rmix)+Ns*Cp_s)*(Tf-T0) = 0.009269478952543691 J`.

Native u is J/kg and M is kg/mol; phase inventories and caloric constants supply the remaining molar/J units. Constant formation-energy offsets cancel. This directly resolves the prior bundle's missing-native-u audit limitation.

| Endpoint difference | Saved and independently recomputed | Original gate |
|---|---:|---:|
| Pore work | 7.359925505625448e-7 J | 1e-6 J |
| Elastic work | 5.0998818317242125e-11 J | 1e-6 J |
| Interface work | 1.800279722635236e-11 J | 1e-6 J |
| Temperature | 8.605013590567978e-9 K | 2e-5 K |
| Pressure | 1.1998112313449383e-5 Pa | .2 Pa |

All pass; body/dissipation errors are zero. Inverse settings remain 1e-6 J/1e-6 K/100 iterations. No gate was relaxed.

Native entropy operands reproduce the fixed-inventory entropy balance as -3.383434174784915e-11 J/K, versus saved -3.3834258636976366e-11 J/K, both below 1e-8 J/K. The 8.31e-17 J/K difference comes from reconstructing initial gas volume through saved NRT/P rather than retaining the oracle's original bulk-minus-liquid representation. This is offline arithmetic from shared native-provider values, not an independent EOS or interval certificate.

Endpoint lambda=0.9999275207519531 matches the original cubic smooth motion at t=1/64; bulk volume is V0*lambda^3 and phase/solid volumes reconcile. T=300.0001103613235 K and p=304582.59242255014 Pa lie within the registered reference brackets. The original final lambda=.9 remains unreached. Four prefixes have ledger closure, but only the final prefix has the independently assembled entropy/component truth in this result.

The earlier coarse run remains FAILED; this separately identified finer partial run passes. There is no active phase transfer, depletion event, full wet convergence claim or material qualification. The reported installed full-suite result is separate evidence and was not audited or rerun here.

## Frozen artifact bindings

- `PLAN.json`: `20d4d9621510995a1615b4abd683375b80a21d0adbb21e9a15809e91a6bc49bc`
- `child.py`: `6491f21e576c986144b7129b416446800ce7703cb60d0b0e9d519c8e192ad939`
- `entropy_reference.py`: `d61e40dc96253394e534123daf578a45eb288da82b8853fd017dd44fcd03c323`
- `previous-result.json`: `28579430fdca5d0ced746f01ab61773c9bcd1de296fcc30186cc8b6a1ef96d6a`
- `result.json`: `fd646b61e06ad224ba46e5ba1cad91b08b3c1c3754a96d9072abf394b7548d8f`
- `run/metadata.json`: `8e62c78d501402caec8fb9d4fd41359e588ce9a8ed0713bdc5ec312035a3cf1c`
- `run/status.json`: `6c5523a32240a2a5eca5d711d9da46c8c6f57614e7ae5b5d7af222cd98c7b582`
- `run/stdout.log`: `e3b0c44298fc1c149afbf4c8996fb92427ae41e4649b934ca495991b7852b855`
- `run/stderr.log`: `e3b0c44298fc1c149afbf4c8996fb92427ae41e4649b934ca495991b7852b855`
