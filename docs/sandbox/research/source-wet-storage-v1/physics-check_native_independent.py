"""Independent scalar closure/oracle; never calls aggregate production evaluators."""
from pathlib import Path
from fractions import Fraction as F
import importlib.util, json, hashlib, math, time
from scipy.optimize import brentq
ROOT=Path('/Users/wanggaoying/Desktop/brickmodel-github')
OUT=Path('/private/tmp/brick-source-wet-physics-v1')
FILES=['src/sludge_sandbox/source_wet_storage.py','src/sludge_sandbox/mass_wet_storage.py','src/sludge_sandbox/rigid_storage.py','src/sludge_sandbox/source_mass_caloric.py','data/sandbox/research/arlabosse2005/source.json']
def hashes(): return {p:hashlib.sha256((ROOT/p).read_bytes()).hexdigest() for p in FILES}
start=time.monotonic(); before=hashes()
spec=importlib.util.spec_from_file_location('native_config','/private/tmp/brick-source-wet-storage-v1/run_native.py')
module=importlib.util.module_from_spec(spec);spec.loader.exec_module(module)
model,state=module.make_case(ROOT)  # Configuration and admission only.
actual=json.loads(Path('/private/tmp/brick-source-wet-storage-v1/native-example.json').read_text())
water=model.fluid_template.mechanical.water
R=model.fluid_template.mechanical.gas_constant_j_mol_k
mass=F(model.dry_mass_kg); anchor=F('313.15'); volume=.001
# Printed source Eq2, independent of the production caloric adapter.
def solid(t):
    x=F(t)-F('273.15'); a=anchor-F('273.15')
    return mass*(1434*(x-a)+F('1.645')*(x*x-a*a))
def oracle(t,nl=.25,ng=(.125,.25,.00390625)):
    def close(p):
        w=water.state_tp(t,p,phase='liquid')
        return nl*w.molar_mass_kg_mol/w.density_kg_m3+sum(ng)*R*t/p-volume
    p=brentq(close,1e5,1e7,xtol=1e-8,rtol=1e-14,maxiter=80)
    w=water.state_tp(t,p,phase='liquid')
    terms=[nl*w.internal_energy_j_mol]
    for k,n in zip(('O2','N2','H2O'),ng):
        provider=model.fluid_template.gas_phases[k].caloric
        curve=provider if k=='H2O' else provider.segments[0]
        terms.append(n*curve.internal_energy_j_mol(t))
    uf=math.fsum(terms)
    return {'t':t,'p':p,'u':float(F(uf)+solid(t)),'fluid_u':uf,'closure_residual_m3':close(p)}
base=oracle(331.25)
fd={str(h):(oracle(331.25+h)['u']-oracle(331.25-h)['u'])/(2*h) for h in (.01,.005)}
delta=1/1024; shifted=(.125,.25,.00390625+delta); nl=.25-delta
shift_same_t=oracle(331.25,nl,shifted)
root=brentq(lambda t:oracle(t,nl,shifted)['u']-actual['total_internal_energy_j'],331.,331.25,xtol=1e-10,rtol=1e-14,maxiter=20)
shift=oracle(root,nl,shifted)
source_min=mass*(1434+F('3.29')*(310-F('273.15')))
cmin=source_min+sum(map(F,state.gas_amounts_mol))*20
rates=model.chemistry.evaluate(state.solid_mass_kg,state.gas_amounts_mol)
checks={
 'baseline_energy_within_reported_bound':abs(base['u']-actual['total_internal_energy_j'])<=actual['numerical_energy_error_j'],
 'pressure_within_reported_bound':abs(base['p']-actual['pressure_pa'])<=actual['pressure_error_pa'],
 'solid_exact_matches':solid(331.25)==F(actual['solid_internal_energy_j_exact']['numerator'],actual['solid_internal_energy_j_exact']['denominator']),
 'whole_domain_cmin_downrounded':F(actual['minimum_heat_capacity_j_k'])<=cmin,
 'local_closed_cp_difference_below_1e_5':max(abs(v-actual['closed_heat_capacity_j_k']) for v in fd.values())<1e-5,
 'phase_inverse_within_reported_bound':abs(root-actual['phase_shift_temperature_k'])<=actual['phase_shift_temperature_bound_k'],
 'phase_shift_cools':root<331.25,
 'phase_shift_same_temperature_requires_energy':shift_same_t['u']>base['u'],
 'water_inventory_exact_zero':F(nl)+F(shifted[2])-F(.25)-F(.00390625)==0,
 'dry_mass_unchanged':state.solid_mass_kg==(model.dry_mass_kg,),
 'chemical_rates_exact_zero':all(x==0 for x in (*rates.solid_kg_s,*rates.gas_mol_s,rates.chemical_reference_power_w)),
 'no_physical_fit_bound_or_total_h_or_solid_volume':all(actual[k] is None for k in ('fit_error','total_enthalpy_j','solid_volume_m3')) and actual['material_qualified'] is False,
 'reviewed_files_unchanged':before==hashes(),
}
result={'elapsed_seconds':time.monotonic()-start,'baseline':base,'local_closed_cp_centered_differences':fd,'exact_nominal_whole_domain_cmin':str(cmin),'independent_phase_inverse':shift,'phase_same_temperature_energy_increase_j':shift_same_t['u']-base['u'],'checks':checks,'hashes':before,'script_sha256':hashlib.sha256(Path(__file__).read_bytes()).hexdigest(),'limits':'Shared primitive water/gas providers; independent pressure root and source polynomial/aggregation. Few points, no EOS-wide certificate, fit uncertainty unknown; manufactured volume; not trajectory or material validation.'}
(OUT/'INDEPENDENT_RESULT.json').write_text(json.dumps(result,indent=2)+'\n')
print(json.dumps(result,indent=2));assert all(checks.values())
