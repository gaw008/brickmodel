"""Manufactured composition coupling; no water EOS or material qualification."""
from dataclasses import FrozenInstanceError, replace
from fractions import Fraction
import math
import pytest

from sludge_sandbox.geometry import ReferenceSlab
from sludge_sandbox.skeleton_energy import DiagonalSkeletonEnergy, SkeletonEnergyError
from sludge_sandbox.reacting_skeleton_energy import ManufacturedReactingSkeletonEnergy


def model(**changes):
    base = DiagonalSkeletonEnergy(reference=ReferenceSlab(.02, .04, 2), cell_index=0,
        fixed_solid_inventory_mol=(('a', 2.), ('b', 0.)), solid_provider_identity=('manufactured-solid', 'v1'),
        bulk_modulus_pa=1000., shear_modulus_pa=400., viscosity_pa_s=3.,
        interface_energy_j_m2=.5, reference_interface_area_m2=.003,
        stretch_range=(.5, 2.), maximum_absolute_log_rate_per_s=2., model_id='base', version='1',
        source_ids=('manufactured-oracle',), classification='manufactured_test_fixture', allow_manufactured=True)
    return ManufacturedReactingSkeletonEnergy(**(dict(reference_model=base, composition_offset=.5,
        composition_weights_per_mol=(('a', .25), ('b', .75)), model_id='reacting', version='1',
        classification='manufactured_test_fixture', allow_manufactured=True) | changes))


def evaluate(p, amounts=None, **changes):
    return p.evaluate(**(dict(normal_stretch=1.1, tangential_stretch=.9,
        normal_rate_per_s=.03, tangential_rate_per_s=-.02,
        solid_inventory_mol={'a': 2., 'b': 0.} if amounts is None else amounts) | changes))


def test_independent_interface_formula_and_composition_derivatives():
    p = model()
    s = evaluate(p, {'a': 1., 'b': 2.})
    exact_surface = Fraction(.5)*Fraction(.003)*Fraction(.9)**2
    exact_q = Fraction(.5)+Fraction(.25)+2*Fraction(.75)
    assert abs(Fraction(s.interface_energy_j)-exact_q*exact_surface) <= Fraction(s.numerical_error_bounds['interface_energy_j'])
    for key, weight in p.composition_weights_per_mol:
        actual = s.interface_composition_derivative_j_mol[key]
        bound = s.numerical_error_bounds['interface_composition_derivative_j_mol'][key]
        assert abs(Fraction(actual)-Fraction(weight)*exact_surface) <= Fraction(bound)
        delta = 1e-5
        plus, minus = {'a': 1., 'b': 2.}, {'a': 1., 'b': 2.}
        plus[key] += delta
        minus[key] -= delta
        for prefix in ('elastic', 'interface'):
            fd = (getattr(evaluate(p, plus), prefix+'_energy_j')-getattr(evaluate(p, minus), prefix+'_energy_j'))/(2*delta)
            assert fd == pytest.approx(getattr(s, prefix+'_composition_derivative_j_mol')[key], abs=1e-11, rel=0)


def test_composition_storage_changes_without_external_deformation_power():
    p = model()
    first = evaluate(p, normal_rate_per_s=0., tangential_rate_per_s=0.)
    second = evaluate(p, {'a': 1., 'b': 1.}, normal_rate_per_s=0., tangential_rate_per_s=0.)
    assert second.elastic_energy_j > first.elastic_energy_j
    assert second.interface_energy_j > first.interface_energy_j
    for state in (first, second):
        assert state.elastic_rate_w == state.interface_rate_w == state.dissipation_w == state.rayleigh_potential_w == 0
    assert first.model_identity == second.model_identity == p.identity
    assert second.elastic_composition_derivative_j_mol['a'] > 0


