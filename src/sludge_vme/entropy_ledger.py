"""Recompute signed entropy balances from required saved arrays only.

Direct-file CLI uses the standard library and does not import sludge_vme's
package initializer, a model, a thermodynamic operator or a solver.
"""
from __future__ import annotations

import argparse
from copy import deepcopy
import json
from pathlib import Path


def calculate_saved_entropy_ledger(ledger: dict) -> dict:
    """Recompute each interval at its own origin; never reuse stored PASS flags."""
    series = ledger['series']
    times = series['time_s']
    stored = series['complete_stored_entropy_j_k']
    production = series['cumulative_entropy_production_j_k']
    exchange = series['cumulative_entropy_exchange_j_k']
    normalization = ledger['normalization']
    scale = normalization['energy_scale_j'] / normalization['reference_temperature_k']
    limit = normalization['acceptance_entropy_relative_record']['value']

    def interval(start: int, end: int) -> dict:
        indices = list(range(start, end + 1))
        delta_stored = [stored[k] - stored[start] for k in indices]
        delta_production = [production[k] - production[start] for k in indices]
        delta_exchange = [exchange[k] - exchange[start] for k in indices]
        residual = [(ds - dp) - de for ds, dp, de in zip(delta_stored, delta_production, delta_exchange)]
        absolute = [abs(value) for value in residual]
        relative = [value / scale for value in absolute]
        maximum = max(relative)
        return {'start_index': start, 'end_index': end,
            'time_s': [times[k] for k in indices],
            'origin_j_k': {'complete_stored_entropy': stored[start],
                'cumulative_entropy_production': production[start],
                'cumulative_entropy_exchange': exchange[start]},
            'signed_delta_stored_entropy_j_k': delta_stored,
            'signed_delta_entropy_production_j_k': delta_production,
            'signed_delta_entropy_exchange_j_k': delta_exchange,
            'signed_residual_j_k': residual, 'absolute_residual_j_k': absolute,
            'relative_residual_by_sample': relative,
            'maximum_absolute_residual_j_k': max(absolute),
            'maximum_relative_residual': maximum,
            'entropy_scale_j_k': scale, 'threshold_relative': limit,
            'sampled_same_origin_balance_passed': maximum < limit}

    full = ledger['intervals']['full_window']
    whole = interval(full['start_index'], full['end_index'])
    stages = {stage['name']: interval(stage['start_index'], stage['end_index'])
        for stage in ledger['intervals']['stages']}
    return {'full_window': whole, 'stages': stages,
        'all_declared_sampled_interval_balances_passed': whole['sampled_same_origin_balance_passed'] and all(stage['sampled_same_origin_balance_passed'] for stage in stages.values()),
        'qualification': ledger['qualification']}


def replay_saved_entropy_file(source: str | Path, *, ledger_path: list[str]) -> dict:
    """Read an explicit JSON path and recalculate; missing history raises KeyError."""
    ledger = json.loads(Path(source).read_text())
    for key in ledger_path:
        ledger = ledger[key]
    return {'schema': ledger['output_contract']['replay_schema'],
        'source_file': str(source), 'ledger_path': ledger_path,
        'source_ledger_schema': ledger['schema'],
        'series': deepcopy(ledger['series']),
        'intervals': deepcopy(ledger['intervals']),
        'normalization': deepcopy(ledger['normalization']),
        'recomputed': calculate_saved_entropy_ledger(ledger),
        'physical_model_calls': 0,
        'source_rates_integrated_or_missing_history_backfilled': False}


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('input', type=Path)
    parser.add_argument('--ledger-path', nargs='+', required=True)
    parser.add_argument('--out', type=Path, required=True)
    args = parser.parse_args()
    result = replay_saved_entropy_file(args.input, ledger_path=args.ledger_path)
    args.out.write_text(json.dumps(result, ensure_ascii=False, indent=2, allow_nan=False) + '\n')


if __name__ == '__main__':
    main()
