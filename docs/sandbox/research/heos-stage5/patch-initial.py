from pathlib import Path
p=Path('/private/tmp/brick-heos-stage5/sludge_sandbox')
def edit(name,old,new):
    f=p/name;s=f.read_text();assert old in s,(name,old);f.write_text(s.replace(old,new))
edit('water_properties.py','from ._water_python_backend import PythonIAPWS95Calls','from ._water_python_backend import PythonIAPWS95Calls\nfrom .water_implementation import WaterImplementation')
edit('water_properties.py','    method_id: str\n\n    @property','    method_id: str\n    implementation: WaterImplementation | None = field(default=None,kw_only=True)\n\n    @property')
edit('water_properties.py','        return self.reference.source_ids\n','        return self.reference.source_ids + (() if self.implementation is None else self.implementation.source_ids)\n')
edit('water_properties.py','    def _solve(self, **inputs):','    @property\n    def implementation(self):return None\n\n    @property\n    def source_ids(self):return self.reference.source_ids\n\n    def _solve(self, **inputs):')
edit('water_properties.py','def load_water_properties(source_directory) -> WaterProperties:\n    return WaterProperties(source_directory)', '''def is_water_provider(value):
    if type(value) is WaterProperties:return True
    from .water_heos import HEOSWaterProperties
    return type(value) is HEOSWaterProperties


def load_water_properties(source_directory, *, backend='python', backend_manifest=None):
    if backend=='python':
        if backend_manifest is not None:raise WaterSourceError('python_backend_does_not_take_heos_manifest')
        return WaterProperties(source_directory)
    if backend=='heos' and backend_manifest is not None:
        from .water_heos import HEOSWaterProperties
        return HEOSWaterProperties(source_directory,backend_manifest)
    raise WaterSourceError('explicit_supported_backend_and_manifest_required')''')
for name in ['phase_storage.py','rigid_water_gas.py','water_chemical_potential.py','deforming_solid_storage.py']:
    f=p/name;s=f.read_text();s='from sludge_sandbox.water_properties import is_water_provider\n'+s
    # Preserve module docstring/future import requirements by put import after future if present.
    if 'from __future__ import annotations' in s:
        s=s.removeprefix('from sludge_sandbox.water_properties import is_water_provider\n').replace('from __future__ import annotations','from __future__ import annotations\nfrom sludge_sandbox.water_properties import is_water_provider')
    s=s.replace('type(self.water) is not WaterProperties','not is_water_provider(self.water)').replace('type(x) is WaterProperties','is_water_provider(x)')
    f.write_text(s)
edit('ideal_water_vapor.py','def __init__(self, source_directory):','def __init__(self, source_directory, *, backend="python", backend_manifest=None):')
edit('ideal_water_vapor.py','water = load_water_properties(source_directory)','water = load_water_properties(source_directory,backend=backend,backend_manifest=backend_manifest)')
edit('ideal_water_vapor.py','return self.reference.source_ids + self.constant_source_ids','return self._water.source_ids + self.constant_source_ids')
edit('ideal_water_vapor.py',"or state.method_id != 'derived_iapws95_ideal_helmholtz'", "or state.implementation != self._water.implementation\n                or state.method_id != 'derived_iapws95_ideal_helmholtz'")
edit('joined_water_vapor.py','*,low_enthalpy_error_j_mol,numerical_error_source_ids):','*,low_enthalpy_error_j_mol,numerical_error_source_ids,backend="python",backend_manifest=None):')
edit('joined_water_vapor.py','IdealWaterVapor(water_source_directory)','IdealWaterVapor(water_source_directory,backend=backend,backend_manifest=backend_manifest)')
edit('water_chemical_potential.py','type(state) is not WaterState or state.reference is not self.reference','type(state) is not WaterState or state.reference is not self.reference\n                or state.implementation != self.water.implementation')
edit('phase_storage.py',"_REFERENCE,r.source_ids,'derived_from_evidence'","_REFERENCE,self.water.source_ids,'derived_from_evidence'")
for name in ['rigid_water_gas.py','solid_fluid_storage.py','rigid_fluid_heat.py']:
    f=p/name;s=f.read_text().replace('water.reference.source_ids','water.source_ids');f.write_text(s)
edit('solid_fluid_heat.py',"provider_id='iapws95_real_fluid_helmholtz',provider_version='1.5.5',", "provider_id=('iapws95_real_fluid_helmholtz' if water.implementation is None else water.implementation.provider_id),\n                    provider_version=('1.5.5' if water.implementation is None else water.implementation.provider_version),")
