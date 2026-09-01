from __future__ import annotations

import copy
import hashlib
import json
from pathlib import Path

from .types import CaseConfig, NormalizedFeed
from .units import degc_to_k, water_per_dry_mass


def canonical_json_bytes(value: object) -> bytes:
    return json.dumps(value, sort_keys=True, separators=(",", ":"), ensure_ascii=False).encode("utf-8")


def sha256_json(value: object) -> str:
    return hashlib.sha256(canonical_json_bytes(value)).hexdigest()


def load_case(path: Path | str) -> CaseConfig:
    source_path = Path(path).resolve()
    raw = json.loads(source_path.read_text(encoding="utf-8"))
    resolved = copy.deepcopy(raw)
    if isinstance(resolved, dict):
        forming = resolved.get("forming")
        if isinstance(forming, dict) and "initial_temperature_degC" in forming:
            forming["initial_temperature_K"] = degc_to_k(forming["initial_temperature_degC"])
        kiln = resolved.get("kiln")
        profile = kiln.get("profile") if isinstance(kiln, dict) else None
        if isinstance(profile, list):
            for knot in profile:
                if not isinstance(knot, dict):
                    continue
                if "gas_temperature_degC" in knot:
                    knot["gas_temperature_K"] = degc_to_k(knot["gas_temperature_degC"])
                if "wall_temperature_degC" in knot:
                    knot["wall_temperature_K"] = degc_to_k(knot["wall_temperature_degC"])
    return CaseConfig(raw=resolved, source_path=source_path, content_hash=sha256_json(resolved))


def normalize_feedstocks(case: CaseConfig) -> NormalizedFeed:
    feedstocks = case.raw.get("feedstocks", {})
    fractions = {name: float(feed.get("dry_mass_fraction", 0.0)) for name, feed in feedstocks.items()}
    total = sum(fractions.values())
    if total <= 0:
        raise ValueError("dry feed fractions must have a positive sum")
    dry = {name: value / total for name, value in fractions.items()}
    water = {
        name: water_per_dry_mass(float(feed.get("free_moisture_wet_basis", 0.0)))
        for name, feed in feedstocks.items()
    }
    mixture = sum(dry[name] * water[name] for name in dry)
    return NormalizedFeed(dry, water, mixture)
