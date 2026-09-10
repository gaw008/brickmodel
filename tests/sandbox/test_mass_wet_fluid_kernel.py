"""Shared closure regression; artificial liquid seam, source-bound dry gases.

Goldens captured from the unchanged pre-extraction implementation, including
all point fields and model identity; native liquid EOS is forbidden by setup.
"""
from dataclasses import replace
from fractions import Fraction as F
import pytest
from test_mass_wet_storage import setup
from sludge_sandbox.deforming_solid_storage import _digest
from sludge_sandbox import mass_wet_storage as module


GOLDEN = {
    'wet': ('47f09f2ecc0b339f2a236625551802dd8362c75ba1a72b4e4beec38c3107cb06', '2d282a9b3f0ddb5cd64211234e37b3b4bb074925422f11d88dabd239bf5d0e34', 44),
    'dry': ('47f09f2ecc0b339f2a236625551802dd8362c75ba1a72b4e4beec38c3107cb06', '53dfbb90821bfc1390287f3805bff86b1aa0391d6a1c2c1e180a2ae2c227027b', 0),
    'error': ('abce13e9a0e5173ae03e62f4486b5a8de6e1ac4ec77e53da4e955b192385c968', '6bb43c278905d16463ebfe97117e25836ea7befaf9c6390d9219d07d1f5b3969', 44),
}


@pytest.mark.parametrize('case', GOLDEN)
def test_pre_extraction_full_point_and_identity(monkeypatch, case):
    st, state, calls = setup(monkeypatch)
    if case == 'dry':
        state = replace(state, liquid_water_mol=0.)
    if case == 'error':
        st = replace(st, bulk_volume_error_m3=1e-12, fluid_template=replace(
            st.fluid_template, envelope=replace(st.fluid_template.envelope,
            liquid_abs_du_dp_bound_j_mol_pa=1e-6)))
        state = st.state(state.solid_mass_kg, state.liquid_water_mol, state.gas_amounts_mol, 0.)
    point = st.evaluate(state, 305.)
    assert (st._identity, _digest(point), len(calls)) == GOLDEN[case]


def arguments(st, state):
    return dict(template=st.fluid_template, gas_ids=st.gas_ids,
                liquid_mol=state.liquid_water_mol, gas_amounts=state.gas_amounts_mol,
                temperature_k=305., nominal_available_m3=.000989,
                available_error_m3=F(1e-12))


def test_shared_kernel_exact_error_propagation_and_single_evaluation(monkeypatch):
    st, state, _ = setup(monkeypatch)
    original = module.RigidStorage.evaluate_at_temperature
    calls = []
    def observed(self, *args, **kwargs):
        calls.append(self)
        return original(self, *args, **kwargs)
    monkeypatch.setattr(module.RigidStorage, 'evaluate_at_temperature', observed)
    args = arguments(st, state)
    result = module.evaluate_wet_fluid(**args)
    assert calls == [result.fluid_template]
    assert result.fluid_template is not st.fluid_template
    assert st.fluid_template.mechanical.available_pore_volume_m3 != args['nominal_available_m3']
    assert result.fluid_template.mechanical.available_pore_volume_m3 == args['nominal_available_m3']
    # Independent rational reconstruction of both outward-rounded bounds.
    ng = sum(map(F, state.gas_amounts_mol), F())
    rt = F(st.fluid_template.mechanical.gas_constant_j_mol_k) * F(305.)
    base = F(result.point.pressure_error_bound_pa)
    maximum = F(st.fluid_template.envelope.pressure_range_pa[1])
    extra_global = F(module.upper(F(1e-12) * maximum**2 / (ng * rt)))
    global_bound = F(module.upper(base + extra_global))
    certified = min(maximum, F(result.point.mechanical.pressure_pa) + global_bound)
    extra_local = F(module.upper(F(1e-12) * certified**2 / (ng * rt)))
    assert result.global_pressure_error_pa == global_bound
    assert result.extra_pressure_error_pa == extra_local
    assert result.pressure_error_pa == module.upper(base + extra_local)


@pytest.mark.parametrize('changes', [
    {'gas_ids': ('H2O', 'N2', 'O2')}, {'gas_amounts': (.2, .2)},
    {'available_error_m3': -1.}, {'available_error_m3': True},
    {'available_error_m3': float('nan')}, {'nominal_available_m3': 0.},
    {'temperature_k': float('inf')}, {'liquid_mol': True},
    {'gas_amounts': (.2, -.2, .001)}, {'template': object()},
])
def test_invalid_kernel_inputs(monkeypatch, changes):
    st, state, _ = setup(monkeypatch)
    args = arguments(st, state)
    args.update(changes)
    with pytest.raises(ValueError):
        module.evaluate_wet_fluid(**args)


