"""Independent Decimal solution of the preregistered manufactured ramp problem."""
from decimal import Decimal, localcontext
from pathlib import Path
import json


def d(value):
    return Decimal.from_float(float(value))


def reference(time_s):
    if not 0 <= time_s <= 40:
        raise ValueError('time_outside_reference_domain')
    with localcontext() as ctx:
        ctx.prec = 60
        capacity = d(2)*d(50)+d(.01)*(d(30)-d(8.31446261815324))
        conductance = d(.01)/(d(.01)/(d(2)*d(10))+1/d(100000))
        decay = conductance/capacity
        temperature = d(300)
        bath = d(300)
        for start,end,left,right in ((0,10,300,305),(10,20,305,305),(20,40,305,295)):
            if time_s <= start:
                break
            duration = min(d(time_s),d(end))-d(start)
            slope = (d(right)-d(left))/(d(end)-d(start))
            bath = d(left)+slope*duration
            temperature = bath-slope/decay+(temperature-d(left)+slope/decay)*(-decay*duration).exp()
            if time_s <= end:
                break
        surface = ((d(2)*d(10)/d(.01))*temperature+d(100000)*bath)/(d(2)*d(10)/d(.01)+d(100000))
        return {k:str(v) for k,v in dict(time_s=d(time_s),temperature_k=temperature,
            bath_temperature_k=bath,surface_temperature_k=surface,net_heat_j=capacity*(temperature-d(300)),
            capacity_j_k=capacity,conductance_w_k=conductance).items()}


if __name__ == '__main__':
    output=dict(classification='manufactured_test_fixture',candidate_run=False,
                method='60_digit_decimal_piecewise_linear_forced_constant_capacity_analytic_solution',
                checkpoints=[reference(t) for t in (0,5,10,15,20,30,40)])
    target=Path(__file__).with_suffix('.json')
    target.write_text(json.dumps(output,indent=2,allow_nan=False)+'\n')
    print(target)
