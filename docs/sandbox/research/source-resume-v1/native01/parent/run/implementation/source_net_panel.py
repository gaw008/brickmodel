"""Source-column numerical affine inventory evidence, not event authorization."""
from dataclasses import dataclass
from fractions import Fraction as F
import numpy as np
from sludge_sandbox.exact_event_clock import ExactEventTime as T
from sludge_sandbox.exact_boundary_program import ExactBoundaryState
from sludge_sandbox.exact_source_column import SourceExactEvaluation
from sludge_sandbox.integration import ConservedState, Rates
from sludge_sandbox.mass_wet_storage import WetMixedState
from sludge_sandbox.mass_wet_transport import WetPhaseEvaluation
from sludge_sandbox.source_mass_caloric import DisabledChemicalRates
from sludge_sandbox.source_wet_column import SourceColumnRates, LiquidSourceColumnRates
from sludge_sandbox.programmed_source_wet_column import ProgrammedSourceRates, ProgrammedLiquidSourceRates
from sludge_sandbox.mass_wet_exact_stage import InventoryPolynomial
from sludge_sandbox.deforming_solid_storage import _digest


def require(ok, reason):
    if not ok: raise ValueError(reason)


@dataclass(frozen=True)
class SavedSourceSample:
    state: ConservedState
    evaluation: SourceExactEvaluation
    role: str


def _validate(sample, operator_identity, energy_identity, fixed_kg):
    require(type(sample) is SavedSourceSample and type(sample.state) is ConservedState
            and type(sample.evaluation) is SourceExactEvaluation, 'actual_saved_source_sample')
    require(type(sample.role) is str and bool(sample.role.strip()), 'explicit_stage_role')
    s, e = sample.state, sample.evaluation
    require(all(type(a) is np.ndarray and a.dtype == np.float64 and np.all(np.isfinite(a))
                for a in (s.amounts_mol, s.internal_energy_j)), 'source_state_binary64_arrays_required')
    require(type(e.time) is T, 'exact_saved_time')
    require(e.material_qualified is False, 'source_sample_not_material_qualified')
    require(e.operator_identity == operator_identity and s.energy_model_identity == energy_identity,
            'sample_identity_mismatch')
    require(s.mechanical_stretches is None, 'fixed_source_no_dynamic_mechanics')
    require(type(operator_identity) is tuple and len(operator_identity)==3
            and operator_identity[0]=='exact_source_column_v1'
            and operator_identity[2]==('liquid_water','O2','N2','H2O'), 'explicit_source_operator_layout')
    require(type(energy_identity) is tuple and len(energy_identity)==3
            and energy_identity[0]=='source_column_fixed_dry_energy_v1'
            and energy_identity[2]==operator_identity[2], 'explicit_source_energy_layout')
    n=len(fixed_kg)
    require(n>0 and s.amounts_mol.shape==(n,4) and s.internal_energy_j.shape==(n,)
            and len(e.source_states)==n and len(energy_identity[1])==n, 'source_sample_shape')
    raw=e.source_evaluation
    require(type(raw) in (SourceColumnRates,LiquidSourceColumnRates,ProgrammedSourceRates,ProgrammedLiquidSourceRates), 'actual_source_observation')
    require(raw.material_qualified is False, 'source_observation_not_material_qualified')
    if type(raw) in (ProgrammedSourceRates, ProgrammedLiquidSourceRates):
        require(type(raw.boundary) is ExactBoundaryState and type(raw.boundary.time) is T
                and raw.boundary.time == e.time, 'source_program_sample_time_mismatch')
    require(raw.model_identity==operator_identity[1] and len(raw.cells)==n and len(raw.faces)==n+1,
            'source_observation_identity_shape')
    require(type(e.rates) is Rates and e.rates.mechanical_rates_per_s is None
            and e.rates.cell_power_components_w is None, 'fixed_source_rate_schema')
    r=e.rates
    require(all(type(a) is np.ndarray and a.dtype == np.float64 and np.all(np.isfinite(a))
                for a in (r.face_species_mol_s, r.face_energy_w,
                          r.reaction_species_mol_s, r.cell_power_w)), 'source_rate_binary64_arrays_required')
    require(r.face_species_mol_s.shape==(n+1,4) and r.face_energy_w.shape==(n+1,)
            and r.reaction_species_mol_s.shape==(n,4) and r.cell_power_w.shape==(n,), 'source_rate_shape')
    require(np.all(r.cell_power_w==0), 'no_extra_energy_source')
    for i,(source,cell,mass) in enumerate(zip(e.source_states,raw.cells,fixed_kg)):
        require(type(source) is WetMixedState and source.solid_mass_kg==(mass,)
                and source.energy_model_identity==energy_identity[1][i], 'fixed_mass_storage_binding')
        require(tuple(s.amounts_mol[i])==(source.liquid_water_mol,*source.gas_amounts_mol)
                and s.internal_energy_j[i]==source.internal_energy_j, 'packed_source_state_mismatch')
        chemistry = cell.chemistry
        require(type(chemistry) is DisabledChemicalRates
                and type(chemistry.solid_kg_s) is tuple and len(chemistry.solid_kg_s) == 1
                and type(chemistry.gas_mol_s) is tuple and len(chemistry.gas_mol_s) == 3
                and all(type(value) is F and value == 0 for value in
                        (*chemistry.solid_kg_s, *chemistry.gas_mol_s, chemistry.chemical_reference_power_w))
                and chemistry.phase_transfer_included is False,
                'explicit_inactive_chemistry')
        require(type(cell.phase) is WetPhaseEvaluation,'actual_phase_observation')
        phase=cell.phase.phase_water_mol_s
        require(tuple(r.reaction_species_mol_s[i])==(-phase,0.,0.,phase),'actual_phase_rate_mapping')
    for i,face in enumerate(raw.faces):
        left_cell=i-1 if i else None
        right_cell=i if i<n else None
        require(type(face.face_id) is int and face.face_id==i
                and type(face.left_cell) is type(left_cell) and face.left_cell==left_cell
                and type(face.right_cell) is type(right_cell) and face.right_cell==right_cell,
                'shared_face_incidence')
        require(tuple(r.face_species_mol_s[i])==(getattr(face,'liquid_mol_s',0.),*face.gas_mol_s)
                and r.face_energy_w[i]==face.energy_w,'actual_face_rate_mapping')
    require(r.face_species_mol_s[0,0]==r.face_species_mol_s[-1,0]==0.,'source_liquid_boundary_no_flux')
    # Numeric binding uses the existing canonical digest on explicit array data,
    # and retains the complete raw observation, not only net derivative sums.
    return _digest((sample.role,s.amounts_mol.tolist(),s.internal_energy_j.tolist(),s.energy_model_identity,
        e.time,e.source_states,raw,e.operator_identity,r.face_species_mol_s.tolist(),r.face_energy_w.tolist(),
        r.reaction_species_mol_s.tolist(),r.cell_power_w.tolist()))


