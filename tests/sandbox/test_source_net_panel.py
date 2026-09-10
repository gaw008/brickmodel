"""Artificial saved-rate tests. No provider construction, inverse or EOS."""
from dataclasses import replace
from fractions import Fraction as F
import unittest
import numpy as np
import pytest
from sludge_sandbox.source_net_panel import SavedSourceSample,build_source_panel
from sludge_sandbox.exact_event_clock import ExactEventTime as T
from sludge_sandbox.exact_source_column import SourceExactEvaluation
from sludge_sandbox.integration import ConservedState,Rates
from sludge_sandbox.mass_wet_storage import WetMixedState
from sludge_sandbox.mass_wet_transport import WetPhaseEvaluation
from sludge_sandbox.source_mass_caloric import DisabledChemicalRates
from sludge_sandbox.source_wet_column import SourceColumnCell,LiquidSourceColumnRates,LiquidColumnFaceRate

OP=('exact_source_column_v1','a'*64,('liquid_water','O2','N2','H2O'))
ENERGY=('source_column_fixed_dry_energy_v1',('b'*64,)*3,OP[2])
MASSES=(.125,)*3


def sample(at,liquid_faces=(0.,1.,.5,0.),phase=(0.,0.,0.),role='first',liquid=2.):
    states=tuple(WetMixedState((MASSES[i],),liquid,(1.,2.,3.),100.+i,'b'*64) for i in range(3))
    packed=ConservedState(np.array([(s.liquid_water_mol,*s.gas_amounts_mol) for s in states]),
                          np.array([s.internal_energy_j for s in states]),ENERGY)
    faces=[]
    for i in range(4):
        gas=(0.,0.,0.) if i in (0,3) else (i*.125,-i*.25,i*.5)
        faces.append(LiquidColumnFaceRate(face_id=i,left_cell=i-1 if i else None,right_cell=i if i<3 else None,
            gas_mol_s=gas,energy_w=float(i+1),conduction_w=float(i+1),diffusive_enthalpy_w=(0.,)*3,
            advective_enthalpy_w=(0.,)*3,shared_evaluation=None,liquid_mol_s=liquid_faces[i],
            liquid_enthalpy_w=0.,liquid_enthalpy_projection_w=F(),liquid_exchange=None))
    cells=tuple(SourceColumnCell(None,WetPhaseEvaluation(v,1.,None,None,None),
                                DisabledChemicalRates((F(),),(F(),)*3)) for v in phase)
    raw=LiquidSourceColumnRates(cells=cells,gas_states=(),faces=tuple(faces),model_identity=OP[1],
        source_ids=('manufactured:rate-record-only',),liquid_states=())
    rates=Rates(np.array([(f.liquid_mol_s,*f.gas_mol_s) for f in faces]),
                np.array([f.energy_w for f in faces]),np.array([(-v,0.,0.,v) for v in phase]),np.zeros(3))
    return SavedSourceSample(packed,SourceExactEvaluation(T(at),states,raw,rates,OP),role)


def panel(first=None,interior=None,origin=F()):
    return build_source_panel(first or sample(origin),interior or sample(origin+F(1,2),role='interior'),
        T(origin+1),operator_identity=OP,energy_identity=ENERGY,fixed_dry_mass_kg=MASSES)


