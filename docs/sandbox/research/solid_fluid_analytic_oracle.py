"""Generate solver-independent manufactured solid/gas reference values."""
from decimal import Decimal, localcontext
from hashlib import sha256
import json
from pathlib import Path


def d(value):
    return Decimal.from_float(float(value))


def reference(temperature, solid_amounts):
    t = d(temperature) if not isinstance(temperature, Decimal) else temperature
    r, bulk, p0 = d(8.31446261815324), d(1e-4), d(1e5)
    ns = tuple(map(d, solid_amounts))
    ng = tuple(map(d, (.001,.002)))
    vs = tuple(map(d, (1e-5,2e-5)))
    cs, cg = tuple(map(d,(30.,50.))), tuple(map(d,(30.,40.)))
    hs, hg = tuple(map(d,(-100000.,-200000.))), tuple(map(d,(-1000.,-2000.)))
    solid_volume = sum(n*v for n,v in zip(ns,vs))
    gas_volume = bulk-solid_volume
    pressure = sum(ng)*r*t/gas_volume
    energy = sum(n*(c*t+h-p0*v) for n,c,h,v in zip(ns,cs,hs,vs))
    energy += sum(n*((c-r)*t+h) for n,c,h in zip(ng,cg,hg))
    capacity = sum(n*c for n,c in zip(ns,cs))+sum(n*(c-r) for n,c in zip(ng,cg))
    return dict(temperature_k=t,solid_volume_m3=solid_volume,gas_volume_m3=gas_volume,
                pressure_pa=pressure,internal_energy_j=energy,
                enthalpy_j=energy+pressure*bulk,heat_capacity_j_k=capacity)


def main():
    with localcontext() as context:
        context.prec = 60
        cases = {"initial_300k": reference(300.,(2.,1.)),
                 "higher_350k": reference(350.,(2.,1.)),
                 "half_solid_300k": reference(300.,(1.,.5))}
        final_t = d(300.)+d(250.)/cases["initial_300k"]["heat_capacity_j_k"]
        cases["after_250j"] = reference(final_t,(2.,1.))
        output = dict(classification="manufactured_test_fixture",runtime_comparison_performed=False,
                      cases={k:{name:str(value) for name,value in row.items()} for k,row in cases.items()},
                      script_sha256=sha256(Path(__file__).read_bytes()).hexdigest())
    path=Path(__file__).with_suffix('.json')
    path.write_text(json.dumps(output,indent=2)+"\n")
    print(json.dumps(output,indent=2))


if __name__ == '__main__':
    main()
