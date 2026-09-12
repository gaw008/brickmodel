"""Explicit material identities, separate mass analyses, and green-batch bookkeeping.

No mineral phases, constitutive properties, or missing native water are inferred.
Evidence IDs are retained for the application resolver; presence is not approval.
"""

from dataclasses import dataclass
import math
import re
from types import MappingProxyType
from typing import Mapping


class MaterialError(ValueError):
    """A material identity, mass basis, or batch is not defined consistently."""


MATERIAL_CLASSES = frozenset({
    "raw_sewage_sludge", "sewage_sludge_ash", "industrial_sludge", "clay", "shale",
    "coal_gangue", "pure_substance", "manufactured",
})
ANALYSIS_BASES = {
    "elemental": {"wet_total", "dry_solid", "dry_ash_free", "ash"},
    "oxide": {"dry_solid", "ash", "normalized_oxides"},
    "mineral_phase": {"dry_solid", "ash"},
    "proximate": {"wet_total", "dry_solid"},
    "loss_on_ignition": {"dry_solid", "ash"},
}
ELEMENT_SYMBOLS = frozenset((
    "H He Li Be B C N O F Ne Na Mg Al Si P S Cl Ar K Ca Sc Ti V Cr Mn Fe Co Ni Cu Zn "
    "Ga Ge As Se Br Kr Rb Sr Y Zr Nb Mo Tc Ru Rh Pd Ag Cd In Sn Sb Te I Xe Cs Ba La Ce "
    "Pr Nd Pm Sm Eu Gd Tb Dy Ho Er Tm Yb Lu Hf Ta W Re Os Ir Pt Au Hg Tl Pb Bi Po At Rn "
    "Fr Ra Ac Th Pa U Np Pu Am Cm Bk Cf Es Fm Md No Lr Rf Db Sg Bh Hs Mt Ds Rg Cn Nh Fl Mc Lv Ts Og"
).split())


def _analyte_kind(name: str, kind: str) -> None:
    if kind == "elemental" and name not in ELEMENT_SYMBOLS:
        raise MaterialError("Elemental analyses require element symbols, not compound/LOI labels")
    if kind == "oxide":
        match = re.fullmatch(r"([A-Z][a-z]?)(?:[1-9][0-9]*)?O(?:[1-9][0-9]*)?", name)
        if match is None or match[1] not in ELEMENT_SYMBOLS - {"O", "H"}:
            raise MaterialError("Oxide analysis requires explicit binary oxide formulas; water/LOI stay separate")
    if kind == "loss_on_ignition" and name != "LOI":
        raise MaterialError("LOI must be a separate analysis")
    if kind == "proximate" and name not in {"water", "ash", "volatile_matter", "fixed_carbon"}:
        raise MaterialError("Unknown proximate analyte")


def _text(value: str, name: str) -> None:
    if not isinstance(value, str) or not value.strip():
        raise MaterialError(f"{name} must be nonempty text")


def _number(value: float, name: str, *, positive: bool = False) -> float:
    try:
        if type(value) not in (int, float) or not math.isfinite(value):
            raise MaterialError(f"{name} must be a finite number")
        result = float(value)
    except OverflowError as exc:
        raise MaterialError(f"{name} exceeds finite range") from exc
    if (positive and result <= 0) or (not positive and result < 0):
        raise MaterialError(f"{name} outside nonnegative mass domain")
    return result


@dataclass(frozen=True)
class MaterialIdentity:
    material_id: str
    material_class: str
    batch_id: str
    source_node_ids: tuple[str, ...]

    def __post_init__(self):
        _text(self.material_id, "material_id")
        _text(self.batch_id, "batch_id")
        if not isinstance(self.material_class, str) or self.material_class not in MATERIAL_CLASSES:
            raise MaterialError("Unknown material class; raw sludge and ash must stay distinct")
        if not isinstance(self.source_node_ids, (tuple, list)) or not self.source_node_ids:
            raise MaterialError("Material identity source nodes are required")
        for source in self.source_node_ids:
            _text(source, "source_node_id")
        if len(set(self.source_node_ids)) != len(self.source_node_ids):
            raise MaterialError("Duplicate identity source")
        object.__setattr__(self, "source_node_ids", tuple(self.source_node_ids))


