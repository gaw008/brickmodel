"""Independent Cp integrals and original published gas curves, never brick data."""
from dataclasses import FrozenInstanceError
from fractions import Fraction
from pathlib import Path
import math

import pytest
from scipy.integrate import quad

from sludge_sandbox.continuous_caloric import ContinuousCaloricError, ContinuousShomateGas
from sludge_sandbox.thermochemistry import ShomateGas, ShomateSegment, load_thermochemistry


SOURCE = ('manufactured:continuous-caloric',)
DATA = Path(__file__).resolve().parents[2] / 'data/sandbox/thermochemistry/nist_gases_v1.json'


def gas():
    return ShomateGas('fixture', (
        ShomateSegment((300, 600), (30, 0, 0, 0, 0, 100, 0, 0), 0, 8, SOURCE),
        ShomateSegment((600, 1000), (40, 0, 0, 0, 0, 200, 0, 0), 0, 8, SOURCE),
        ShomateSegment((1000, 1500), (50, 0, 0, 0, 0, -300, 0, 0), 0, 8, SOURCE),
    ), 'manufactured_test_fixture', SOURCE)


def continuous(source=None, **changes):
    values = dict(source_gas=source or gas(), model_id='continuous-fixture', version='1',
                  anchor_temperature_k=800, method_source_ids=('derivation:cp-integral',), gas_constant_source_ids=('explicit:gas-constant',),
                  allow_manufactured=True)
    values.update(changes)
    return ContinuousShomateGas(**values)


def test_anchor_and_both_directions_across_three_segments():
    source = gas()
    c = continuous(source)
    anchor = source.enthalpy_j_mol(800)
    assert c.enthalpy_j_mol(800) == anchor
    assert c.enthalpy_j_mol(400) == anchor - 40*200 - 30*200
    assert c.enthalpy_j_mol(1200) == anchor + 40*200 + 50*200
    assert c.enthalpy_change_j_mol(400, 1200) == 30*200 + 40*400 + 50*200
    assert c.enthalpy_change_j_mol(1200, 400) == -32000
    assert c.internal_energy_change_j_mol(400, 1200) == 32000 - 8*800
    assert c.enthalpy_change_j_mol(1200, 1200) == 0
    for t in (300, 400, 600, 800, 1000, 1500):
        assert c.internal_energy_j_mol(t) == c.enthalpy_j_mol(t)-8*t
        assert c.cv_j_mol_k(t) == c.cp_j_mol_k(t)-8


def test_seams_h_continuous_cp_jump_retained_and_offsets_inspectable():
    c = continuous()
    for left, right in zip(c.segments, c.segments[1:]):
        t = right.temperature_range_k[0]
        assert left.enthalpy_j_mol(t) == right.enthalpy_j_mol(t)
        assert c.segment_for(t) is right
        assert c.cp_j_mol_k(t) == right.source_segment.cp_j_mol_k(t)
        assert c.cp_j_mol_k(math.nextafter(t, -math.inf)) == left.source_segment.cp_j_mol_k(t)
    for segment, record in zip(c.segments, c.segment_offsets):
        low, high = record.temperature_range_k
        assert record.source_ids == SOURCE
        for t in (low, (low+high)/2, high):
            assert segment.enthalpy_j_mol(t)-segment.source_segment.enthalpy_j_mol(t) == pytest.approx(
                record.enthalpy_offset_j_mol, abs=1e-8, rel=0)
    assert c.classification == 'manufactured_test_fixture'
    assert c.source_classification == 'manufactured_test_fixture'
    assert c.method_id == 'piecewise_shomate_cp_integral_v1'
    assert 'derivation:cp-integral' in c.source_ids
    assert not hasattr(c, 'entropy_j_mol_k')
    with pytest.raises(FrozenInstanceError):
        c.segment_offsets[0].enthalpy_offset_j_mol = 0


