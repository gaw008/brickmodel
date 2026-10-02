"""Frozen local diagnostics of the assumed full-cycle constitutive laws."""
from math import expm1, log

from scipy.optimize import brentq


def frozen_water_equilibrium(config, *, water_moles, sites_mol, temperature_k,
                             phase_affinity_j_mol) -> dict:
    """Classify local water phase equilibrium with all other quantities frozen.

    Inputs are scalar: n0>0, N>=0 and T>0, with the existing nonnegative
    binding energy and heat-capacity parameters. The supplied affinity is
    mu_vapor-mu_water at n0. Temperature, site inventory, vapor chemical
    potential and all non-retention contributions remain fixed as n varies.
    This conditional root is not a coupled steady state or a conserved-mass
    trajectory; bulk/pore geometry feasibility is not checked.
    """
    parameters = config['parameters']
    gas_constant = parameters['reference.R']['value']
    reference_temperature = parameters['reference.temperature']['value']
    binding_energy = parameters['water.binding_energy']['value']
    binding_capacity = parameters['water.binding_heat_capacity']['value']
    rtol = parameters['numerics.rtol']['value']
    atol = parameters['numerics.atol']['value']
    n0, sites, temperature = water_moles, sites_mol, temperature_k
    rt = gas_constant*temperature
    binding = -binding_energy+binding_capacity*(
        (temperature-reference_temperature)-temperature*log(temperature/reference_temperature))
    log_activity = log(n0/(n0+sites))
    binding_partial = binding*(sites/(n0+sites))**2
    constant = phase_affinity_j_mol+rt*log_activity+binding_partial
    result = {
        'status': None,
        'n_eq_mol': None,
        'A_j_mol': constant,
        'B_j_mol': binding,
        'reconstructed_initial_affinity_j_mol': constant-rt*log_activity-binding_partial,
        'root_residual_j_mol': None,
        'n_eq_over_n0': None,
        'identity': 'simulation',
        'constitutive_identity': 'assumed',
        'frozen_conditions': 'Temperature, site inventory, vapor chemical potential and all non-retention affinity terms are fixed; only the local liquid-water amount varies.',
        'interpretation': 'Conditional local phase-exchange equilibrium only; not a fully coupled steady state, conserved-mass path, material qualification or process qualification.',
        'global_geometry_feasibility': 'not_checked',
        'root_coordinate': 'y=-ln(n/(n+N)); dimensionless',
        'tolerance_policy': 'Root-coordinate xtol and rtol reuse root numerics.atol and numerics.rtol directly.',
        'root_coordinate_atol': atol,
        'root_coordinate_rtol': rtol,
    }
    if sites == 0:
        result['status'] = ('any_positive_water_amount_equilibrium' if phase_affinity_j_mol == 0
                            else 'no_equilibrium_zero_sites')
        return result
    if constant >= 0:
        result['status'] = ('equilibrium_only_at_infinite_water_limit' if constant == 0
                            else 'no_finite_positive_equilibrium')
        return result

    upper = -constant/rt

    def transformed_affinity(y):
        # A+RT*y written about the upper endpoint preserves its exact zero.
        return rt*(y-upper)-binding*(-expm1(-y))**2

    coordinate = brentq(transformed_affinity, 0, upper, xtol=atol, rtol=rtol)
    equilibrium = sites/expm1(coordinate)
    result.update({
        'status': 'unique_finite_positive_equilibrium',
        'n_eq_mol': equilibrium,
        'root_residual_j_mol': constant+rt*coordinate-binding*(-expm1(-coordinate))**2,
        'n_eq_over_n0': equilibrium/n0,
    })
    return result