def test_global_domain_and_backend_failure_propagate(monkeypatch):
    st, state, _ = setup(monkeypatch)
    args = arguments(st, state)
    with pytest.raises(ValueError, match='global_pressure_uncertainty_outside_domain'):
        module.evaluate_wet_fluid(**dict(args, available_error_m3=F(1e-4)))
    def failed(*args, **kwargs):
        raise RuntimeError('backend_failure_probe')
    monkeypatch.setattr(module.RigidStorage, 'evaluate_at_temperature', failed)
    with pytest.raises(RuntimeError, match='backend_failure_probe'):
        module.evaluate_wet_fluid(**args)


def test_storage_uses_shared_water_and_fluid_checks(monkeypatch):
    st, state, _ = setup(monkeypatch)
    fluid_calls, water_calls = [], []
    fluid, water = module.evaluate_wet_fluid, module.check_wet_water
    def observed_fluid(*args, **kwargs):
        fluid_calls.append(1)
        return fluid(*args, **kwargs)
    def observed_water(*args, **kwargs):
        water_calls.append(1)
        return water(*args, **kwargs)
    monkeypatch.setattr(module, 'evaluate_wet_fluid', observed_fluid)
    monkeypatch.setattr(module, 'check_wet_water', observed_water)
    st.evaluate(state, 305.)
    assert fluid_calls == [1]
    assert water_calls == [1, 1]
    with pytest.raises(ValueError, match='explicit_water_element_convention'):
        water(st.fluid_template, object())


@pytest.mark.parametrize('field,value', [
    ('liquid_mol', F(1, 5)),
    ('gas_amounts', (F(1, 5), .2, .001)),
    ('temperature_k', F(9151, 30)),
    ('nominal_available_m3', F(989, 1000000)),
])
def test_nonbinary_eos_inputs_rejected_before_closure(monkeypatch, field, value):
    st, state, _ = setup(monkeypatch)
    def forbidden(*args, **kwargs):
        pytest.fail('lossy input reached fluid closure')
    monkeypatch.setattr(module.RigidStorage, 'evaluate_at_temperature', forbidden)
    with pytest.raises(ValueError, match='wet_fluid_input_not_exact_binary64'):
        module.evaluate_wet_fluid(**dict(arguments(st, state), **{field: value}))


def test_reviewer_fraction_inventory_pressure_underbound_rejected(monkeypatch):
    import math
    st, state, _ = setup(monkeypatch)
    gases = list(state.gas_amounts_mol)
    gases[0] = F(gases[0]) + F(math.ulp(gases[0])) * F(49, 100)
    error = F(9938182635383032647, 9903520314283042199192993792000)
    with pytest.raises(ValueError, match='wet_fluid_input_not_exact_binary64'):
        module.evaluate_wet_fluid(**dict(arguments(st, state),
            gas_amounts=tuple(gases), available_error_m3=error))


def test_exact_fraction_inputs_and_nonbinary_volume_error_preserved(monkeypatch):
    st, state, _ = setup(monkeypatch)
    args = arguments(st, state)
    # All quantities describe exactly the same represented binary64 state.
    args.update(liquid_mol=F(state.liquid_water_mol),
                gas_amounts=tuple(map(F, state.gas_amounts_mol)),
                temperature_k=F(305), nominal_available_m3=F(.000989),
                available_error_m3=F(1, 10**12))
    out = module.evaluate_wet_fluid(**args)
    actual = out.point.mechanical
    assert actual.gas_inventory_mol == dict(zip(st.gas_ids, state.gas_amounts_mol))
    ng = sum(map(F, actual.gas_inventory_mol.values()), F())
    rt = F(st.fluid_template.mechanical.gas_constant_j_mol_k) * F(actual.temperature_k)
    cap = min(F(st.fluid_template.envelope.pressure_range_pa[1]),
              F(actual.pressure_pa) + out.global_pressure_error_pa)
    exact_extra = args['available_error_m3'] * cap**2 / (ng * rt)
    assert out.extra_pressure_error_pa == F(module.upper(exact_extra))
