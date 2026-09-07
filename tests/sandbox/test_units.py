import pytest

from sludge_sandbox.units import UnitError, convert


def test_temperature_offset_and_kinetic_energy_are_explicit():
    assert convert(100, "degC", "K") == pytest.approx(373.15)
    assert convert(114, "kJ/mol", "J/mol") == pytest.approx(114000)
    assert convert(10, "wt%", "1") == pytest.approx(0.1)
    assert convert(1, "1/min", "1/s") == pytest.approx(1 / 60)


def test_basis_changing_conversion_is_refused():
    with pytest.raises(UnitError):
        convert(100, "J/mol", "J/kg")


@pytest.mark.parametrize("value", [float("nan"), float("inf"), True, "2", 10**1000])
def test_nonfinite_or_coerced_values_are_rejected(value):
    with pytest.raises(UnitError):
        convert(value, "K", "K")
