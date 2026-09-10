"""An ordinary segment may choose steps without replacing its error budgets."""
from dataclasses import fields, replace
import math

import pytest

from sludge_sandbox.integration import IntegrationError, IntegrationPolicy
from sludge_sandbox.source_trajectory import SourceOrdinaryStepSizes


def reference_policy():
    return IntegrationPolicy(initial_step_s=1e-6, minimum_step_s=2**-30,
        maximum_step_s=1e-6, relative_tolerance=1e-8,
        amount_absolute_tolerance_mol=1e-7, energy_absolute_tolerance_j=.001,
        amount_scale_mol=1., energy_scale_j=1e5, maximum_steps=4,
        maximum_rejections=4, maximum_wall_seconds=180.)


def test_only_initial_and_maximum_steps_change_for_a_new_segment():
    original = reference_policy()
    sizes = SourceOrdinaryStepSizes(1/64, 1/32, 'Declared post-event heat-transfer experiment.')
    changed = sizes.apply(original)
    assert changed is not original
    assert (changed.initial_step_s, changed.maximum_step_s) == (1/64, 1/32)
    for field in fields(original):
        if field.name not in ('initial_step_s', 'maximum_step_s'):
            assert getattr(changed, field.name) == getattr(original, field.name)
    assert sizes.classification == 'numerical_policy'


@pytest.mark.parametrize(('initial', 'maximum', 'rationale'), [
    (0., .1, 'reason'), (.2, .1, 'reason'), (math.inf, math.inf, 'reason'),
    (.1, math.nan, 'reason'), (True, .1, 'reason'), (1, 2., 'reason'),
    (.1, .1, ''), (.1, .1, None),
])
def test_invalid_step_declarations_are_rejected(initial, maximum, rationale):
    with pytest.raises(IntegrationError):
        SourceOrdinaryStepSizes(initial, maximum, rationale)


def test_original_minimum_step_and_source_limits_still_apply():
    original = reference_policy()
    with pytest.raises(IntegrationError):
        SourceOrdinaryStepSizes(2**-40, 2**-40, 'Below original minimum.').apply(original)
    with pytest.raises(IntegrationError):
        replace(SourceOrdinaryStepSizes(.1, .1, 'reason'), classification='measured_public_data')


def test_mutated_declaration_cannot_be_applied():
    sizes = SourceOrdinaryStepSizes(.1, .1, 'reason')
    object.__setattr__(sizes, 'maximum_step_s', math.inf)
    with pytest.raises(IntegrationError):
        sizes.apply(reference_policy())