def free_water_ledger(config, start, end, *, boundary_in_mol,
                      boundary_out_mol) -> dict:
    """Account liquid water plus pore H2O from cumulative endpoint differences.

    No conditional roots are evaluated. Free water excludes hydrogen bound in
    minerals and organics; chemical reaction water sources are explicit.
    Internal redistribution is inferred, not independently integrated.
    """
    import numpy as np

    liquid_start = np.asarray(start['liquid_water_inventory_mol'])
    liquid_end = np.asarray(end['liquid_water_inventory_mol'])
    vapor_start = np.asarray(start['gas_inventory_mol']['H2O'])
    vapor_end = np.asarray(end['gas_inventory_mol']['H2O'])
    liquid_change = liquid_end-liquid_start
    vapor_change = vapor_end-vapor_start
    liquid_reaction = np.zeros_like(liquid_start)
    vapor_reaction = np.zeros_like(vapor_start)
    reaction_water = {}
    for reaction in config['reactions']:
        name = reaction['id']
        extent = (np.asarray(end['reaction_extent_mol'][name])
                  -np.asarray(start['reaction_extent_mol'][name]))
        liquid = extent*reaction['stoichiometry'].get('water', 0)
        vapor = extent*reaction['stoichiometry'].get('H2O', 0)
        liquid_reaction += liquid
        vapor_reaction += vapor
        reaction_water[name] = {
            'signed_extent_mol_by_cell': extent.tolist(),
            'liquid_water_source_mol_by_cell': liquid.tolist(),
            'vapor_water_source_mol_by_cell': vapor.tolist(),
            'total_free_water_source_mol': float(np.sum(liquid+vapor)),
            'role': 'phase_exchange' if name == 'evaporation' else 'chemical_reaction',
        }
    redistribution = liquid_change-liquid_reaction
    net_boundary_out = boundary_out_mol-boundary_in_mol
    chemical_source = sum(item['total_free_water_source_mol'] for item in reaction_water.values()
                          if item['role'] == 'chemical_reaction')
    return {
        'identity': 'simulation', 'constitutive_identity': 'assumed',
        'start_time_s': start['time_s'], 'end_time_s': end['time_s'],
        'inventory_definition': 'Free water is liquid water plus pore-gas H2O; it is not total water-equivalent hydrogen including minerals or organics.',
        'units': 'mol of H2O; signed changes over the reported interval',
        'sign_convention': 'Reaction sources are positive into each inventory. Evaporation extent is positive liquid-to-vapor and negative for condensation. Boundary in/out are separately nonnegative; net outward is out minus in. Cell redistribution is positive for net liquid gain from internal faces; the liquid exterior is closed.',
        'accounting_basis': 'Reaction extent differences and gas boundary in/out differences use existing solver-integrated ledgers. Cell liquid redistribution is inferred as liquid inventory change minus stoichiometric liquid reaction sources; it includes numerical inventory/extent mismatch and is not an independent flux-integral check.',
        'liquid_initial_mol_by_cell': liquid_start.tolist(),
        'liquid_final_mol_by_cell': liquid_end.tolist(),
        'liquid_change_mol_by_cell': liquid_change.tolist(),
        'liquid_reaction_source_mol_by_cell': liquid_reaction.tolist(),
        'internal_liquid_redistribution_inferred_mol_by_cell': redistribution.tolist(),
        'internal_liquid_redistribution_sum_residual_mol': float(redistribution.sum()),
        'pore_vapor_initial_mol_by_cell': vapor_start.tolist(),
        'pore_vapor_final_mol_by_cell': vapor_end.tolist(),
        'pore_vapor_change_mol_by_cell': vapor_change.tolist(),
        'vapor_reaction_source_mol_by_cell': vapor_reaction.tolist(),
        'reaction_water_sources': reaction_water,
        'non_phase_chemical_free_water_source_mol': chemical_source,
        'boundary_vapor_in_mol': float(boundary_in_mol),
        'boundary_vapor_out_mol': float(boundary_out_mol),
        'boundary_vapor_net_out_mol': float(net_boundary_out),
        'pore_vapor_balance_residual_mol': float(vapor_change.sum()-vapor_reaction.sum()+net_boundary_out),
        'total_free_water_change_mol': float(liquid_change.sum()+vapor_change.sum()),
        'total_free_water_balance_residual_mol': float(liquid_change.sum()+vapor_change.sum()-liquid_reaction.sum()-vapor_reaction.sum()+net_boundary_out),
        'reaction_source_note': 'Non-phase reaction water is taken from each existing reaction stoichiometry and signed extent; retention-site loss creates no separate water source. Internal liquid and gas transfers cancel in whole-domain water accounting.',
    }


