"""Check actual upwind liquid faces against the independent continuum file."""
from dataclasses import replace
import hashlib
import json
import math
from pathlib import Path

from sludge_sandbox.liquid_transport import LiquidTransportState,SaturationMobilityTable,LiquidConnection,liquid_face_exchange
from sludge_sandbox.phase_storage import LiquidWaterPhase
from sludge_sandbox.water_properties import load_water_properties

ROOT=Path(__file__).resolve().parents[3]


def main():
    reference_path=Path(__file__).with_name('liquid_face_continuum_reference.json')
    ref=json.loads(reference_path.read_text())
    water=load_water_properties(ROOT/'data/sandbox/water')
    assert dict(water.source_asset_sha256)==ref['water_source_asset_sha256']
    for name,expected in ref['hashes'].items():
        assert hashlib.sha256((ROOT/name).read_bytes()).hexdigest()==expected,name
    plan=Path(__file__).with_name('LIQUID_FACE_CONTINUUM_PLAN.md')
    relation=SaturationMobilityTable(saturation_knots=(0.,1.),permeability_m2=(1e-17,)*2,
        relative_permeability=(1.,)*2,viscosity_pa_s=(.001,)*2,
        temperature_range_k=(299.,301.),pressure_range_pa=(1e5,6e7),model_id='manufactured:continuum-mobility',
        version='1',classification='manufactured_test_fixture',source_ids=('manufactured:continuum-plan',),
        source_asset_sha256=((str(plan.relative_to(ROOT)),hashlib.sha256(plan.read_bytes()).hexdigest()),),
        relation_kind='frozen_manufactured')
    connection=LiquidConnection(status='connected',connection_id='manufactured:connected',version='1',
        classification='manufactured_test_fixture',source_ids=('manufactured:continuum-plan',))
    def state(point):
        return LiquidTransportState(temperature_k=300.,pressure_pa=point['pressure_pa'],inventory_mol=1.,
            saturation=.5,pressure_error_pa=10.,molar_volume_m3_mol=point['molar_volume_m3_mol'],
            enthalpy_j_mol=point['enthalpy_j_mol'],metadata=LiquidWaterPhase(water).metadata,
            provider_id='iapws95_real_fluid_helmholtz',provider_version='1.5.5',
            source_asset_sha256=tuple(sorted(water.source_asset_sha256.items())))
    rows=[]
    exact=ref['exact_molar_flow_mol_s']
    for cells in (4,8,16,32):
        faces=[]
        for i in range(cells):
            left=state(ref['points'][str(i*32//cells)])
            right=state(ref['points'][str((i+1)*32//cells)])
            options=dict(left_relation=relation,right_relation=relation,connection=connection,
                area_m2=ref['area_m2'],left_distance_m=ref['length_m']/cells/2,
                right_distance_m=ref['length_m']/cells/2,allow_manufactured=True)
            forward=liquid_face_exchange(left,right,**options)
            reverse=liquid_face_exchange(right,left,**options)
            expected_energy=forward.molar_flow_mol_s*left.enthalpy_j_mol
            energy_error=abs(forward.enthalpy_flow_w-expected_energy)
            reverse_energy_error=abs(reverse.enthalpy_flow_w-reverse.molar_flow_mol_s*left.enthalpy_j_mol)
            faces.append(dict(face=i,pressure_left_pa=left.pressure_pa,pressure_right_pa=right.pressure_pa,
                molar_flow_mol_s=forward.molar_flow_mol_s,exact_molar_flow_mol_s=exact,
                relative_error=abs(forward.molar_flow_mol_s-exact)/abs(exact),enthalpy_flow_w=forward.enthalpy_flow_w,
                donor=forward.donor,reverse_donor=reverse.donor,reverse_molar_flow_mol_s=reverse.molar_flow_mol_s,
                enthalpy_identity_error_w=energy_error,reverse_enthalpy_identity_error_w=reverse_energy_error,
                passed_local=(forward.donor=='left' and reverse.donor=='right'
                    and math.isclose(reverse.molar_flow_mol_s,-forward.molar_flow_mol_s,rel_tol=1e-12,abs_tol=0.)
                    and energy_error<=1e-8+1e-12*abs(expected_energy)
                    and reverse_energy_error<=1e-8+1e-12*abs(expected_energy))))
        rows.append(dict(intervals=cells,max_relative_error=max(v['relative_error'] for v in faces),faces=faces))
    ratios=[a['max_relative_error']/b['max_relative_error'] if b['max_relative_error'] else None
        for a,b in zip(rows,rows[1:])]
    right=state(ref['points']['32'])
    left=replace(right,pressure_pa=right.pressure_pa+1.)
    uncertain=liquid_face_exchange(left,right,left_relation=relation,right_relation=relation,connection=connection,
        area_m2=.01,left_distance_m=.05,right_distance_m=.05,allow_manufactured=True)
    uncertain_ok=(uncertain.molar_flow_mol_s>0 and uncertain.direction_qualification=='nominal_direction_not_certified'
        and uncertain.pressure_interval_scope=='fixed_decoded_temperature' and not uncertain.full_inverse_direction_certified)
    passed=(all(face['passed_local'] for row in rows for face in row['faces'])
        and all(r is not None and r>=1.7 for r in ratios) and rows[-1]['max_relative_error']<=.002 and uncertain_ok)
    paths=[Path(__file__),reference_path,plan,ROOT/'src/sludge_sandbox/liquid_transport.py']
    output=dict(classification='manufactured_mobility_pure_water_discretization_not_material_validation',passed=passed,
        refinement_ratios=ratios,grids=rows,uncertain_pressure_nominal_flow_preserved=uncertain_ok,
        quadrature_relative_difference=ref['quadrature_relative_difference'],
        qualification='quad16_vs32_is_consistency_check_not_rigorous_error_bound',
        hashes={str(p.relative_to(ROOT)):hashlib.sha256(p.read_bytes()).hexdigest() for p in paths})
    Path(__file__).with_suffix('.json').write_text(json.dumps(output,indent=2,allow_nan=False)+'\n')
    print(json.dumps(dict(passed=passed,ratios=ratios,max_relative_errors=[row['max_relative_error'] for row in rows],
        uncertain_pressure_nominal_flow_preserved=uncertain_ok),indent=2))
    return 0 if passed else 1


if __name__=='__main__':raise SystemExit(main())
