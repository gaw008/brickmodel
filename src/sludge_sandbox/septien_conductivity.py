"""Pinned Septien donor measurements with a declared two-node k(W) extension.

The original measurement temperature is unknown. Temperature independence and
transfer from VIP faecal sludge to the Arlabosse hybrid are model choices, with
unknown errors. Source 90% intervals are not total conductivity error bounds.
No water EOS or transport host is instantiated by this read-only provider.
"""
from dataclasses import dataclass, field
from decimal import Decimal
from fractions import Fraction as F
import hashlib
import json
import math
from pathlib import Path
from xml.etree import ElementTree as ET


SOURCE_ID = 'SRC_SEPTIEN_2020_FAECAL_SLUDGE_THERMAL'
MODEL_ID = 'SEPTIEN2020_TWO_NODE_CONDITIONAL_CONDUCTIVITY_V1'
SOURCE_FILENAME = 'fecal2019-original.xml'
SOURCE_SHA256 = 'cda0a7fba9cea9dc3b20d8a4b68f36ad571dcaf22deaec7386f323dd95714a0f'
FACTS_PATH = 'data/sandbox/research/septien-conductivity-v1/source.json'
FACTS_SHA256 = '5d68c9d8e4d2c2b263270b66af62d6f7b6d1dbd141bbdb9db53fa0d61cd16abd'
MODEL_PATH = 'data/sandbox/research/septien-conductivity-v1/model.json'
MODEL_SHA256 = 'c5d36c30be29b8f9aea569dde355ad0580b6c5d8474a0f85cc4a036c6976cb15'
MOISTURE_DOMAIN = (.30, .80)
TEMPERATURE_DOMAIN_K = (308.15, 368.15)
QUALIFICATION = 'conditional_cross_material_donor_conductivity_not_material_admission'
Coordinate = int | float | Decimal | F


class ConductivityError(ValueError):
    """Pinned source, nominal domain, or source-table correspondence failed."""


def _require(ok: bool, reason: str) -> None:
    if not ok:
        raise ConductivityError(reason)


def _coordinate(value: Coordinate) -> F:
    if type(value) in (int, F):
        return F(value)
    if type(value) is float and math.isfinite(value):
        return F(value)
    if type(value) is Decimal and value.is_finite():
        return F(value)
    raise ConductivityError('finite_numeric_coordinate_required')


def _read_source_file(path: Path, expected: str, kind: str) -> bytes:
    try:
        raw = path.read_bytes()
    except OSError as exc:
        raise ConductivityError(f'conductivity_{kind}_unavailable') from exc
    _require(hashlib.sha256(raw).hexdigest() == expected, f'conductivity_{kind}_changed')
    return raw


def _text(element: ET.Element) -> str:
    return ' '.join(''.join(element.itertext()).split())


def _reading(text: str) -> tuple[F, F]:
    pieces = text.split(' ± ')
    _require(len(pieces) == 2, 'conductivity_original_cell_format')
    try:
        value, half_width = map(F, pieces)
    except (ValueError, ZeroDivisionError) as exc:
        raise ConductivityError('conductivity_original_cell_number') from exc
    _require(value > 0 and half_width >= 0, 'conductivity_original_cell_domain')
    return value, half_width


def _ratio(value: F) -> list[int]:
    return [value.numerator, value.denominator]


@dataclass(frozen=True)
class ConductivitySourcePoint:
    """Original source measurements and exact wet-to-dry coordinate conversion."""
    row_label: str
    moisture_wet_percent_original: str
    conductivity_w_m_k_original: str
    moisture_wet_percent: F
    moisture_wet_percent_half_width: F
    moisture_dry_basis: F
    conductivity_w_m_k: F
    conductivity_half_width_w_m_k: F
    table_id: str = 'tbl0010'
    confidence_level: F = F(9, 10)
    measurement_temperature_c: None = None

    def to_record(self) -> dict:
        return {'table_id': self.table_id, 'row_label': self.row_label,
            'moisture_wet_percent_original': self.moisture_wet_percent_original,
            'conductivity_w_m_k_original': self.conductivity_w_m_k_original,
            'moisture_wet_percent': str(self.moisture_wet_percent),
            'moisture_wet_percent_half_width': str(self.moisture_wet_percent_half_width),
            'moisture_dry_basis_exact': _ratio(self.moisture_dry_basis),
            'conductivity_w_m_k_exact': _ratio(self.conductivity_w_m_k),
            'conductivity_half_width_w_m_k_exact': _ratio(self.conductivity_half_width_w_m_k),
            'confidence_level': float(self.confidence_level),
            'confidence_scope': 'original source sample repeatability only',
            'measurement_temperature_c': None}