@pytest.mark.parametrize('species', ['O2', 'N2', 'CO2', 'H2O'])
def test_real_nist_cp_unchanged_independent_quadrature_and_closed_cycle(species):
    pack = load_thermochemistry(DATA)
    original = pack.species(species)
    low, high = original.temperature_range_k
    anchor = (low + original.segments[0].temperature_range_k[1])/2
    c = continuous(original, anchor_temperature_k=anchor, allow_manufactured=False,
                   gas_constant_source_ids=pack.constant_source_ids)
    assert c.classification == 'derived_from_evidence'
    assert c.source_classification == 'literature_constitutive_model'
    assert c.temperature_range_k == original.temperature_range_k
    integral = math.fsum(quad(lambda t: segment.cp_j_mol_k(t), *segment.temperature_range_k,
                              epsabs=1e-8, epsrel=1e-12)[0] for segment in original.segments)
    assert c.enthalpy_change_j_mol(low, high) == pytest.approx(integral, abs=2e-7, rel=0)
    assert c.enthalpy_change_j_mol(low, high) + c.enthalpy_change_j_mol(high, low) == 0
    for segment in c.segments:
        a, b = segment.temperature_range_k
        for t in (a, (a+b)/2, b):
            assert segment.cp_j_mol_k(t) == segment.source_segment.cp_j_mol_k(t)
    for left, right in zip(c.segments, c.segments[1:]):
        seam = right.temperature_range_k[0]
        assert left.enthalpy_j_mol(seam) == right.enthalpy_j_mol(seam)


def test_huge_original_baseline_does_not_erase_small_integrated_heat():
    source = ShomateGas('huge', (ShomateSegment((300, 1500),
        (30, 0, 0, 0, 0, 1e25, 0, 0), 0, 8, SOURCE),), 'manufactured_test_fixture', SOURCE)
    c = continuous(source)
    start = 800.
    end = math.nextafter(start, math.inf)
    assert source.enthalpy_j_mol(end)-source.enthalpy_j_mol(start) == 0
    assert c.enthalpy_change_j_mol(start, end) == float(30*(Fraction(end)-Fraction(start)))
    assert c.internal_energy_change_j_mol(start, end) == float(22*(Fraction(end)-Fraction(start)))
    assert c.resolution_j_mol(start).enthalpy_ulp_j_mol > c.enthalpy_change_j_mol(start, end)


@pytest.mark.parametrize('temperature', [299, 1501, math.nan, math.inf, True, '800'])
def test_invalid_query_and_anchor_domains(temperature):
    c = continuous()
    with pytest.raises(ContinuousCaloricError):
        c.enthalpy_j_mol(temperature)
    with pytest.raises(ContinuousCaloricError):
        continuous(anchor_temperature_k=temperature)


@pytest.mark.parametrize('changes', [dict(allow_manufactured=False), dict(model_id=''),
                                    dict(version=''), dict(method_source_ids=()),
                                    dict(method_source_ids=('x', 'x'))])
def test_identity_and_manufactured_gate(changes):
    with pytest.raises(ContinuousCaloricError):
        continuous(**changes)


def test_all_cp_terms_tiny_interval_decimal_integral_and_no_domain_gap():
    from decimal import Decimal, localcontext
    from sludge_sandbox.thermochemistry import ThermochemistryError

    coefficients = (50., -2., 1., -.5, -1., 100., 0., 0.)
    source = ShomateGas('terms', (ShomateSegment((300, 1500), coefficients, 0, 8, SOURCE),),
                        'manufactured_test_fixture', SOURCE)
    c = continuous(source)
    left = 800.
    right = math.nextafter(left, math.inf)
    with localcontext() as context:
        context.prec = 90
        x, y = Decimal.from_float(left)/1000, Decimal.from_float(right)/1000
        a, b, cc, d, e, *_ = map(Decimal.from_float, coefficients)
        expected = 1000*(a*(y-x)+b*(y*y-x*x)/2+cc*(y**3-x**3)/3+d*(y**4-x**4)/4+e*(1/x-1/y))
    assert c.enthalpy_change_j_mol(left, right) == float(expected)
    with pytest.raises(ThermochemistryError, match='adjacent'):
        ShomateGas('gap', (source.segments[0], ShomateSegment((1600, 1800),
            (30, 0, 0, 0, 0, 0, 0, 0), 0, 8, SOURCE)), 'manufactured_test_fixture', SOURCE)
    with pytest.raises(ContinuousCaloricError, match='gas_constant_source'):
        continuous(gas_constant_source_ids=())


def test_anchor_at_seam_uses_original_upper_branch_and_preserves_anchor():
    source = gas()
    c = continuous(source, anchor_temperature_k=600)
    assert source.segments[0].enthalpy_j_mol(600) != source.segments[1].enthalpy_j_mol(600)
    assert c.anchor_enthalpy_j_mol == source.segments[1].enthalpy_j_mol(600)
    assert c.enthalpy_j_mol(600) == c.anchor_enthalpy_j_mol


