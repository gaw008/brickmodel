"""Independent Decimal first-order solid-to-gas inventory/energy/volume model."""
from decimal import Decimal,localcontext
import json
from pathlib import Path


def d(x):return Decimal.from_float(float(x))


def reference(time_s):
    if not 0<=time_s<=2:raise ValueError('outside_reference_time')
    with localcontext() as ctx:
        ctx.prec=60
        r=d(8.31446261815324)
        fs=d(-50.*298.15/1000.)
        fx=d(-1.-30.*298.15/1000.)
        fn=d(-30.*298.15/1000.)
        vs=d(1e-5)
        cs=d(50);cg=d(30)-r
        us0=cs*d(300)+1000*fs-d(1e5)*vs
        un0=cg*d(300)+1000*fn
        u0=d(.01)*us0+d(.01)*un0
        ns=d(.01)*(-d(time_s)).exp()
        nx=d(.01)-ns
        nn=d(.01)
        capacity=ns*cs+(nx+nn)*cg
        offset=ns*(1000*fs-d(1e5)*vs)+nx*1000*fx+nn*1000*fn
        temperature=(u0-offset)/capacity
        volume=d(1e-4)-ns*vs
        pressure=(nx+nn)*r*temperature/volume
        return {k:str(v) for k,v in dict(time_s=d(time_s),solid_mol=ns,product_gas_mol=nx,
            carrier_mol=nn,temperature_k=temperature,pressure_pa=pressure,gas_volume_m3=volume,
            internal_energy_j=u0,capacity_j_k=capacity,solid_F_kj_mol=fs,
            product_F_kj_mol=fx,carrier_F_kj_mol=fn).items()}


if __name__=='__main__':
    output=dict(classification='manufactured_test_fixture_not_real_carbon_or_sludge',candidate_run=False,
        checkpoints=[reference(t) for t in (0,.25,.5,1,2)])
    Path(__file__).with_suffix('.json').write_text(json.dumps(output,indent=2,allow_nan=False)+'\n')
    print(json.dumps(output,indent=2))