def test_q_one_and_scaled_power_match_complete_reference_enclosures():
    for p, amounts, q in ((model(), {'a': 2., 'b': 0.}, 1), (model(), {'a': 1., 'b': 1.}, 1.5),
                           (model(composition_offset=1., composition_weights_per_mol=(('a', 0.), ('b', 0.))), {'a': 4., 'b': 3.}, 1)):
        result = evaluate(p, amounts)
        base = p.reference_model.evaluate(normal_stretch=1.1, tangential_stretch=.9,
            normal_rate_per_s=.03, tangential_rate_per_s=-.02, solid_inventory_mol={'a': 2., 'b': 0.})
        for key, err in base.numerical_error_bounds.items():
            expected, actual, bound = getattr(base, key), getattr(result, key), result.numerical_error_bounds[key]
            expected, actual, err, bound = ((expected, actual, err, bound) if isinstance(expected, tuple)
                                            else ((expected,), (actual,), (err,), (bound,)))
            for e, a, eb, ab in zip(expected, actual, err, bound, strict=True):
                assert abs(Fraction(a)-Fraction(q)*Fraction(e)) <= Fraction(ab)+Fraction(q)*Fraction(eb)
        assert result.dissipation_w >= 0


@pytest.mark.parametrize('amounts', [{}, {'a': 1.}, {'a': 1., 'b': 0., 'c': 0.}, {'a': -1., 'b': 1.},
    {'a': 0., 'b': 0.}, {'a': True, 'b': 1.}, {'a': math.inf, 'b': 1.}, {'a': math.nan, 'b': 1.}])
def test_invalid_current_inventory(amounts):
    with pytest.raises(SkeletonEnergyError):
        evaluate(model(), amounts)


@pytest.mark.parametrize('changes', [dict(composition_offset=0.), dict(composition_offset=True),
    dict(composition_weights_per_mol=(('a', 1.),)), dict(composition_weights_per_mol=(('a', 1.), ('a', 0.))),
    dict(composition_weights_per_mol=(('a', -1.), ('b', 0.))), dict(composition_weights_per_mol=(('a', math.nan), ('b', 0.))),
    dict(allow_manufactured=False), dict(classification='qualified_material'), dict(reference_model=None), dict(model_id='')])
def test_configuration_rejection(changes):
    with pytest.raises(SkeletonEnergyError):
        model(**changes)


def test_domains_old_guards_identity_and_immutability():
    p = model()
    for changes in (dict(normal_stretch=.49), dict(normal_rate_per_s=5.)):
        with pytest.raises(SkeletonEnergyError):
            evaluate(p, **changes)
    with pytest.raises(SkeletonEnergyError, match='fixed_inventory_mismatch'):
        p.reference_model.evaluate(normal_stretch=1., tangential_stretch=1., normal_rate_per_s=0.,
            tangential_rate_per_s=0., solid_inventory_mol={'a': 1., 'b': 1.})
    for other in (replace(p, composition_offset=.6), replace(p, version='2'),
                  replace(p, composition_weights_per_mol=(('a', .3), ('b', .75))),
                  replace(p, reference_model=replace(p.reference_model, bulk_modulus_pa=1001.))):
        assert other.identity != p.identity
    assert p.source_ids == p.reference_model.source_ids
    assert p.solid_provider_identity == p.reference_model.solid_provider_identity
    assert p.reference is p.reference_model.reference
    assert p.reference_solid_inventory_mol == (('a', 2.), ('b', 0.))
    s = evaluate(p)
    for prefix in ('elastic', 'interface'):
        key = prefix+'_composition_derivative_j_mol'
        assert set(getattr(s, key)) == set(s.numerical_error_bounds[key]) == {'a', 'b'}
        with pytest.raises(TypeError):
            getattr(s, key)['a'] = 0.
        with pytest.raises(TypeError):
            s.numerical_error_bounds[key]['a'] = 0.
    with pytest.raises(FrozenInstanceError):
        p.composition_offset = 1.
    with pytest.raises(FrozenInstanceError):
        s.elastic_energy_j = 1.


def test_underflow_and_overflow_are_explicit_not_clipped():
    tiny = math.nextafter(0., 1.)
    for p in (model(composition_offset=tiny, composition_weights_per_mol=(('a', 0.), ('b', 0.))),
              model(composition_weights_per_mol=(('a', tiny), ('b', 1.))),
              model(composition_weights_per_mol=(('a', 1e308), ('b', 1e308)))):
        with pytest.raises(SkeletonEnergyError, match='unrepresentable'):
            evaluate(p, {'a': 1e308, 'b': 1e308} if p.composition_weights_per_mol[0][1] == 1e308 else None)
