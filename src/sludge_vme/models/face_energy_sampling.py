"""Root-configured sampling of existing finite-gas summary arrays.

No state reconstruction, rates/RHS calls, quadrature, or writes while sampling.
Native face capture is active only around a scheduled existing summary rate.
"""
from __future__ import annotations

import gzip
import json
from pathlib import Path


BUNDLE_FIELD = '_face_energy_sample_bundle'


def configured_sampler(model):
    contract = model.config['face_energy_sampling']
    mode = model.p(contract['enabled_parameter'], '1')
    if mode == 0:
        return None
    if mode != 1:
        raise ValueError('face-energy sampling explicitly selects 0 or 1')
    return FaceEnergySamples(model, contract)


class FaceEnergySamples:
    def __init__(self, model, contract):
        selection = contract['selection_by_cell_count'][str(model.n)]
        self.times = tuple(model.p(contract['times_parameter'], 's'))
        self.faces = model.p(selection['faces_parameter'], '1')
        self.cells = model.p(selection['cells_parameter'], '1')
        self.limit_bytes = int(model.p(contract['byte_limit_parameter'], 'byte'))
        self.filename = contract['output_filename']
        self.species = contract['gas_species']
        self.gas_columns = {name: model.ng.index(name) for name in self.species}
        self.n = model.n
        self.reference_faces = model.initial_partition['faces_m']
        self.condensed_count = len(model.ns)
        self.P, self.R, self.v = model.P, model.R, model.v
        self.scale = model.escale
        self.encoded_records = []
        self.first = None
        header = {
            'schema': 'passive_saved_face_energy_samples_v1',
            'requested_times_s': self.times,
            'selected_face_indices': self.faces,
            'selected_cell_indices': self.cells,
            'selected_species': self.species,
            'reference_geometry': {
                'cells': model.n, 'area_m2': model.area,
                'reference_faces_m': model.initial_partition['faces_m'].tolist(),
                'saved_reference_bulk_m3': model.initial_partition['initial_bulk_m3'].tolist()},
            'orientation': 'Faces 0..N point toward exterior; cell gain is F_left-F_right. Native gas face k is array[k-1]; symmetry face 0 is zero.',
            'units': {'gas_species_faces': 'mol/s', 'energy_faces': 'W', 'stored_energy_and_ledgers': 'J', 'bulk': 'm3', 'time': 's'},
            'energy_scope': 'Unmodified summary state_thermo condensed+pore gas, pore surface, water binding, additional_storage exactly once; no added reaction or phase heat.',
            'thermal_face_scope': 'Native existing internal=conductance*diff(T), outward=-internal; outer outward=-qext. No cell-divergence reconstruction.',
            'gas_energy_scope': 'Existing transport hg supplies molecular/Darcy decompositions; shared energy remains the original energy_flux, counted once.',
            'work_scope': 'Same constant exterior P: -P*(bulk-current minus bulk-first saved sample), not pore-pressure work.',
            'max_uncompressed_bytes': self.limit_bytes,
        }
        self.prefix = (json.dumps(header, ensure_ascii=False, separators=(',', ':'), allow_nan=False)[:-1] + ',"records":[').encode()
        self.size = len(self.prefix) + len(b']}\n')

    def require_existing_times(self, summary_times):
        if not self.times or len(set(self.times)) != len(self.times) or any(t not in summary_times for t in self.times):
            raise ValueError('fixed sample times must be distinct existing summary times')

    def append(self, *, time_s, f, T, ns, h, bulk, surface, extra_u, r,
               published_row, native_faces, native_complete_energy_j):
        components = {
            'condensed': (ns*(h[:, :self.condensed_count]-self.P*self.v)).sum(axis=1),
            'pore_gas': (r['gas']*(h[:, self.condensed_count:]-self.R*T[:, None])).sum(axis=1),
            'pore_surface': surface,
            'water_binding': r['water_binding']['energy'],
            'additional_storage': extra_u,
        }
        complete = sum(components.values())
        selected = lambda values: [float(values[i]) for i in self.cells]
        record = {
            'time_s': float(time_s), 'exterior_pressure_pa': float(self.P),
            'complete_energy_j': selected(complete),
            'energy_components_j': {name: selected(values) for name, values in components.items()},
            'bulk_m3': selected(bulk),
            'cumulative_heat_j': selected(f[7]*self.scale),
            'cumulative_flow_j': selected(f[8]*self.scale),
            'gas_inventory_mol': {name: selected(r['gas'][:, column]) for name, column in self.gas_columns.items()},
            'reaction_extent_mol': {name: selected(values) for name, values in published_row['reaction_extent_mol'].items()},
            'native_global_complete_energy_minus_component_sum_j': float(native_complete_energy_j-complete.sum()),
            'cell_complete_energy_expected_rate_w': selected(r['heat']+r['flow']-self.P*r['db']),
            'faces': [],
        }
        if 'direct_carbonation' in record['reaction_extent_mol']:
            record['direct_extent_mol'] = record['reaction_extent_mol']['direct_carbonation']
            record['direct_rate_mol_s'] = selected(published_row['direct_carbonation_rate_mol_s'])
        for face in self.faces:
            values = {}
            for species, column in self.gas_columns.items():
                for suffix, key in (('molecular', 'molecular_flux'), ('darcy', 'darcy_flux'), ('total', 'gas_flux')):
                    values[species+'_'+suffix+'_mol_s'] = float(r[key][face-1, column]) if face else 0.0
            values.update({
                'gas_shared_energy_w': float(r['energy_flux'][face-1]) if face else 0.0,
                'gas_molecular_energy_w': float(native_faces['gas_molecular_energy_w'][face-1]) if face else 0.0,
                'gas_darcy_energy_w': float(native_faces['gas_darcy_energy_w'][face-1]) if face else 0.0,
                'liquid_water_energy_w': float(r['water_energy_flux'][face-1]) if 0 < face < self.n else 0.0,
                'thermal_energy_native_w': float(native_faces['thermal_energy_native_w'][face]),
            })
            record['faces'].append({
                'face_index': face,
                'reference_position_m': float(self.reference_faces[face]),
                'left_cell': face-1 if face else None,
                'right_cell': face if face < self.n else None,
                'outward_rates': values,
                'left_cell_gain_rates': {name: -value for name, value in values.items()} if face else None,
                'right_cell_gain_rates': values.copy() if face < self.n else None,
            })
        if self.first is None:
            self.first = record
        first = self.first
        work = [-self.P*(v-v0) for v, v0 in zip(record['bulk_m3'], first['bulk_m3'])]
        record['local_exterior_pressure_work_since_first_sample_j'] = work
        record['local_complete_energy_ledger_residual_since_first_sample_j'] = [
            u-u0-(q-q0)-(flow-flow0)-w for u,u0,q,q0,flow,flow0,w in zip(
                record['complete_energy_j'], first['complete_energy_j'], record['cumulative_heat_j'],
                first['cumulative_heat_j'], record['cumulative_flow_j'], first['cumulative_flow_j'], work)]
        data = json.dumps(record, ensure_ascii=False, separators=(',', ':'), allow_nan=False).encode()
        new_size = self.size+len(data)+(1 if self.encoded_records else 0)
        if new_size > self.limit_bytes:
            raise ValueError('configured face-energy summary byte limit exceeded; no truncated export')
        self.encoded_records.append(data)
        self.size = new_size

    def bundle(self):
        if len(self.encoded_records) != len(self.times):
            raise ValueError('not all configured summary times were sampled')
        return {'output_filename': self.filename, 'json_utf8': self.prefix+b','.join(self.encoded_records)+b']}\n',
                'records': len(self.encoded_records)}


def write_sample_bundle(out, bundle):
    """Called once by the artifact writer after integration and summary."""
    payload = bundle['json_utf8']
    data = gzip.compress(payload, mtime=0)
    path = Path(out)/bundle['output_filename']
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open('xb') as stream:
        stream.write(data)
    return {'path': bundle['output_filename'], 'records': bundle['records'],
            'uncompressed_bytes': len(payload), 'compressed_bytes': len(data)}