@dataclass(frozen=True)
class ConductivityPoint:
    """Positive nominal k and an immutable provenance snapshot for that readout."""
    temperature_k: float
    moisture_kg_water_per_kg_dry: float
    k_w_m_k: float
    nominal_k_w_m_k: F
    binary64_projection_error_w_m_k: F
    model_identity: str
    source_ids: tuple[str, ...]
    _provenance_json: str = field(repr=False)
    unit: str = 'W/(m K)'
    interpolation_model_error: None = None
    temperature_extension_model_error: None = None
    pressure_extension_model_error: None = None
    cross_material_transfer_error: None = None
    total_model_uncertainty: None = None
    material_qualified: bool = False
    training_eligible: bool = False
    source_confidence_intervals_are_total_model_bounds: bool = False
    qualification: str = QUALIFICATION

    def to_record(self) -> dict:
        """Return fresh JSON-compatible provenance; no mutable provider state leaks."""
        return {'temperature_k': self.temperature_k,
            'moisture_kg_water_per_kg_dry': self.moisture_kg_water_per_kg_dry,
            'k_w_m_k': self.k_w_m_k, 'unit': self.unit,
            'nominal_k_w_m_k_exact': _ratio(self.nominal_k_w_m_k),
            'binary64_projection_error_w_m_k_exact': _ratio(self.binary64_projection_error_w_m_k),
            'numerical_error_scope': 'final binary64 projection only; no physical uncertainty bound',
            'model_identity': self.model_identity, 'source_ids': list(self.source_ids),
            'provenance': json.loads(self._provenance_json),
            'interpolation_model_error': None, 'temperature_extension_model_error': None,
            'pressure_extension_model_error': None, 'cross_material_transfer_error': None,
            'total_model_uncertainty': None, 'material_qualified': False, 'training_eligible': False,
            'source_confidence_intervals_are_total_model_bounds': False,
            'qualification': self.qualification}


def _table_points(article: ET.Element, facts: dict) -> tuple[ConductivitySourcePoint, ...]:
    """Bind both nominal parameters to original tbl0010 rows and physical columns."""
    tables = article.findall(".//table-wrap[@id='tbl0010']")
    _require(len(tables) == 1 and facts['table']['id'] == 'tbl0010', 'conductivity_table_identity')
    table = tables[0]
    _require(table.findtext('label') == 'Table 2', 'conductivity_table_label')
    headers = table.findall('table/thead/tr')[0].findall('th')
    columns = [name for header in headers for name in
               [_text(header)]*int(header.get('colspan', '1'))]
    indices = []
    for key in ('moisture_heading', 'conductivity_heading'):
        matches = [index for index, name in enumerate(columns) if name == facts['table'][key]]
        _require(len(matches) == 1, 'conductivity_table_column_identity')
        indices.append(matches[0])
    rows = [tuple(_text(cell) for cell in row.findall('td'))
            for row in table.findall('table/tbody/tr')]
    result = []
    for fact in facts['points']:
        matches = [row for row in rows if row and row[0] == fact['row_label']]
        _require(len(matches) == 1 and len(matches[0]) == len(columns), 'conductivity_table_row_identity')
        original_w, original_k = (matches[0][index] for index in indices)
        _require(original_w == fact['moisture_wet_percent_original'] and
                 original_k == fact['conductivity_w_m_k_original'], 'conductivity_original_cell_mismatch')
        w, w_half = _reading(original_w)
        k, k_half = _reading(original_k)
        _require(w < 100, 'conductivity_original_moisture_domain')
        dry = w/(100-w)
        _require(dry == F(fact['moisture_dry_basis']), 'conductivity_wet_to_dry_conversion')
        _require((w, w_half, k, k_half) == tuple(F(fact[key]) for key in (
            'moisture_wet_percent', 'moisture_wet_percent_half_width',
            'conductivity_w_m_k', 'conductivity_w_m_k_half_width')), 'conductivity_original_cell_numeric_mismatch')
        result.append(ConductivitySourcePoint(fact['row_label'], original_w, original_k,
                                             w, w_half, dry, k, k_half))
    _require(len(result) == 2 and result[0].moisture_dry_basis < result[1].moisture_dry_basis,
             'conductivity_two_ordered_source_nodes_required')
    return tuple(result)


