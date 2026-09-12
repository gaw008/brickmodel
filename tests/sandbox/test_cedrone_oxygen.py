"""Manufactured bookkeeping/entry tests: no Element, phase, EOS or equilibrium."""
from dataclasses import replace
from fractions import Fraction as F
import importlib.util
import hashlib
import json
from pathlib import Path
import sys
from types import SimpleNamespace

import pytest

from sludge_sandbox import cedrone_oxygen as co
from sludge_sandbox.tp_equilibrium import TPPolicy, TPResult

ROOT = Path(__file__).resolve().parents[2]
WEIGHTS = dict(zip(co.ELEMENTS, (12.011, 1.008, 15.999, 14.007, 32.06)))
SPEC = importlib.util.spec_from_file_location("cedrone_cli", ROOT / "examples/sandbox/run_cedrone_oxygen.py")
cli = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(cli)


def manufactured_result(inputs):
    """A feasible elemental inventory, explicitly not an equilibrium solution."""
    source = json.loads((ROOT / "data/sandbox/research/tp-equilibrium-v1/derived.json").read_text())
    b = inputs.pool.element_mol
    n = [F() for _ in co.SPECIES]
    for i, value in ((0, b[1] / 2), (5, b[2] / 2), (6, b[3] / 2), (17, b[4] / 2), (18, b[0])):
        n[i] = value
    raw = tuple(float(value / 1000) for value in n)
    actual = tuple(F(value) * 1000 for value in raw)
    out = (actual[18], 2 * actual[0], 2 * actual[5], 2 * actual[6], 2 * actual[17])
    loaded = {"gas_atomic_weights_kg_kmol": WEIGHTS, "species": tuple(
        {"name": row["name"], "composition": row["composition"]} for row in source["species"])}
    point = {"amounts_kmol": raw, "loaded_definition": loaded, "temperature_k": 800., "pressure_pa": 100000.}
    return TPResult("completed", None, inputs.pool, TPPolicy().definition(), None, point, point,
                    {"checks": {"manufactured_seam": True}, "amounts_mol": actual,
                     "element_residual_mol": tuple(a - v for a, v in zip(out, b))}, None,
                    {"model_sha256": co.MODEL_SHA256}, {"kind": "actual_cantera", "version": "3.2.0"},
                    0, 0, 0., True)


def fake_runtime(monkeypatch, *, weight_failure=None, solve_callback=None, tp_path=None):
    calls = []
    def element(name):
        if name == weight_failure:
            raise RuntimeError("manufactured_element_read_failure")
        return SimpleNamespace(symbol=name, weight=WEIGHTS[name])
    def solve(pool, source_root, **kwargs):
        calls.append((pool, kwargs))
        inputs = co.derive_cedrone_oxygen_pool(source_root, F(1, 4), WEIGHTS)
        result = manufactured_result(inputs)
        return solve_callback(result) if solve_callback else result
    runtime = (SimpleNamespace(__version__="3.2.0", Element=element), co,
               SimpleNamespace(TPPolicy=TPPolicy, solve_tp=solve,
                               __file__=tp_path or sys.modules[TPPolicy.__module__].__file__))
    monkeypatch.setattr(cli, "load_runtime", lambda: runtime)
    return calls


def test_exact_additions_use_original_pool_and_full_added_mass():
    records = [co.derive_cedrone_oxygen_pool(ROOT, value, WEIGHTS).definition() for value in (F(), F(1, 4), F(1))]
    base, quarter, one = records
    assert one["added_O2_mol"] == 4 * quarter["added_O2_mol"]
    assert quarter["added_N2_mol"] / quarter["added_O2_mol"] == F(79, 21)
    for row in records:
        assert row["base_element_mol"] == base["total_element_mol"]
        assert row["model_input_mass_kg"] == F(".704") + row["added_gas_mass_kg"]
        assert row["total_element_mol"][0] == base["total_element_mol"][0]
    inp = co.derive_cedrone_oxygen_pool(ROOT, F(1, 4), WEIGHTS)
    assert inp.pool.basis_id == "CEDRONE_TABLE4_REPORTED_SAMPLE_1KG_CONDITIONAL_CHONS"
    output = co.check_cedrone_oxygen_result(manufactured_result(inp), inp)
    assert len(output["species"]) == 19
    assert output["mass_audit"]["residual_kg"] == output["mass_audit"]["weighted_element_residual_kg"]


def test_same_version_phase_weights_must_match_element_reads():
    inputs = co.derive_cedrone_oxygen_pool(ROOT, F(1, 4), WEIGHTS)
    result = manufactured_result(inputs)
    changed = dict(result.final)
    changed["loaded_definition"] = dict(changed["loaded_definition"])
    changed["loaded_definition"]["gas_atomic_weights_kg_kmol"] = WEIGHTS | {"O": 16.}
    with pytest.raises(ValueError, match="atomic_weights_binding"):
        co.check_cedrone_oxygen_result(replace(result, initial=changed, final=changed), inputs)


def test_source_change_and_unsupported_inputs_are_rejected(tmp_path):
    path = tmp_path / "data/sandbox/research/cedrone2024-element-pool-v1"
    path.mkdir(parents=True)
    (path / "printed-pool.json").write_text("{}")
    with pytest.raises(ValueError, match="source_hash"):
        co.derive_cedrone_oxygen_pool(tmp_path, F(1, 4), WEIGHTS)
    for value, weights in ((F(1, 2), WEIGHTS), (True, WEIGHTS), (F(1), WEIGHTS | {"O": 0.})):
        with pytest.raises(ValueError):
            co.derive_cedrone_oxygen_pool(ROOT, value, weights)


