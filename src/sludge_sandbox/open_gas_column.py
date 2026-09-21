"""Attach one shared gas reservoir to the outer face of a source wet column.

The ordinary midpoint column integrator updates all carrier and vapor amounts.
The fixed-carrier equilibrium integrator is a separate, unchanged interface.
case_id is a user-declared label, not a content digest or authenticity claim.
"""
from dataclasses import dataclass

from .gas_transport import GasState
from .open_gas_boundary import GasBoundaryTransfer, OpenGasBoundaryRate, open_gas_boundary_rate
from .source_wet_column import ColumnFaceRate, ColumnStepLedger, SourceColumnRates, SourceWetColumn


@dataclass(frozen=True, kw_only=True)
class OpenGasColumnRates(SourceColumnRates):
    closed_rates: SourceColumnRates
    boundary: OpenGasBoundaryRate


@dataclass(frozen=True, kw_only=True)
class OpenGasColumnLedger(ColumnStepLedger):
    boundary: OpenGasBoundaryRate
    midpoint_rates: OpenGasColumnRates
    predictor_rates: OpenGasColumnRates
    predictor_faces: tuple
    predictor_phase_water_mol: tuple


@dataclass(frozen=True)
class OpenGasColumn:
    base: SourceWetColumn
    reservoir: GasState
    transfer: GasBoundaryTransfer
    case_id: str
    source_ids: tuple[str, ...]

    @property
    def storages(self): return self.base.storages

    @property
    def interface_modes(self): return self.base.interface_modes

    @property
    def gas_ids(self): return self.base.gas_ids

    @property
    def cell_count(self): return self.base.cell_count

    @property
    def model_identity(self): return self.case_id

    def evaluate(self, states):
        closed = self.base.evaluate(states)
        phases = self.storages[-1].fluid_template.gas_phases
        boundary = open_gas_boundary_rate(
            closed.gas_states[-1], self.reservoir, self.transfer,
            lambda key, temperature: phases[key]._curve.enthalpy_j_mol(temperature),
        )
        face = ColumnFaceRate(
            self.cell_count, self.cell_count-1, None,
            tuple(boundary.exchange.net_mol_s[key] for key in self.gas_ids),
            boundary.energy_out_w, boundary.conduction_out_w,
            tuple(boundary.diffusive_enthalpy_out_w[key] for key in self.gas_ids),
            tuple(boundary.advective_enthalpy_out_w[key] for key in self.gas_ids), boundary,
        )
        return OpenGasColumnRates(
            cells=closed.cells, gas_states=closed.gas_states,
            faces=(*closed.faces[:-1], face), model_identity=self.case_id,
            source_ids=tuple(sorted(set(closed.source_ids+self.source_ids))),
            closed_rates=closed, boundary=boundary,
        )

    def step_ledger(self, duration, faces, phase, error, predictor_error, midpoint, middle, *,
                    predictor_rates, predictor_faces, predictor_phase):
        return OpenGasColumnLedger(
            duration, faces, phase, error, predictor_error, midpoint,
            boundary=middle.boundary, midpoint_rates=middle, predictor_rates=predictor_rates,
            predictor_faces=predictor_faces, predictor_phase_water_mol=predictor_phase,
        )

    def provenance(self):
        return {
            'schema': 'open_gas_column_v1', 'case_id': self.case_id,
            'identity_kind': 'declared_label_not_content_digest',
            'base': self.base.provenance(), 'transfer': self.transfer,
            'reservoir': self.reservoir, 'source_ids': self.source_ids,
            'sign': 'positive outward; subtract each species and energy once',
            'caloric_reference': 'same outer-cell gas phase curves for both directions',
            'material_qualified': False, 'training_eligible': False,
        }
