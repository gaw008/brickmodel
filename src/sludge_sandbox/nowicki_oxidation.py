"""Source-condition shrinking-core times for a preformed municipal-sludge char.

Only two endpoint fitted slopes enter inverse-temperature interpolation.
The response is the increasing figure coordinate, not a mass/molar inventory.
"""
import hashlib
import json
import math
import os
from pathlib import Path
import stat
import sys
from typing import Any, Sequence

TRAINING_SHA256 = "565592bfd4e7bffe7e93ad7c553a2228ffc54e76c6f5f871ca471d7894702d42"
SOURCE_SHA256 = "f2c497bf09fd657213e2cf3fe41a0bc66a9e3286f52880b22b6ae536b821f6e7"
DEFAULT_LEVELS = (.1, .2, .3, .4, .5, .6, .7, .8)


class CharOxidationError(ValueError):
    """Invalid input or source data for this narrowly specified response model."""


def _read(path: Path, expected: str) -> dict[str, Any]:
    with os.fdopen(os.open(path, os.O_RDONLY | os.O_NONBLOCK), "rb") as stream:
        if not stat.S_ISREG(os.fstat(stream.fileno()).st_mode):
            raise CharOxidationError(f"regular_{path.name}_required")
        raw = stream.read(65537)
    if len(raw) > 65536 or hashlib.sha256(raw).hexdigest() != expected:
        raise CharOxidationError(f"reviewed_{path.name}_changed")
    return json.loads(raw)


def _number(value: object, name: str) -> float:
    if type(value) not in (float, int, str):
        raise CharOxidationError(f"finite_{name}_required")
    if isinstance(value, str) and len(value) > 128:
        raise CharOxidationError(f"bounded_{name}_required")
    try:
        result = float(value)
    except (ValueError, OverflowError) as exc:
        raise CharOxidationError(f"finite_{name}_required") from exc
    if not math.isfinite(result):
        raise CharOxidationError(f"finite_{name}_required")
    return result


def calculate_nowicki_oxygen_times(
    source_directory: str | Path, *, temperature_c: object = 500.,
    conversion_levels: Sequence[object] = DEFAULT_LEVELS,
) -> dict[str, Any]:
    """Calculate prescribed alpha_plot hitting times at fixed 10 vol.% oxygen.

450--550 C is an interpolation domain, not a validated continuous material law.
0.1--0.8 is the selected figure-response domain; no oxygen/energy or mass balance
can be inferred from these times. Source figure observations are not loaded.
"""
    directory = Path(source_directory)
    training = _read(directory/'training.json', TRAINING_SHA256)
    source = _read(directory/'source_metadata.json', SOURCE_SHA256)
    temperature = _number(temperature_c, 'temperature_c')
    if not 450. <= temperature <= 550.:
        raise CharOxidationError('temperature_outside_450_to_550_C')
    if not isinstance(conversion_levels, (list, tuple)) or not 1 <= len(conversion_levels) <= 64:
        raise CharOxidationError('one_to_64_explicit_conversion_levels_required')
    levels = [_number(a, 'alpha_plot') for a in conversion_levels]
    if any(not .1 <= a <= .8 for a in levels):
        raise CharOxidationError('alpha_plot_outside_selected_0.1_to_0.8_domain')
    temperature_k = temperature+273.15
    low, high = training['rows']
    t_low, t_high = float(low['temperature_k']), float(high['temperature_k'])
    k_low, k_high = float(low['ks_s_inv']), float(high['ks_s_inv'])
    weight = (1/temperature_k-1/t_low)/(1/t_high-1/t_low)
    # Preserve the original endpoint values at their exact labels.
    rate = (k_low if temperature == 450. else k_high if temperature == 550.
            else math.exp((1-weight)*math.log(k_low)+weight*math.log(k_high)))
    predictions = []
    for alpha in levels:
        phi = -math.expm1(math.log1p(-alpha)/3.)
        predictions.append(dict(alpha_plot=alpha, phi=phi, time_s=phi/rate,
            coordinate_rate_s_inv=3*rate*math.exp((2/3)*math.log1p(-alpha))))
    model = dict(id=training['interpolation']['id'],
                 inverse_temperature_weight=weight, rate_s_inv=rate,
                 equation=training['equation'], interpolation=training['interpolation'])
    trace = {
        'temperature_k': dict(formula='temperature_c+273.15', dependencies=['temperature_c']),
        'model.inverse_temperature_weight': dict(
            formula='(1/T-1/T_low)/(1/T_high-1/T_low)',
            dependencies=['temperature_k', 'training.rows.0.temperature_k', 'training.rows.1.temperature_k']),
        'model.rate_s_inv': dict(formula=training['interpolation']['formula'],
            dependencies=['model.inverse_temperature_weight', 'training.rows.0.ks_s_inv', 'training.rows.1.ks_s_inv'],
            source_id=source['id'], source_locators=[low['locator'], high['locator']]),
    }
    for i in range(len(predictions)):
        prefix = f'predictions.{i}'
        trace[f'{prefix}.phi'] = dict(formula=training['equation']['phi'],
            dependencies=[f'{prefix}.alpha_plot'], source_id=source['id'],
            source_locator=training['equation']['locator'])
        trace[f'{prefix}.time_s'] = dict(formula='phi/model.rate_s_inv',
            dependencies=[f'{prefix}.phi', 'model.rate_s_inv'])
        trace[f'{prefix}.coordinate_rate_s_inv'] = dict(formula=training['equation']['rate'],
            dependencies=[f'{prefix}.alpha_plot', 'model.rate_s_inv'],
            source_id=source['id'], source_locator=training['equation']['locator'])
    return dict(schema='nowicki_oxygen_times_result_v1', status='calculated',
        temperature_c=temperature, temperature_k=temperature_k,
        conditions=training['gas'], training=training, source=source,
        model=model, predictions=predictions, trace=trace,
        identity=dict(training_sha256=TRAINING_SHA256, source_metadata_sha256=SOURCE_SHA256,
            module_sha256=hashlib.sha256(Path(__file__).read_bytes()).hexdigest(),
            python=sys.version.split()[0]),
        input_classification=dict(temperature_c='virtual_design_choice',
            alpha_plot_levels='virtual_design_choice', source_ks='derived_from_evidence'),
        uncertainty=dict(experimental_variability=None, parameter_confidence_interval=None,
            reason='Only two printed author-fitted slopes; no residual degrees of freedom or replicate variance.'),
        qualification=dict(material_id=source['material_id'],
            response='increasing alpha_plot coordinate; printed Eq1 normalization conflict retained',
            selected_alpha_plot_domain=[.1, .8], oxygen_mole_fraction=.1,
            observations_loaded=False, experimental_validation_performed=False,
            mass_or_molar_conversion_admitted=False, reaction_heat=None,
            oxygen_consumption=None, product_gas_stoichiometry=None,
            energy_balance_solved=False, dynamic_temperature_solved=False,
            full_firing_cycle=False, full_material_package=False,
            table3_A_or_concentration_power_used=False))
