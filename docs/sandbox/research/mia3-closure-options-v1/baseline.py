"""Execute the preregistered, same-protocol MIA3 empirical baseline once.

This is a data calculation, not a physical sintering solver. No application,
EOS, plotting, fitting-library or network import is needed.
"""
import argparse
from datetime import datetime, timezone
from decimal import Decimal, localcontext
from fractions import Fraction
from hashlib import sha256
import json
from pathlib import Path


INPUT_SHA = "26bc48e2718a22296daf38bf9a6b9ca41b9d76c5aaf8f4b799b5c4709692cf44"
PREREG_SHA = "0064889f13b4a8f6ce9e29148d4918c1861e7d49465784664f8ad987573150b3"
DIRECTORY = Path(__file__).resolve().parent
INPUT = DIRECTORY.parent / "material-closure-next-v1/AREIAS2025_MIA3_TABLE6.json"


def checked_read(path, expected_sha):
    raw = path.read_bytes()
    if sha256(raw).hexdigest() != expected_sha:
        raise ValueError(f"Frozen input changed: {path.name}")
    return raw


def decimal_text(value):
    with localcontext() as ctx:
        ctx.prec = 50
        return str(Decimal(value.numerator) / Decimal(value.denominator))


def number(value):
    return {"exact_fraction": str(value), "decimal_display": decimal_text(value)}


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--output", type=Path, default=DIRECTORY / "BASELINE_RESULT.json")
    args = parser.parse_args()
    checked_read(DIRECTORY / "BASELINE_PREREGISTRATION.md", PREREG_SHA)
    data = json.loads(checked_read(INPUT, INPUT_SHA))
    rows = [r for r in data["observations"] if r["quantity"] == "linear_shrinkage_percent"]
    if (len(rows) != 4 or {r["firing_temperature_c"] for r in rows} != {"1150", "1160", "1170", "1180"}
            or any(r["formulation"] != "MIA3" or r["unit"] != "percent" for r in rows)):
        raise ValueError("The frozen MIA3 observation contract is not satisfied")
    observations = {int(r["firing_temperature_c"]): r for r in rows}
    values = {t: Fraction(r["printed_value"]) for t, r in observations.items()}
    # Only these two labels enter either fitted coefficient.
    a = values[1150]
    b = (values[1170] - values[1150]) / 20
    predictions = []
    errors = []
    for temperature, scope in ((1160, "interpolation"), (1180, "extrapolation_above_training_range")):
        prediction = a + b * (temperature - 1150)
        observation = values[temperature]
        error = prediction - observation
        errors.append(error)
        predictions.append({
            "temperature_c": temperature, "prediction_scope": scope,
            "observation_id": observations[temperature]["observation_id"],
            "observed_shrinkage_percent": number(observation),
            "predicted_shrinkage_percent": number(prediction),
            "signed_error_percentage_points": number(error),
            "absolute_error_percentage_points": number(abs(error)),
            "absolute_relative_error_percent": number(100 * abs(error) / abs(observation)),
            "source_printed_plus_minus": observations[temperature]["printed_plus_minus"],
            "plus_minus_statistical_interpretation": None,
        })
    mae = sum(map(abs, errors), Fraction(0)) / len(errors)
    mse = sum((e * e for e in errors), Fraction(0)) / len(errors)
    with localcontext() as ctx:
        ctx.prec = 50
        rmse = str((Decimal(mse.numerator) / Decimal(mse.denominator)).sqrt())
    result = {
        "executed_at_utc": datetime.now(timezone.utc).isoformat(),
        "preregistration_sha256": PREREG_SHA, "input_sha256": INPUT_SHA,
        "script_sha256": sha256(Path(__file__).read_bytes()).hexdigest(),
        "model": "s_hat(T_C)=a+b*(T_C-1150)",
        "model_classification": "same_material_same_reported_protocol_empirical_cold_shrinkage_baseline",
        "training_temperatures_c": [1150, 1170], "prediction_temperatures_c": [1160, 1180],
        "a_percent": number(a), "b_percentage_points_per_c": number(b),
        "predictions": predictions,
        "mae_percentage_points": number(mae), "mse_squared_percentage_points": number(mse),
        "rmse_percentage_points_decimal_display": rmse,
        "training_residual_note": "Two data points determine the affine line; zero training residual is not validation.",
        "acceptance_threshold": None, "scientific_acceptance": "not_assessed_no_threshold_registered",
        "blind_test": False, "sintering_mechanism_validated": False,
        "full_cycle_material_qualified": False,
        "uncertainty_note": "Printed +/- has unknown meaning and was not used as weight, tolerance or prediction interval.",
    }
    # Refuse to erase a previous attempt. A repeat needs a different output path.
    with args.output.open("x", encoding="utf-8") as stream:
        json.dump(result, stream, ensure_ascii=False, indent=2, allow_nan=False)
        stream.write("\n")
    print(json.dumps({"output": str(args.output), "mae_percentage_points": str(mae),
                      "rmse_percentage_points": rmse}, ensure_ascii=False))


if __name__ == "__main__":
    main()