class SourcePanelTests(unittest.TestCase):
    def test_drainage_without_evaporation(self):
        p=panel();self.assertEqual(p.inventories[0].linear,F(-1))
        self.assertEqual(p.inventories[0].quadratic,0)
        self.assertEqual(p.inventories[0].minimum(F(1)),(F(1),F(1)))

    def test_drainage_exceeds_condensation(self):
        p=panel(sample(F(),phase=(-.25,0.,0.)),sample(F(1,2),phase=(-.25,0.,0.),role='interior'))
        self.assertEqual(p.inventories[0].linear,F(-3,4))
        self.assertEqual(p.inventories[3].linear,F(-3,4)) # vapor outward .5 + condensation .25

    def test_shared_N3_water_and_energy_telescope(self):
        p=panel();d={(x.cell,x.index):x for x in p.inventories}
        self.assertEqual(sum(d[i,0].linear+d[i,3].linear for i in range(3)),0)
        self.assertEqual(sum(x.linear for x in p.energies),F(-3))
        self.assertEqual(len([h for h in p.shared_rate_history if h[0][0]=='face_mol']),16)

    def test_interior_minimum_is_actual_imported_tool(self):
        from sludge_sandbox.mass_wet_exact_stage import InventoryPolynomial
        p=panel(sample(F(),phase=(4.,0.,0.),liquid=3.),
                sample(F(1,2),phase=(0.,0.,0.),liquid=3.,role='interior'))
        x=p.inventories[0]
        self.assertIs(type(x),InventoryPolynomial)
        self.assertEqual(x.minimum(F(1)),(F(23,16),F(5,8)))

    def test_exactclock_translation(self):
        a,b=panel(),panel(origin=F(2**80)+F(1,3))
        self.assertEqual(a.inventories,b.inventories);self.assertEqual(a.energies,b.energies)
        self.assertEqual(a.shared_rate_history,b.shared_rate_history)

    def test_nonhalf_interior_acceleration(self):
        p=panel(sample(F(),phase=(4.,0.,0.)),sample(F(1,4),phase=(0.,0.,0.),role='interior'))
        self.assertEqual(p.inventories[0].quadratic,F(8))

    def test_bad_time_identity_and_packed_mapping(self):
        a=sample(F());b=sample(F(1,2),role='interior')
        for bad in (replace(b,evaluation=replace(b.evaluation,time=T(F()))),
                    replace(b,evaluation=replace(b.evaluation,operator_identity=('wrong',))),
                    replace(b,state=ConservedState(b.state.amounts_mol+1,b.state.internal_energy_j,ENERGY))):
            with self.assertRaises(ValueError):panel(a,bad)

    def test_derived_polynomials_and_shared_history_cannot_be_replaced(self):
        p=panel()
        forged_inventory=replace(p.inventories[0],initial=F(999))
        forged_energy=replace(p.energies[0],linear=F(999))
        key,rate,acceleration=p.shared_rate_history[0]
        for forged in (
            replace(p,inventories=(forged_inventory,*p.inventories[1:])),
            replace(p,energies=(forged_energy,*p.energies[1:])),
            replace(p,shared_rate_history=((key,rate+1,acceleration),*p.shared_rate_history[1:])),
            replace(p,upper=T(F(2))),
            replace(p,upper=T(F(1,4))),
        ):
            with self.subTest(changed_field=next((name for name in ('inventories','energies','shared_rate_history','upper') if getattr(forged,name)!=getattr(p,name)),'none')):
                with self.assertRaises(ValueError):forged.check()
                with self.assertRaises(ValueError):forged.minima()

    def test_full_source_mapping_and_mutation_binding(self):
        a=sample(F());p=panel(a)
        wrong=replace(a.evaluation.source_evaluation.faces[1],energy_w=999.)
        raw=replace(a.evaluation.source_evaluation,faces=(a.evaluation.source_evaluation.faces[0],wrong,*a.evaluation.source_evaluation.faces[2:]))
        with self.assertRaises(ValueError):panel(replace(a,evaluation=replace(a.evaluation,source_evaluation=raw)))
        object.__setattr__(a.evaluation.source_evaluation,'source_ids',('changed',))
        with self.assertRaisesRegex(ValueError,'content_changed'):p.check()

    def test_source_material_qualification_cannot_be_upgraded(self):
        for target in ('evaluation', 'source_evaluation'):
            a = sample(F())
            p = panel(a)
            record = a.evaluation if target == 'evaluation' else a.evaluation.source_evaluation
            object.__setattr__(record, 'material_qualified', True)
            with self.subTest(target=target):
                with self.assertRaisesRegex(ValueError, 'not_material_qualified'):
                    p.check()
                with self.assertRaisesRegex(ValueError, 'not_material_qualified'):
                    p.minima()


@pytest.mark.parametrize('face_index,field,value', [
    (1, 'face_id', True), (0, 'face_id', 0.),
    (1, 'left_cell', False), (1, 'left_cell', 0.),
    (1, 'right_cell', True), (0, 'right_cell', False),
])
def test_face_incidence_rejects_equal_values_with_wrong_types(face_index, field, value):
    first = sample(F())
    raw = first.evaluation.source_evaluation
    faces = list(raw.faces)
    faces[face_index] = replace(faces[face_index], **{field: value})
    bad = replace(first, evaluation=replace(first.evaluation,
                  source_evaluation=replace(raw, faces=tuple(faces))))
    with pytest.raises(ValueError, match='shared_face_incidence'):
        panel(bad)


@pytest.mark.parametrize('role', ('first', 'interior'))
@pytest.mark.parametrize('owner_name,field', [
    ('state', 'amounts_mol'), ('state', 'internal_energy_j'),
    ('rates', 'face_species_mol_s'), ('rates', 'face_energy_w'),
    ('rates', 'reaction_species_mol_s'), ('rates', 'cell_power_w'),
])
def test_equal_float32_arrays_cannot_replace_bound_binary64_samples(role, owner_name, field):
    first, interior = sample(F()), sample(F(1, 2), role='interior')
    original = panel(first, interior)
    target = first if role == 'first' else interior
    owner = target.state if owner_name == 'state' else target.evaluation.rates
    object.__setattr__(owner, field, getattr(owner, field).astype(np.float32))
    with pytest.raises(ValueError, match='binary64'):
        original.check()
    with pytest.raises(ValueError, match='binary64'):
        panel(first, interior)


if __name__=='__main__':unittest.main()
