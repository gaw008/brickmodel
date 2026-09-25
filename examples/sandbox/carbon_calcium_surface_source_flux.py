"""Source-only double-precision surface reconstruction for full quadratures."""
import math

from scipy.optimize import brentq

from carbon_calcium_radiation_reference import RadiationSource
from carbon_calcium_source_audit import independent_exchange
from review_carbon_calcium_open_cell import source_bath


def solve_float(source, bulk, reservoir, interior, exterior, radiation, settings):
    names = exterior['gas_order']
    tb,tc = reservoir['temperature_k'],bulk['temperature_k']
    li,lo = interior['gas_mobilities_mol2_k_j_s'],exterior['gas_mobilities_mol2_k_j_s']
    rad_source = RadiationSource(radiation)

    def state(temperature):
        standard = source_bath(source,temperature,source.p0,{k:1. for k in names})
        potentials,flows = {},{}
        for k in names:
            a = reservoir['mu'][k]/tb+(reservoir['h'][k]+standard['h'][k])/2*(1/temperature-1/tb)
            b = bulk['mu'][k]/tc-(bulk['h'][k]+standard['h'][k])/2*(1/tc-1/temperature)
            potentials[k] = (lo[k]*a+li[k]*b)/(lo[k]+li[k])
            flows[k] = lo[k]*li[k]/(lo[k]+li[k])*(a-b)
        rad = rad_source.flux(temperature,radiation['reservoir_temperature_k'])
        residual = math.fsum([exterior['heat_conductance_w_k']*(tb-temperature),
            -interior['heat_conductance_w_k']*(temperature-tc),rad['energy_in_w']]
            +[(reservoir['h'][k]-bulk['h'][k])/2*flows[k] for k in names])
        return residual,potentials,standard,rad

    policy = settings['numerics']
    temperature = brentq(lambda t:state(t)[0],*settings['surface_temperature_domain_k'],
        xtol=policy['temperature_absolute_tolerance_k'],rtol=policy['temperature_relative_tolerance'],
        maxiter=policy['maximum_root_iterations'])
    _,potentials,standard,rad = state(temperature)
    partial = {k:source.p0*math.exp((potentials[k]-standard['mu'][k]/temperature)/source.r) for k in names}
    pressure = math.fsum(partial.values())
    surface = source_bath(source,temperature,pressure,{k:v/pressure for k,v in partial.items()})
    surface.update(pressure_pa=pressure,partial_pressures_pa=partial)
    outer,inner = independent_exchange(reservoir,surface,exterior),independent_exchange(surface,bulk,interior)
    species = {k:outer['gas'][k]-inner['gas'][k] for k in names}
    energy = outer['energy']+rad['energy_in_w']-inner['energy']
    entropy = outer['entropy'][1]+inner['entropy'][0]+rad['body_entropy_rate_w_k']
    production = math.fsum([outer['dissipation'],inner['dissipation'],rad['entropy_production_w_k']])
    return {'surface':surface,'outer':outer,'inner':inner,'radiation':rad,
        'species_residuals_mol_s':species,'energy_residual_w':energy,'surface_entropy_w_k':entropy,
        'production_w_k':production}