@dataclass(frozen=True)
class SeptienConductivity:
    """Read only pinned original XML plus facts/model files at explicit locations."""
    repository_root: Path
    source_directory: Path
    _identity: str = field(init=False, repr=False)

    def __post_init__(self) -> None:
        object.__setattr__(self, 'repository_root', Path(self.repository_root).resolve())
        object.__setattr__(self, 'source_directory', Path(self.source_directory).resolve())
        object.__setattr__(self, '_identity', self.binding())

    def _load(self) -> tuple[dict, dict, tuple[ConductivitySourcePoint, ...]]:
        facts = json.loads(_read_source_file(self.repository_root/FACTS_PATH, FACTS_SHA256, 'facts'))
        model = json.loads(_read_source_file(self.repository_root/MODEL_PATH, MODEL_SHA256, 'model'))
        raw = _read_source_file(self.source_directory/SOURCE_FILENAME, SOURCE_SHA256, 'original_xml')
        _require(facts['source_id'] == SOURCE_ID and model['model_id'] == MODEL_ID and
                 facts['primary_asset']['sha256'] == SOURCE_SHA256 and
                 len(raw) == facts['primary_asset']['bytes'] and
                 model['upstream']['source_facts_sha256'] == FACTS_SHA256 and
                 model['upstream']['original_xml_sha256'] == SOURCE_SHA256, 'conductivity_source_binding')
        # Hash admission precedes parsing; unknown XML is not interpreted.
        article = ET.fromstring(raw)
        dois = article.findall("./front/article-meta/article-id[@pub-id-type='doi']")
        _require(len(dois) == 1 and _text(dois[0]) == facts['doi'], 'conductivity_original_doi_mismatch')
        statistical = article.findall(".//sec[@id='sec0055']")
        _require(len(statistical) == 1, 'conductivity_source_confidence_location')
        text = _text(statistical[0])
        _require('duplicates' in text and 'Student’s t-distribution' in text and '90 % confidence interval' in text,
                 'conductivity_source_confidence_semantics')
        points = _table_points(article, facts)
        _require(tuple((str(point.moisture_dry_basis), str(point.conductivity_w_m_k)) for point in points) ==
                 tuple((str(F(w)), str(F(k))) for w, k in model['parameter_derivation']['nominal_nodes']),
                 'conductivity_model_source_nodes_mismatch')
        return facts, model, points

    @staticmethod
    def _binding() -> str:
        content = (MODEL_ID, SOURCE_SHA256, FACTS_SHA256, MODEL_SHA256,
                   MOISTURE_DOMAIN, TEMPERATURE_DOMAIN_K)
        return hashlib.sha256(json.dumps(content, separators=(',', ':')).encode()).hexdigest()

    def binding(self) -> str:
        self._load()
        return self._binding()

    def _check(self) -> tuple[dict, dict, tuple[ConductivitySourcePoint, ...]]:
        loaded = self._load()
        _require(self._binding() == self._identity, 'conductivity_provider_content_changed')
        return loaded

    @property
    def model_identity(self) -> str:
        self._check()
        return self._identity

    @property
    def source_ids(self) -> tuple[str, ...]:
        self._check()
        return SOURCE_ID, MODEL_ID, SOURCE_SHA256, FACTS_SHA256, MODEL_SHA256

    def source_points(self) -> tuple[ConductivitySourcePoint, ...]:
        """Expose original measured nodes, even outside the narrower model domain."""
        return self._check()[2]

    def _definition(self, facts: dict, model: dict,
                    points: tuple[ConductivitySourcePoint, ...]) -> dict:
        return {'model_identity': self._identity, 'source_facts': facts, 'model_definition': model,
            'verified_original_table': {'source_sha256': SOURCE_SHA256, 'table_id': 'tbl0010',
                'reading': 'matched original JATS column headings and exact two row cell strings',
                'points': [point.to_record() for point in points]},
            'verified_assets': {'original_xml': {'filename': SOURCE_FILENAME, 'sha256': SOURCE_SHA256},
                'facts': {'path': FACTS_PATH, 'sha256': FACTS_SHA256},
                'model': {'path': MODEL_PATH, 'sha256': MODEL_SHA256}},
            'material_qualified': False, 'training_eligible': False, 'qualification': QUALIFICATION}

    def definition(self) -> dict:
        """Fresh machine-readable original measurements and separate model choices."""
        return self._definition(*self._check())

    def evaluate(self, temperature_k: Coordinate,
                 moisture_kg_water_per_kg_dry: Coordinate) -> ConductivityPoint:
        """Interpolate nominal source coordinates inside the explicit exploration domain."""
        facts, model, points = self._check()
        temperature = _coordinate(temperature_k)
        moisture = _coordinate(moisture_kg_water_per_kg_dry)
        _require(F(TEMPERATURE_DOMAIN_K[0]) <= temperature <= F(TEMPERATURE_DOMAIN_K[1]),
                 'conductivity_temperature_domain_exit')
        _require(F(MOISTURE_DOMAIN[0]) <= moisture <= F(MOISTURE_DOMAIN[1]),
                 'conductivity_moisture_domain_exit')
        low, high = points
        weight = (moisture-low.moisture_dry_basis)/(high.moisture_dry_basis-low.moisture_dry_basis)
        nominal = low.conductivity_w_m_k+weight*(high.conductivity_w_m_k-low.conductivity_w_m_k)
        k = float(nominal)
        _require(0 <= weight <= 1 and math.isfinite(k) and k > 0, 'conductivity_invalid_interpolation')
        trace = self._definition(facts, model, points)
        # Retain exact coordinates when the caller supplied a nonbinary rational.
        trace['evaluation_coordinates_exact'] = {'temperature_k': _ratio(temperature),
            'moisture_kg_water_per_kg_dry': _ratio(moisture)}
        return ConductivityPoint(float(temperature), float(moisture), k, nominal, abs(F(k)-nominal),
            self._identity, (SOURCE_ID, MODEL_ID, SOURCE_SHA256, FACTS_SHA256, MODEL_SHA256),
            json.dumps(trace, sort_keys=True, separators=(',', ':'), ensure_ascii=False))