def drying_water_diagnostics(config, start, end, *, boundary_in_mol,
                             boundary_out_mol) -> dict:
    """Evaluate same-state conditional roots only at the drying endpoint."""
    cells = []
    for i, (water, sites, temperature, affinity) in enumerate(zip(
            end['liquid_water_inventory_mol'], end['water_retention_sites_mol'],
            end['temperature_k'], end['water_phase_affinity_j_mol'])):
        inputs = {'water_moles': float(water), 'sites_mol': float(sites),
                  'temperature_k': float(temperature),
                  'phase_affinity_j_mol': float(affinity)}
        cells.append({'cell_index': i, 'x_m': end['x_m'][i], 'inputs': inputs,
                      'conditional_equilibrium': frozen_water_equilibrium(config, **inputs)})
    return {
        'identity': 'simulation', 'constitutive_identity': 'assumed',
        'stage': 'drying', 'start_time_s': start['time_s'], 'end_time_s': end['time_s'],
        'end_state_cells': cells,
        'global_geometry_feasibility': 'not_checked',
        'interpretation': 'Same-state conditional roots at drying end only; no coupled steady-state, conserved-mass path or material/process qualification is inferred.',
        'free_water_ledger': free_water_ledger(
            config, start, end, boundary_in_mol=boundary_in_mol,
            boundary_out_mol=boundary_out_mol),
    }


def gas_species_ledger(config, start, end, *, reference_inventory_mol) -> dict:
    """Audit global gas-species endpoint balances using existing net ledgers.

    Endpoint inputs hold scalar totals in mol. The physical host supplies
    positive inventories, including the declared-process initial reference for each
    gas species. Reaction extent changes are interval signed net progress,
    not gross forward/reverse throughput. Internal faces cancel globally;
    this is neither a local independent flux integral nor an interval-maximum
    residual check. Its verdict is separate from existing physical verdicts.
    """
    extent_changes = {reaction['id']:
        end['reaction_extent_mol'][reaction['id']]-start['reaction_extent_mol'][reaction['id']]
        for reaction in config['reactions']}
    threshold = config['parameters']['acceptance.balance_relative']['value']
    species = {}
    for item in config['species']:
        if item['phase'] != 'gas':
            continue
        name = item['id']
        initial = start['gas_inventory_mol'][name]
        final = end['gas_inventory_mol'][name]
        change = final-initial
        sources = {reaction['id']:extent_changes[reaction['id']]*reaction['stoichiometry'].get(name,0)
                   for reaction in config['reactions']}
        source = sum(sources.values())
        inflow = end['boundary_in_mol'][name]-start['boundary_in_mol'][name]
        outflow = end['boundary_out_mol'][name]-start['boundary_out_mol'][name]
        residual = change-source-inflow+outflow
        budget = max(abs(initial),abs(final),sum(abs(value) for value in sources.values()),
                     abs(inflow)+abs(outflow))
        reference = reference_inventory_mol[name]
        species[name] = {
            'initial_inventory_mol':initial, 'final_inventory_mol':final,
            'inventory_change_mol':change,
            'reaction_sources_mol':sources, 'reaction_net_source_mol':source,
            'boundary_in_mol':inflow, 'boundary_out_mol':outflow,
            'boundary_net_out_mol':outflow-inflow,
            'residual_mol':residual, 'absolute_residual_mol':abs(residual),
            'budget_scale_mol':budget, 'reference_inventory_mol':reference,
            'budget_relative_residual':abs(residual)/budget,
            'reference_relative_residual':abs(residual)/reference,
            'passed':bool(abs(residual)/budget < threshold),
        }
    return {
        'identity':'simulation', 'start_time_s':start['time_s'], 'end_time_s':end['time_s'],
        'reaction_extent_delta_mol':extent_changes, 'species':species,
        'acceptance_balance_relative':threshold,
        'passed':all(item['passed'] for item in species.values()),
        'definitions':{
            'residual':'End minus start inventory minus stoichiometric reaction net source minus boundary inflow plus boundary outflow; all amounts in mol.',
            'budget_scale':'max(abs(start inventory),abs(end inventory),sum(abs(each reaction interval net source)),abs(boundary in)+abs(boundary out)); no floors.',
            'reference_scale':'Initial inventory of this gas species at the start of the declared process window, reused for every stage; for a full-cycle configuration this is the full-cycle initial inventory. This normalization is distinct from the budget scale and is not the pass criterion.',
            'boundary_direction':'In/out label the theoretical nonnegative directional flux integrals. Recorded cumulative endpoint differences are used unchanged, including any small negative numerical increments; no clipping or absolute-value replacement is applied to balance amounts.',
            'reaction_progress':'Signed interval net reaction progress from cumulative extents; neither reaction sources nor their absolute sums measure gross forward/reverse traffic.',
            'scope':'Global internal faces cancel; endpoint residual only, not a local independent flux integration or the maximum residual within the interval.',
            'verdict':'Absolute residual divided by budget scale must be strictly below the existing acceptance.balance_relative. This report does not change prior conservation, physical or process-endpoint verdicts.',
        },
    }


