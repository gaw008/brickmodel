"""Source-specific fixed dry mass, independent exact energy and coordinate checks."""
from dataclasses import replace
from decimal import Decimal
from fractions import Fraction as F
from pathlib import Path
from types import SimpleNamespace
import math

import pytest

from sludge_sandbox.arlabosse_caloric import ArlabosseDryCaloric, CaloricError
from sludge_sandbox.evidence import EvidenceRegistry
from sludge_sandbox.phase_storage import InversePolicy
from sludge_sandbox.source_mass_caloric import (
    ArlabosseMassCaloric, FixedMassCaloricStorage, ReactionDisabled,
    SourceMassCaloricError, ENERGY_NODE_ID,
)

ROOT = Path(__file__).resolve().parents[2]


@pytest.fixture
def caloric():
    raw = ArlabosseDryCaloric(ROOT/'data/sandbox/research/arlabosse2005/source.json', ROOT)
    return ArlabosseMassCaloric(raw, F('313.15'))


def storage(caloric, mass=F(1, 5)):
    chemistry = ReactionDisabled((caloric.component_id,), (), 'Fixed-composition caloric interval only')
    return FixedMassCaloricStorage(caloric, mass, chemistry)


def test_source_energy_and_independent_quadratic_inverse(caloric):
    model = storage(caloric)
    point = model.evaluate(F('353.15'))
    # Independent source-review arithmetic: 0.2 kg * 65256 J/kg.
    assert point.internal_energy_j == F(65256, 5)
    assert point.minimum_heat_capacity_j_k == F(30983, 100)
    assert point.closed_heat_capacity_j_k == F(8486, 25)
    target = model.target(point.internal_energy_j)
    result = model.invert(target, InversePolicy(1e-10, 1e-8, 100))
    assert abs(result.point.temperature_k-F('353.15')) <= result.temperature_error_bound_k
    assert result.temperature_error_bound_k <= F(1e-10)
    assert result.point.numerical_energy_error_bound_j == 0
    assert result.point.fit_error is None and not result.point.material_qualified
    assert model.chemistry.evaluate((F(1, 5),), ()).solid_kg_s == (F(0),)


def test_anchor_change_requires_target_translation_and_identity(caloric):
    first = storage(caloric)
    other = storage(replace(caloric, reference_temperature_k=F('333.15')))
    a = first.evaluate(F('353.15')); b = other.evaluate(F('353.15'))
    assert a.internal_energy_j-b.internal_energy_j == 6394
    assert b.internal_energy_j == F(33286, 5)
    assert first.model_identity != other.model_identity
    with pytest.raises(SourceMassCaloricError, match='target_identity'):
        other.invert(first.target(a.internal_energy_j), InversePolicy(1e-8, 1e-6, 100))
    result = other.invert(other.target(b.internal_energy_j), InversePolicy(1e-8, 1e-6, 100))
    assert abs(result.point.temperature_k-F('353.15')) <= result.temperature_error_bound_k


def test_fixed_mass_and_actual_material_identity(caloric):
    a = storage(caloric); b = storage(caloric, F(2, 5))
    assert a.model_identity != b.model_identity
    assert b.evaluate(350).internal_energy_j == 2*a.evaluate(350).internal_energy_j
    assert 'arlabosse' in caloric.component_id.lower()
    with pytest.raises(SourceMassCaloricError, match='chemistry_layout'):
        FixedMassCaloricStorage(caloric, F(1, 5), ReactionDisabled(('A','B'), (), 'Unmatched layout'))


def test_full_bracket_lower_bound_not_hot_endpoint(caloric):
    assert caloric.minimum_specific_heat_capacity(F('308.15'), F('378.15')) == F('1549.15')
    assert caloric.cp(F('378.15')) == F('1779.45')
    with pytest.raises(SourceMassCaloricError, match='ordered'):
        caloric.minimum_specific_heat_capacity(360, 340)


def test_signed_energy_endpoints_and_outside_targets(caloric):
    model = storage(caloric)
    lo, hi = caloric.temperature_domain_k
    assert model.evaluate(lo).internal_energy_j < 0
    for t in (lo, hi):
        result = model.invert(model.target(model.evaluate(t).internal_energy_j), InversePolicy(1e-10, 1e-8, 100))
        assert result.point.temperature_k == t and result.temperature_error_bound_k == 0
    with pytest.raises(SourceMassCaloricError, match='outside'):
        model.invert(model.target(model.evaluate(hi).internal_energy_j+1), InversePolicy(1e-10, 1e-8, 100))


