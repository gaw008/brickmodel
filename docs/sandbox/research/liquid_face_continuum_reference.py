"""Independent isothermal compressible Darcy continuum with source-gated water."""
from functools import lru_cache
import hashlib
import json
from pathlib import Path
import time

import numpy as np
from scipy.optimize import brentq
from sludge_sandbox.water_properties import load_water_properties

ROOT=Path(__file__).resolve().parents[3]


def main():
    started=time.monotonic()
    water=load_water_properties(ROOT/'data/sandbox/water')
    calls=0
    @lru_cache(maxsize=8192)
    def state(p):
        nonlocal calls
        if time.monotonic()-started>120:
            raise RuntimeError('reference_time_budget_exceeded')
        calls+=1
        return water.state_tp(300.,float(p),phase='liquid')
    low,high=1e6,50e6
    grids={n:np.polynomial.legendre.leggauss(n) for n in (16,32)}
    def integral(a,b,order=16):
        if a==b:return 0.
        x,w=grids[order]
        p=(b+a)/2+(b-a)/2*x
        return (b-a)/2*sum(float(weight)*state(float(pressure)).density_kg_m3/water.reference.molar_mass_kg_mol
            for pressure,weight in zip(p,w))
    total16,total32=integral(low,high),integral(low,high,32)
    quadrature_difference=abs(total16-total32)/abs(total32)
    if quadrature_difference>1e-11:
        raise RuntimeError('independent_quadrature_check_failed')
    points={}
    for j in range(33):
        fraction=j/32
        pressure=(high if j==0 else low if j==32 else
            brentq(lambda p:integral(p,high)-fraction*total32,low,high,xtol=1e-4,rtol=1e-13))
        s=state(pressure)
        points[str(j)]=dict(fraction=fraction,pressure_pa=pressure,
            molar_volume_m3_mol=s.molar_mass_kg_mol/s.density_kg_m3,enthalpy_j_mol=s.enthalpy_j_mol)
    output=dict(classification='manufactured_mobility_pure_water_continuum_reference_not_material_validation',
        candidate_run=False,temperature_k=300.,length_m=.1,area_m2=.01,mobility_m2_pa_s=1e-14,
        exact_molar_flow_mol_s=.01*1e-14/.1*total32,
        quadrature_relative_difference=quadrature_difference,points=points,
        water_source_asset_sha256=dict(water.source_asset_sha256),water_calls=calls,
        elapsed_seconds=time.monotonic()-started,
        hashes={str(p.relative_to(ROOT)):hashlib.sha256(p.read_bytes()).hexdigest() for p in
            (Path(__file__),ROOT/'src/sludge_sandbox/water_properties.py',ROOT/'data/sandbox/transport/moose-governing-equations.md')})
    Path(__file__).with_suffix('.json').write_text(json.dumps(output,indent=2,allow_nan=False)+'\n')
    print(json.dumps({k:v for k,v in output.items() if k not in ('points','water_source_asset_sha256','hashes')},indent=2))


if __name__=='__main__':main()