def calcium_phase_ledger(config, start, end) -> dict:
    """Audit saved per-cell phase inventories against independent extents.

    All quantities are interval signed net amounts in mol. The global residual
    is the sum of cell residuals, preserving the existing phase audit's order
    of arithmetic. A zero budget leaves its relative verdict unqualified.
    """
    import numpy as np

    threshold = config['parameters']['acceptance.balance_relative']['value']
    species = {}
    for name in ('calcite', 'lime', 'portlandite'):
        initial = np.asarray(start[name+'_inventory_mol'])
        final = np.asarray(end[name+'_inventory_mol'])
        change = final-initial
        sources = {reaction['id']:
            (np.asarray(end['reaction_extent_mol'][reaction['id']])
             -np.asarray(start['reaction_extent_mol'][reaction['id']]))
            *reaction['stoichiometry'].get(name, 0.)
            for reaction in config['reactions']}
        residual = change-sum(sources.values())
        cell_budget = np.maximum.reduce([
            np.abs(initial), np.abs(final), sum(np.abs(x) for x in sources.values())])
        budget = max(abs(float(initial.sum())), abs(float(final.sum())),
                     sum(abs(float(x.sum())) for x in sources.values()))
        signed_global = float(residual.sum())
        reference = float(initial.sum())
        relative = abs(signed_global)/budget if budget != 0 else None
        passed = bool(relative is not None and relative < threshold)
        species[name] = {
            'initial_mol_by_cell':initial.tolist(), 'final_mol_by_cell':final.tolist(),
            'signed_change_mol_by_cell':change.tolist(),
            'signed_sources_mol_by_reaction':{key:value.tolist() for key,value in sources.items()},
            'signed_residual_mol_by_cell':residual.tolist(),
            'signed_global_residual_mol':signed_global,
            'absolute_global_residual_mol':abs(signed_global),
            'saved_global_residual_exact_zero':signed_global == 0,
            'saved_cell_residuals_all_exact_zero':bool(np.all(residual == 0)),
            'budget_mol':budget, 'budget_relative':relative,
            'initial_inventory_mol':reference,
            'initial_relative':abs(signed_global)/abs(reference) if reference != 0 else None,
            'initial_relative_undefined_reason':'zeroactualinitial' if reference == 0 else None,
            'initial_reference_status':'undefined_zero_reference' if reference == 0 else 'defined',
            'cell_budget_mol':cell_budget.tolist(),
            'cell_budget_relative':[abs(float(x))/float(b) if b != 0 else None
                                    for x,b in zip(residual,cell_budget)],
            'passed':passed, 'undefined_budget_not_qualified':relative is None,
            'relative_status':('undefined_zero_budget' if relative is None
                               else 'passed' if passed else 'failed'),
        }
    return {
        'identity':'simulation', 'start_time_s':start['time_s'], 'end_time_s':end['time_s'],
        'species':species, 'acceptance_balance_relative':threshold,
        'passed':all(item['passed'] for item in species.values()),
        'relative_status':('failed' if any(item['relative_status'] == 'failed' for item in species.values())
                           else 'undefined_zero_budget' if any(item['undefined_budget_not_qualified'] for item in species.values())
                           else 'passed'),
    }


def calcium_phase_ledger_report(config, endpoints) -> dict:
    """Report the declared window and its stages from existing endpoint rows."""
    return {
        'schema':'sludge_vme_calcium_phase_ledger_v1',
        'scope':{'stages':list(config['stages']),
                 'start_time_s':endpoints[0]['time_s'], 'end_time_s':endpoints[-1]['time_s'],
                 'whole_cycle_meaning':'Entire declared process window only; omitted stages are not covered.'},
        'whole_cycle':calcium_phase_ledger(config, endpoints[0], endpoints[-1]),
        'stages':{name:calcium_phase_ledger(config, endpoints[i], endpoints[i+1])
                  for i,name in enumerate(config['stages'])},
        'definitions':{
            'residual':'Per-cell end minus start inventory minus each signed stoichiometric interval reaction source; global residual is the sum of these cell residuals.',
            'cell_budget':'max(abs(cell start), abs(cell end), sum(abs(each cell reaction source))); mol, no floor.',
            'global_budget':'max(abs(sum(start)), abs(sum(end)), sum(abs(sum(each reaction source)))); mol. This is the existing phase budget, not a Ca-pool or gas-species scale.',
            'reference':'Signed start inventory summed across cells for this interval; its absolute value normalizes initial_relative. A zero actual initial inventory is explicitly undefined.',
            'extent':'Independent integrated reaction_extent_mol slots, including active direct carbonation; signed net progress, not inferred from phase inventories or gross forward/reverse traffic.',
            'relative_verdict':'Only defined abs(global residual)/global budget below root acceptance.balance_relative passes. Zero budget yields null and passed=false; an absolute saved zero is a separate observation.',
            'scope':'Saved endpoint arithmetic only, not continuous positivity, local transport closure, or an interval-maximum residual. Existing physical, process and whole-project flags are unchanged.',
        },
    }