def test_cli_help_bad_lambda_and_existing_output_do_not_load_runtime(monkeypatch, tmp_path):
    monkeypatch.setattr(cli, "load_runtime", lambda: pytest.fail("runtime must not load"))
    with pytest.raises(SystemExit) as help_exit:
        cli.main(["--help"])
    assert help_exit.value.code == 0
    with pytest.raises(SystemExit):
        cli.main(["--source-root", str(ROOT), "--output-dir", str(tmp_path / "new"), "--lambda", "0.5"])
    assert cli.main(["--source-root", str(ROOT), "--output-dir", str(tmp_path), "--lambda", "1/4"]) == 2


@pytest.mark.parametrize("change_code", (False, True))
def test_one_worker_call_saves_complete_inputs_and_nineteen_outputs(monkeypatch, tmp_path, change_code):
    folder = tmp_path / "calculation"
    tp_path = tmp_path / "manufactured_tp_source.py"
    original_bytes = Path(sys.modules[TPPolicy.__module__].__file__).read_bytes()
    tp_path.write_bytes(original_bytes)
    in_flight = []
    def observe(result):
        in_flight.append(json.loads((folder / "STATUS.json").read_text()))
        if change_code:
            tp_path.write_bytes(original_bytes + b"\n# manufactured in-flight change\n")
        return result
    calls = fake_runtime(monkeypatch, solve_callback=observe, tp_path=str(tp_path))
    assert cli.run_worker(ROOT, folder, F(1, 4)) == (1 if change_code else 0)
    assert len(calls) == 1
    assert in_flight[0]["new_solve_attempts"] == 0
    assert in_flight[0]["attempt_count_final"] is False
    saved = json.loads((folder / "INPUT.json").read_text())
    assert set(saved["element_reads"]) == set(co.ELEMENTS)
    identities = saved["runtime"]["code_identity"]
    assert set(identities) == {"cedrone_oxygen", "tp_equilibrium"}
    assert identities["tp_equilibrium"]["sha256"] == hashlib.sha256(original_bytes).hexdigest()
    assert identities["tp_equilibrium"]["bytes"] == len(original_bytes)
    status = json.loads((folder / "STATUS.json").read_text())
    assert status["attempt_count_final"] is True
    assert status["atomic_weights_binding_checked"] is True
    assert status["runtime_code_unchanged"] is (not change_code)
    assert (folder / "RESULT.json").exists()
    assert len(json.loads((folder / "OBSERVABLES.json").read_text())["species"]) == 19


def test_failed_element_read_keeps_completed_prefix_and_never_solves(monkeypatch, tmp_path):
    calls = fake_runtime(monkeypatch, weight_failure="O")
    folder = tmp_path / "calculation"
    assert cli.run_worker(ROOT, folder, F(1, 4)) == 1
    assert calls == []
    assert set(json.loads((folder / "INPUT.json").read_text())["element_reads"]) == {"C", "H"}
    assert json.loads((folder / "STATUS.json").read_text())["new_solve_attempts"] == 0


def test_result_first_write_failure_preserves_called_state(monkeypatch, tmp_path):
    calls = fake_runtime(monkeypatch)
    original = cli.save
    def fail_result(path, value, **kwargs):
        if path.name == "RESULT.json":
            raise OSError("manufactured_result_write_failure")
        return original(path, value, **kwargs)
    monkeypatch.setattr(cli, "save", fail_result)
    folder = tmp_path / "calculation"
    assert cli.run_worker(ROOT, folder, F(1, 4)) == 2
    status = json.loads((folder / "STATUS.json").read_text())
    assert len(calls) == status["new_solve_attempts"] == 1
    assert status["stage"] == "solve_returned"
    assert status["status"] != "completed"
    assert status["attempt_count_final"] is True


def test_returned_timeout_keeps_result_and_does_not_claim_completion(monkeypatch, tmp_path):
    now = [0.]
    monkeypatch.setattr(cli.time, "monotonic", lambda: now[0])
    def delayed(result):
        now[0] = 31.
        return result
    calls = fake_runtime(monkeypatch, solve_callback=delayed)
    folder = tmp_path / "calculation"
    assert cli.run_worker(ROOT, folder, F(1, 4)) == 1
    assert len(calls) == 1
    assert (folder / "RESULT.json").exists()
    assert json.loads((folder / "STATUS.json").read_text())["status"] == "resource_limit"


def test_parent_uses_code_relative_supervisor_and_one_isolated_worker(monkeypatch, tmp_path):
    captured = []
    def supervise(*args, **kwargs):
        captured.append((args, kwargs))
        return {"status": "complete", "returncode": 0, "inputs_unchanged": True,
                "cleanup": {"leader_reaped": True}}
    monkeypatch.setattr(cli, "load_supervisor", lambda: SimpleNamespace(run_attempt=supervise))
    data_root = tmp_path / "data-only"
    data_root.mkdir()
    output = tmp_path / "new-run"
    assert cli.main(["--source-root", str(data_root), "--output-dir", str(output), "--lambda", "1/4"]) == 0
    assert len(captured) == 1
    args, kwargs = captured[0]
    assert kwargs["timeout_s"] == 40. and kwargs["cleanup_grace_s"] == 5.
    assert "-I" in args[1] and "--worker" in args[1]
    assert str(data_root) not in str(cli.supervisor_path())