def test_explicit_derived_pack_drives_actual_gas_heat_integration_across_seam():
    from sludge_sandbox.gas_heat_model import GasHeatModel
    from sludge_sandbox.integration import IntegrationPolicy, Rates, integrate
    from sludge_sandbox.thermochemistry import Thermochemistry

    derived = continuous(anchor_temperature_k=500)
    pack = Thermochemistry('derived-fixture-continuous-integration-v1', {'fixture': derived},
                           8, derived.gas_constant_source_ids, allow_manufactured=True)
    model = GasHeatModel(
        thermochemistry=pack, species_order=('fixture',), molar_masses_kg_mol={'fixture': .012},
        face_area_m2=1, cell_widths_m=(1,), gas_volumes_m3=(1,), conductivities_w_m_k=(0,),
        effective_diffusivities_m2_s={'fixture': (0,)}, permeability_m2=(0,),
        relative_permeability=(1,), viscosity_pa_s=(1,), coefficient_source_ids=SOURCE,
        coefficient_set_id='manufactured-sealed-cell', coefficient_version='1',
        coefficient_classification='manufactured', allow_manufactured=True,
    )
    initial = model.state_from_temperatures([[1]], [500])
    trial_temperatures = []

    def heated_cell(state, time):
        # This call runs the actual GasHeatModel caloric decoding at every trial.
        rates = model(state, time)
        trial_temperatures.append(model.temperatures_k(state)[0])
        # Explicit manufactured electrical power, not an invented material rate.
        return Rates(rates.face_species_mol_s, rates.face_energy_w,
                     rates.reaction_species_mol_s, [1000])

    policy = IntegrationPolicy(
        initial_step_s=.7, maximum_step_s=.7, minimum_step_s=1e-10,
        relative_tolerance=1e-9, amount_absolute_tolerance_mol=1e-12,
        energy_absolute_tolerance_j=1e-8, amount_scale_mol=1, energy_scale_j=5400,
        maximum_steps=100, maximum_rejections=100, maximum_wall_seconds=20,
    )
    result = integrate(initial, heated_cell, start_s=0, end_s=5.4,
                       breakpoints_s=(2.2,), policy=policy)
    assert result.status == 'completed', (result.status, result.reason)
    assert result.rejected_trials == 0
    assert len(trial_temperatures) == result.evaluations
    assert min(trial_temperatures) <= 500 and max(trial_temperatures) > 699
    assert 2.2 in result.times_s
    for time, state in zip(result.times_s, result.states):
        # Independent piecewise constant Cv = 30-8 then 40-8 J/(mol K).
        exact_temperature = 500+1000*time/22 if time <= 2.2 else 600+(1000*time-2200)/32
        assert model.temperatures_k(state)[0] == pytest.approx(exact_temperature, abs=1e-8, rel=0)
        assert state.internal_energy_j[0] == pytest.approx(initial.internal_energy_j[0]+1000*time,
                                                         abs=1e-8, rel=0)
        assert state.amounts_mol[0, 0] == 1
    for step in result.steps:
        assert step.cell_work_j[0] == pytest.approx(1000*(step.end_s-step.start_s), abs=1e-8, rel=0)
        assert all(value == 0 for value in step.face_energy_j)
    assert math.fsum(step.cell_work_j[0] for step in result.steps) == pytest.approx(5400, abs=1e-8, rel=0)
    assert pack.contains_manufactured_models
    assert 'derivation:cp-integral' in model.source_ids


def test_real_derived_nist_pack_inverse_has_no_old_fit_gap_at_oxygen_seam():
    from sludge_sandbox.thermochemistry import Thermochemistry

    source_pack = load_thermochemistry(DATA)
    original = source_pack.species('O2')
    derived = continuous(original, anchor_temperature_k=400, allow_manufactured=False,
                         gas_constant_source_ids=source_pack.constant_source_ids)
    pack = Thermochemistry('explicit-derived-nist-O2-v1', {'O2': derived},
                           source_pack.gas_constant_j_mol_k, source_pack.constant_source_ids)
    assert pack.pack_id != source_pack.pack_id
    assert not pack.contains_manufactured_models
    for temperature in (699.9, 700., 700.1):
        energy = pack.mixture_internal_energy_j({'O2': 1}, temperature)
        recovered = pack.temperature_from_internal_energy_j(energy, {'O2': 1})
        assert recovered == pytest.approx(temperature, abs=1e-8, rel=0)
    assert derived.classification == 'derived_from_evidence'
    assert original.seam_diagnostics()[0]['h_right_minus_left_j_mol'] != 0