def water_reference_observables(model, fields, temperature_k) -> dict:
    """Intrinsic sorption observables at the root pure-liquid pressure reference.

    This uses the active host mixing/binding chemical potential and its partial
    enthalpy. Dry composition/site coordinates are held fixed. The reference
    excludes capillary, skeleton-stress and gas-mixture pressure contributions;
    it is NOT a mechanically feasible full-brick equilibrium or drying path.
    Total desorption enthalpy includes vaporization once. No integration,
    equilibrium root, parameter fit, or additional heat source is introduced.
    Arrays and complex temperatures are retained for derivative verification.
    """
    import numpy as np

    temperature = np.asarray(temperature_k)
    mixing_log_activity, _ = model.water_retention(fields)
    binding = model.water_binding(temperature, fields)
    h, s = model.thermo(temperature)
    liquid = model.water_index
    vapor = model.names.index('H2O')
    # Host condensed h includes (P-Pr)*v; expose the declared Pr reference.
    liquid_h = h[..., liquid]-(model.P-model.Pr)*model.v[liquid]
    liquid_g = liquid_h-temperature*s[..., liquid]
    vapor_g = h[..., vapor]-temperature*s[..., vapor]
    chemical_shift = model.R*temperature*mixing_log_activity+binding['mu']
    log_activity = mixing_log_activity+binding['mu']/(model.R*temperature)
    pure_vaporization_h = h[..., vapor]-liquid_h
    desorption_h = pure_vaporization_h-binding['partial_h']
    return {
        'log_activity':log_activity,
        'activity':np.exp(log_activity),
        'mixing_log_activity':mixing_log_activity,
        'binding_mu_j_mol':binding['mu'],
        'chemical_shift_j_mol':chemical_shift,
        'reference_liquid_mu_j_mol':liquid_g+chemical_shift,
        'reference_vapor_mu_j_mol':vapor_g,
        'pure_vaporization_h_j_mol':pure_vaporization_h,
        'binding_partial_h_j_mol':binding['partial_h'],
        'total_desorption_h_j_mol':desorption_h,
        'total_desorption_heat_j_kg_water':desorption_h/model.mw[liquid],
    }


def caloric_reference_observables(model, temperature_k):
    """Pure background/phase caloric output at root reference pressure.

    This uses the host's equilibrium caloric functions, excluding binding,
    elasticity, gas mixing and the dynamic matrix phase coordinate. Matrix
    output is therefore an effective equilibrium proxy, not pure metakaolin.
    Condensed pressure offsets are removed explicitly. No trajectory is run.
    """
    import numpy as np

    temperature = np.asarray(temperature_k)
    h, s = model.thermo(temperature)
    h[..., :len(model.ns)] -= (model.P-model.Pr)*model.v
    cp = np.broadcast_to(model.cp, temperature.shape+(len(model.names),)).astype(
        np.result_type(temperature, float), copy=True)
    cp[..., len(model.ns):] = model.gas_molar_cp(temperature)
    cp[..., model.water_index] = model.water_background_cp(temperature)
    cp[..., model.dry_caloric_indices] = model.dry_background_cp(temperature)
    cp[..., model.quartz] = model.quartz_thermo(temperature)[0]
    cp[..., model.matrix] += model.liquid_active*model.liquid_phase(temperature)[2]
    return {'cp_j_mol_k': cp, 'h_j_mol': h, 's_j_mol_k': s}


def carbonate_reverse_time_coordinate(model, carbonate_fraction):
    """Analytic clock for the fixed-condition reverse-only carbonate law.

    For dx/dt=k*(1-x)/(1+beta*(1-x)), F(x)-F(x0)=k*(t-t0).
    x must be the declared conserved-pool fraction below unity. Converting
    source uptake with an approximate capacity yields only a conditional
    shape diagnostic, not an identified active Ca inventory or full host.
    """
    import numpy as np

    x = np.asarray(carbonate_fraction)
    return -np.log1p(-x)+model.carbonate_phase_resistance*x