@dataclass(frozen=True)
class SourceAffinePanel:
    first: SavedSourceSample
    interior: SavedSourceSample
    upper: T
    operator_identity: tuple
    energy_identity: tuple
    fixed_dry_mass_kg: tuple
    sample_bindings: tuple
    # Each row: key, initial rate, acceleration; N+1 shared faces retained.
    shared_rate_history: tuple
    inventories: tuple
    energies: tuple
    qualification: str = 'saved_numerical_affine_panel_not_stage_or_event_acceptance'

    def check(self):
        expected=build_source_panel(self.first,self.interior,self.upper,
            operator_identity=self.operator_identity,energy_identity=self.energy_identity,
            fixed_dry_mass_kg=self.fixed_dry_mass_kg)
        require(expected.sample_bindings==self.sample_bindings,'saved_sample_content_changed')
        for name in ('shared_rate_history','inventories','energies'):
            actual,wanted=getattr(self,name),getattr(expected,name)
            require(type(actual) is tuple and actual==wanted,'derived_panel_content_changed:'+name)
        for actual,wanted in zip(self.shared_rate_history,expected.shared_rate_history):
            require(type(actual) is tuple and type(actual[0]) is tuple
                    and all(type(a) is type(b) for a,b in zip(actual[0],wanted[0]))
                    and type(actual[1]) is F and type(actual[2]) is F,'derived_history_exact_types')
        for polynomial in (*self.inventories,*self.energies):
            require(type(polynomial) is InventoryPolynomial and type(polynomial.family) is str
                    and type(polynomial.cell) is int and type(polynomial.index) is int
                    and all(type(x) is F for x in (polynomial.initial,polynomial.linear,polynomial.quadratic)),
                    'derived_polynomial_exact_types')
        require(self.qualification==expected.qualification,'panel_qualification_changed')

    def minima(self):
        self.check()
        duration=self.upper.elapsed_since(self.first.evaluation.time)
        return tuple((p.family,p.cell,p.index,*p.minimum(duration)) for p in self.inventories)


def build_source_panel(first, interior, upper, *, operator_identity, energy_identity, fixed_dry_mass_kg):
    require(type(fixed_dry_mass_kg) is tuple and bool(fixed_dry_mass_kg)
            and all(type(m) is float and np.isfinite(m) and m>0 for m in fixed_dry_mass_kg),'explicit_fixed_mass_tuple')
    bindings=tuple(_validate(s,operator_identity,energy_identity,fixed_dry_mass_kg) for s in (first,interior))
    require(type(upper) is T and first.evaluation.time<interior.evaluation.time<upper,'ordered_exact_panel_times')
    # The caller-declared upper boundary is original input, not derivable from
    # the two samples. Retain it in the existing sample binding tuple.
    bindings=(*bindings,upper)
    hm=interior.evaluation.time.elapsed_since(first.evaluation.time)
    n=len(fixed_dry_mass_kg)
    def components(sample):
        r=sample.evaluation.rates
        return tuple((('face_mol',i,j),F(float(r.face_species_mol_s[i,j]))) for i in range(n+1) for j in range(4))+tuple(
            (('face_U',i),F(float(r.face_energy_w[i]))) for i in range(n+1))+tuple(
            (('local_mol',i,j),F(float(r.reaction_species_mol_s[i,j]))) for i in range(n) for j in range(4))
    left,right=components(first),components(interior)
    history=tuple((key,a,(b-a)/hm) for (key,a),(_,b) in zip(left,right))
    a,b=dict(left),dict(right)
    inventories=[];energies=[]
    for i in range(n):
        for j in range(4):
            da=a['face_mol',i,j]-a['face_mol',i+1,j]+a['local_mol',i,j]
            db=b['face_mol',i,j]-b['face_mol',i+1,j]+b['local_mol',i,j]
            inventories.append(InventoryPolynomial('liquid' if j==0 else 'gas',i,j,
                F(float(first.state.amounts_mol[i,j])),da,(db-da)/(2*hm)))
        du=a['face_U',i]-a['face_U',i+1]
        dum=b['face_U',i]-b['face_U',i+1]
        energies.append(InventoryPolynomial('energy',i,0,F(float(first.state.internal_energy_j[i])),du,(dum-du)/(2*hm)))
    return SourceAffinePanel(first,interior,upper,operator_identity,energy_identity,fixed_dry_mass_kg,
                             bindings,history,tuple(inventories),tuple(energies))
