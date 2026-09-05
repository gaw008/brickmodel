"""Inventory-based diagnostic thresholds, never rate-based burnout."""
from solver import surface_oxygen

NOT_MODELLED = {name: "not_modelled" for name in (
    "t_close", "pressure", "temperature_field", "energy_conservation", "reaction_heat",
    "shrinkage", "open_closed_porosity", "water", "dehydroxylation", "pyrolysis", "CO",
    "other_volatiles", "strength", "black_core_classification", "emission_compliance",
    "kiln_speed", "recipe_optimization")}
ASSUMPTIONS = [
    "dimensionless_mechanism_scenario_not_measured_or_literature_fit",
    "isothermal_external_thermostat_no_energy_balance",
    "fixed_geometry_uniform_open_porosity_symmetric_half_slab",
    "C_is_declared_oxidizable_carbon_not_TG_residue_LOI_or_all_sludge_organics",
    "C(s)+O2->CO2_only", "q=Gamma*K*f*u_assumed_closure_not_identified_intrinsic_kinetics",
    "approximate_equimolar_transport_same_constant_O2_CO2_D_and_film_coefficient",
    "N2_inert_constant_background_not_an_integrated_species",
    "infinite_reservoir_has_finite_film_transfer_not_finite_total_oxygen",
    "finite_reservoir_closed_no_makeup_no_vent_no_reset",
    "sealed_has_no_exchange_or_reservoir_state",
    "95_and_99_percent_are_diagnostic_not_factory_standards",
    "no_physical_seconds_or_factory_material_parameter_mapping",
]
NORMALIZATION = {
    "xi": "x/L, symmetric core 0 to surface 1",
    "tau": "t*D_eff/(epsilon_o*L^2)", "tau_D": "epsilon_o*L^2/D_eff",
    "D_eff_basis": "total_cross_section", "gas_concentration_basis": "pore_volume",
    "u": "c_O2/c_star", "v": "c_CO2/c_star", "f": "C_s/C_s0",
    "Gamma": "C_s0/(epsilon_o*c_star)", "K": "k*tau_D", "Bi": "h_m*L/D_eff",
    "reservoir_ratio": "V_res/(epsilon_o*A*L)",
    "inventory_unit": "epsilon_o*A*L*c_star", "flux_sign": "outward_positive",
    "mass_stoichiometry_only": {"C": 12, "O2": 32, "CO2": 44},
}


def timeseries_rows(result):
    cfg = result.config
    rows = []
    for rec in result.records:
        s = rec.state
        rows.append(dict(scenario_id=cfg.scenario_id, tau=rec.tau,
                         u_core=s.u[0], u_surface=surface_oxygen(s, cfg),
                         carbon_mean=sum(s.f)/cfg.n_cells, carbon_max=max(s.f),
                         co2_body=sum(s.v)/cfg.n_cells, co2_generated=s.generated,
                         co2_net_out=s.net_v, u_res=s.u_res, v_res=s.v_res))
    return rows


def first_crossing(rows, key, remaining_threshold):
    for previous, current in zip(rows, rows[1:]):
        if current[key] <= remaining_threshold:
            fraction = (previous[key]-remaining_threshold)/(previous[key]-current[key])
            return previous["tau"] + fraction*(current["tau"]-previous["tau"])
    return None


def summarize(result) -> dict:
    cfg = result.config
    rows = timeseries_rows(result)
    rho = cfg.reservoir_ratio
    available = None if cfg.boundary_mode == "infinite" else 1+(rho or 0)
    upper = 1.0 if available is None else min(1.0, available/cfg.Gamma)
    summary: dict = dict(scenario_id=cfg.scenario_id, scope=cfg.scope, config=cfg.to_dict(),
                   assumptions=ASSUMPTIONS, normalization=NORMALIZATION,
                   not_modelled=NOT_MODELLED, parameter_evidence="hypothetical_dimensionless",
                   transport_model="approximate_equimolar_transport",
                   budget=dict(initial_body_oxygen=1.0, initial_reservoir_oxygen=rho,
                               initial_solid_carbon=cfg.Gamma, total_available_oxygen=available,
                               oxygen_supply="unbounded" if available is None else "closed_inventory",
                               max_conversion_upper_bound=upper),
                   discretization=dict(method="cell_centered_FV_SSPRK2", n_cells=cfg.n_cells,
                                       dt_max=result.dt_max, steps=result.steps,
                                       u_core_location="first_cell_average_xi=1/(2*n_cells)",
                                       u_surface_location="Robin_half_cell_reconstruction_xi=1",
                                       event_method="linear_interpolation_of_exported_samples",
                                       maximum_event_bracket_width=max(b["tau"]-a["tau"] for a,b in zip(rows,rows[1:]))))
    for percent in (95, 99):
        threshold = 1-percent/100
        for key, metric in ((f"t_burn{percent}", "carbon_mean"),
                            (f"t_local_burn{percent}", "carbon_max")):
            tau = first_crossing(rows, metric, threshold)
            summary[key] = tau
            summary[key+"_status"] = ("reached_diagnostic_threshold" if tau is not None
                                      else "oxygen_budget_limited" if upper < percent/100
                                      else "not_reached_by_horizon")
    summary["status"] = summary["t_burn99_status"]
    summary["t_gen"] = dict(species="CO2_only", basis="fraction_of_initial_declared_carbon_potential",
                            t95=summary["t_burn95"], t99=summary["t_burn99"],
                            status95=summary["t_burn95_status"], status99=summary["t_burn99_status"],
                            interpretation="source_completion_not_net_outflow_completion")
    s = result.records[-1].state
    final = dict(rows[-1])
    final.update(co2_source_rate=cfg.Gamma*cfg.K*sum(f*u for f,u in zip(s.f,s.u))/cfg.n_cells,
                 solid_carbon_body=cfg.Gamma*final["carbon_mean"],
                 oxygen_body=sum(s.u)/cfg.n_cells, carbon_element_body=cfg.Gamma*final["carbon_mean"]+final["co2_body"],
                 oxygen_equivalents_body=sum(u+v for u,v in zip(s.u,s.v))/cfg.n_cells,
                 co2_reservoir=None if rho is None else rho*s.v_res,
                 oxygen_reservoir=None if rho is None else rho*s.u_res,
                 max_local_meets_95=final["carbon_max"] <= .05,
                 max_local_meets_99=final["carbon_max"] <= .01)
    summary["final"] = final
    return summary