@pytest.mark.parametrize('mass', [0, -1, True, float('inf'), F(-1, 10**400)])
def test_invalid_fixed_mass(caloric, mass):
    with pytest.raises(SourceMassCaloricError): storage(caloric, mass)


def test_explicit_binary64_temperature_and_source_limits(caloric):
    assert caloric.cp(350.1) == caloric.cp(F.from_float(350.1))
    assert caloric.cp(Decimal('350.1')) != caloric.cp(350.1)
    assert caloric.cp(Decimal('308.15')) == F('1549.15')
    for t in (308.15, F('308.14999999999999999'), math.nextafter(378.15, math.inf), True, float('nan')):
        with pytest.raises(SourceMassCaloricError): caloric.cp(t)
    with pytest.raises(SourceMassCaloricError): replace(caloric, reference_temperature_k=F('298.15'))


def test_source_trace_and_unknown_fit_error(caloric):
    payload = storage(caloric).registry_payload()
    trace = EvidenceRegistry.from_dict(payload).trace(ENERGY_NODE_ID)
    nodes = {node['id']: node for node in trace['nodes']}
    assert 'ARLABOSSE2005_DRY_CP_EQ2' in nodes
    assert 'ARLABOSSE2005_DRY_SENSIBLE_ENTHALPY_DIFF' in nodes
    assert nodes[ENERGY_NODE_ID]['uncertainty']['status'] == 'unquantified'
    assert trace['sources'][0]['id'] == 'SRC_ARLABOSSE_2005_CONTACT_DRYING'


def test_reaction_disabled_layout_and_phase_separation():
    policy = ReactionDisabled(('sludge',), ('O2','N2','H2O'), 'No chemical conversion in this stage')
    out = policy.evaluate((F(1, 5),), (F(1), F(3), F(0)))
    assert out.solid_kg_s == (F(0),) and out.gas_mol_s == (F(0),)*3
    assert out.chemical_reference_power_w == 0
    assert out.phase_transfer_included is False
    with pytest.raises(SourceMassCaloricError): policy.evaluate((1, 2), (1, 3, 0))
    with pytest.raises(SourceMassCaloricError): ReactionDisabled(('x',), ('x',), 'overlap')


def test_unknown_volume_not_exposed_as_zero(caloric):
    assert caloric.specific_volume_m3_kg is None
    assert storage(caloric).material_qualified is False


def test_mutation_and_missing_source_are_not_silently_accepted(caloric, tmp_path):
    model = storage(caloric)
    object.__setattr__(caloric, 'reference_temperature_k', F('323.15'))
    with pytest.raises(SourceMassCaloricError, match='content_changed'): model.evaluate(350)
    path = tmp_path/'source.json'
    path.write_bytes((ROOT/'data/sandbox/research/arlabosse2005/source.json').read_bytes())
    raw = ArlabosseDryCaloric(path, ROOT)
    source_caloric = ArlabosseMassCaloric(raw, F('313.15'))
    path.unlink()
    with pytest.raises(CaloricError): storage(source_caloric)


def test_inverse_iteration_limit_is_not_success(caloric):
    model = storage(caloric)
    with pytest.raises(SourceMassCaloricError, match='iteration_limit'):
        model.invert(model.target(model.evaluate(F('351.25')).internal_energy_j), InversePolicy(1e-15, 1e-15, 1))


def test_runtime_provider_substitution_cannot_keep_source_identity(caloric):
    model = storage(caloric)
    fake = SimpleNamespace(cp=lambda *a, **kw: SimpleNamespace(value=F(90000)),
                           delta_h=lambda *a, **kw: SimpleNamespace(value=F(100000)))
    object.__setattr__(caloric, 'provider', fake)
    with pytest.raises(SourceMassCaloricError, match='explicit_arlabosse_provider'):
        model.evaluate(350)


@pytest.mark.parametrize('field', ['caloric', 'chemistry'])
def test_runtime_adapter_substitution_rejected_before_callbacks(caloric, field):
    model = storage(caloric)
    def forbidden(): pytest.fail('unadmitted collaborator must be rejected before invocation')
    fake = SimpleNamespace(_check=forbidden, binding=forbidden)
    object.__setattr__(model, field, fake)
    with pytest.raises(SourceMassCaloricError, match='explicit_'):
        model.evaluate(350)