@dataclass(frozen=True)
class MassAnalysis:
    kind: str
    basis: str
    fractions: Mapping[str, float]
    closure: str
    source_node_id: str
    phase_identity_node_ids: Mapping[str, str] | None = None

    def __post_init__(self):
        if not isinstance(self.kind, str) or self.kind not in ANALYSIS_BASES:
            raise MaterialError("Unknown mass analysis kind")
        if not isinstance(self.basis, str) or self.basis not in ANALYSIS_BASES[self.kind]:
            raise MaterialError("Incompatible analysis basis")
        if self.closure not in ("partial", "complete"):
            raise MaterialError("Mass analysis must declare closure")
        _text(self.source_node_id, "source_node_id")
        if not isinstance(self.fractions, Mapping) or not self.fractions:
            raise MaterialError("Explicit analysis values are required")
        fractions = {}
        for name, fraction in self.fractions.items():
            _text(name, "analyte")
            _analyte_kind(name, self.kind)
            fractions[name] = _number(fraction, "mass_fraction")
            if fractions[name] > 1:
                raise MaterialError("A mass fraction cannot exceed one")
        total = math.fsum(fractions.values())
        # This is a rounding tolerance, not permission to normalize measured data.
        if total > 1 + 1e-12 or (self.closure == "complete" and abs(total - 1) > 1e-12):
            raise MaterialError("Mass analysis does not close on its declared basis")
        object.__setattr__(self, "fractions", MappingProxyType(fractions))
        if self.kind == "mineral_phase":
            phase_ids = self.phase_identity_node_ids
            if not isinstance(phase_ids, Mapping) or set(phase_ids) != set(fractions):
                raise MaterialError("Every mineral phase requires a separate source-backed identity node")
            for node_id in phase_ids.values():
                _text(node_id, "phase_identity_node_id")
            object.__setattr__(self, "phase_identity_node_ids", MappingProxyType(dict(phase_ids)))
        elif self.phase_identity_node_ids is not None:
            raise MaterialError("Phase identities cannot turn a different analysis into mineral phases")

    @property
    def unassigned_fraction(self) -> float:
        """Arithmetic difference only; its material identity remains unknown."""
        return 1 - math.fsum(self.fractions.values())


@dataclass(frozen=True)
class FeedPortion:
    identity: MaterialIdentity
    dry_mass_kg: float
    native_water_wet_fraction: float
    water_evidence_id: str

    def __post_init__(self):
        if not isinstance(self.identity, MaterialIdentity):
            raise MaterialError("Explicit material identity required")
        _number(self.dry_mass_kg, "dry_mass_kg", positive=True)
        water = _number(self.native_water_wet_fraction, "native_water_wet_fraction")
        if water >= 1:
            raise MaterialError("Wet-basis water fraction must be below one for a dry feed portion")
        _text(self.water_evidence_id, "water_evidence_id")
        _number(self.native_water_kg, "native_water_kg")

    @property
    def native_water_kg(self) -> float:
        fraction = self.native_water_wet_fraction
        return self.dry_mass_kg * fraction / (1 - fraction)

    @classmethod
    def from_wet_mass(cls, identity: MaterialIdentity, *, wet_mass_kg: float,
                      native_water_wet_fraction: float, water_evidence_id: str) -> "FeedPortion":
        wet = _number(wet_mass_kg, "wet_mass_kg", positive=True)
        fraction = _number(native_water_wet_fraction, "native_water_wet_fraction")
        if fraction >= 1:
            raise MaterialError("Wet-basis water fraction must be below one")
        return cls(identity, wet * (1 - fraction), fraction, water_evidence_id)


@dataclass(frozen=True)
class GreenBatch:
    portions: tuple[FeedPortion, ...]
    dry_mass_kg: float
    native_water_kg: float
    added_water_kg: float
    total_water_kg: float
    wet_mass_kg: float
    moisture_wet_fraction: float
    dry_mass_fractions: Mapping[str, float]
    required_evidence_ids: tuple[str, ...]
    scientific_status: str = "bookkeeping_only_sources_not_resolved"


def prepare_green_batch(portions: tuple[FeedPortion, ...], *, added_water_kg: float) -> GreenBatch:
    """Extra forming water is an explicit mass, never a second total moisture target."""
    if not isinstance(portions, (list, tuple)) or not portions:
        raise MaterialError("At least one feed portion is required")
    if any(not isinstance(p, FeedPortion) for p in portions):
        raise MaterialError("Invalid feed portion")
    ids = [p.identity.material_id for p in portions]
    if len(ids) != len(set(ids)):
        raise MaterialError("Duplicate feed material ids")
    extra = _number(added_water_kg, "added_water_kg")
    try:
        dry = math.fsum(p.dry_mass_kg for p in portions)
        native = math.fsum(p.native_water_kg for p in portions)
        total_water = math.fsum((native, extra))
        wet = math.fsum((dry, total_water))
    except OverflowError as exc:
        raise MaterialError("Batch mass exceeds finite range") from exc
    evidence = {node for p in portions for node in p.identity.source_node_ids}
    evidence.update(p.water_evidence_id for p in portions)
    return GreenBatch(tuple(portions), dry, native, extra, total_water, wet,
                      total_water / wet,
                      MappingProxyType({p.identity.material_id: p.dry_mass_kg / dry for p in portions}),
                      tuple(sorted(evidence)))