def caloric_source_domain_coverage(model, rows, names):
    """Actual sampled temperature coverage; no truncation or domain repair."""
    import numpy as np

    temperatures = np.asarray([row['temperature_k'] for row in rows])
    result = {}
    for name in names:
        domain = model.config['caloric_background']['species_domains'][name]
        lower, upper = domain['source_temperature_range_k']
        result[name] = {
            'source_temperature_range_k': [lower, upper],
            'sampled_temperature_range_k': [float(temperatures.min()), float(temperatures.max())],
            'cell_time_samples': int(temperatures.size),
            'below_source_samples': int(np.count_nonzero(temperatures < lower)),
            'above_source_samples': int(np.count_nonzero(temperatures > upper)),
            'outside_source_status': 'assumed polynomial continuation; source accuracy not granted',
            'coverage_note': 'Counts sampled constitutive evaluations, including depleted species; no guarantee between output nodes.',
        }
    return result


def viscosity_source_domain_coverage(model, rows):
    """Reconstruct the same sampled Darcy face temperature from saved rows."""
    import numpy as np

    temperatures = []
    for row in rows:
        left = np.asarray(row['temperature_k'])
        right = np.r_[left[1:], row['kiln_temperature_k']]
        ratio = (left-right)/right
        temperatures.append(left*np.divide(np.log1p(ratio), ratio,
                                            out=np.ones_like(ratio), where=ratio != 0))
    temperatures = np.asarray(temperatures)
    result = {}
    for name in model.ng:
        domain = model.config['viscosity_background']['species_domains'][name]
        lower, upper = domain['source_temperature_range_k']
        result[name] = {
            'source_temperature_range_k': [lower, upper],
            'domain_kind': domain['domain_kind'],
            'sampled_face_temperature_range_k': [float(temperatures.min()), float(temperatures.max())],
            'face_time_samples': int(temperatures.size),
            'below_source_samples': int(np.count_nonzero(temperatures < lower)),
            'above_source_samples': int(np.count_nonzero(temperatures > upper)),
            'source_law_weight': model.viscosity_mixing,
            'outside_source_status': model.config['viscosity_background']['outside_domain_status'],
            'coverage_note': 'Sampled reciprocal-log Darcy face temperatures, including reservoir face and species with small fractions; no statement about every solver evaluation or finite-density/pore validity.',
        }
    return result


def binary_diffusion_source_domain_coverage(model, rows):
    """Sample actual pair-face conditions; no claim about every solver iterate."""
    import numpy as np

    temperatures, pressures, water = [], [], []
    for row in rows:
        left = np.asarray(row['temperature_k'])
        right = np.r_[left[1:], row['kiln_temperature_k']]
        ratio = (left-right)/right
        temperatures.append(left*np.divide(np.log1p(ratio), ratio,
                                            out=np.ones_like(ratio), where=ratio != 0))
        pressure = np.asarray(row['pressure_pa'])
        pressures.append((pressure+np.r_[pressure[1:], model.P])/2)
        water.extend(row['gas_mole_fractions']['H2O'])
    temperatures, pressures = np.asarray(temperatures), np.asarray(pressures)
    background = model.config['binary_diffusion_background']
    pairs = {}
    for name, domain in background['pair_domains'].items():
        lower, upper = domain['source_temperature_range_k']
        pairs[name] = {
            **domain,
            'sampled_face_temperature_range_k': [float(temperatures.min()), float(temperatures.max())],
            'face_time_samples': int(temperatures.size),
            'below_source_samples': int(np.count_nonzero(temperatures < lower)),
            'above_source_samples': int(np.count_nonzero(temperatures > upper)),
            'outside_source_status': background['outside_domain_status'],
        }
    return {
        'pairs': pairs,
        'sampled_face_pressure_range_pa': [float(pressures.min()), float(pressures.max())],
        'sampled_internal_water_mole_fraction_range': [float(min(water)), float(max(water))],
        'composition_extension_status': background['composition_extension_status'],
        'pressure_extension_status': background['pressure_extension_status'],
        'coverage_note': 'Includes external reservoir face, strict source endpoints included. Saved nodes only; finitewater and pore applicability are not established by temperature coverage.',
    }
