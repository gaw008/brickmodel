"""Clock representation is distinct from inventory arithmetic and storage rounding."""
from dataclasses import replace
from fractions import Fraction
import math
import pytest
from sludge_sandbox.depletion_roundoff import DepletionClockEvidence,DepletionRoundoffError,depletion_writeback,DepletionRoundoffTotals
from sludge_sandbox.integration import ConservedState
from test_depletion_roundoff import policy


def clock_case():
    start=.1; liquid=2.2550840454640983e-7;rate=-.001
    exact=Fraction(start)+Fraction(liquid)/-Fraction(rate)
    end=float(exact)
    if Fraction(end)>exact:end=math.nextafter(end,-math.inf)
    term=float((Fraction(end)-Fraction(start))*Fraction(rate))
    residual=float(Fraction(liquid)+Fraction(term))
    p=policy(correction_absolute_mol=1e-15)
    kwargs=dict(cell_index=0,liquid_index=0,vapor_index=1,panel_liquid_start_mol=liquid,
        panel_liquid_terms_mol=(term,),positive_evaporated_mol=-term,policy=p,totals=DepletionRoundoffTotals(p))
    evidence=DepletionClockEvidence(start,end,(rate,),1e-12)
    return ConservedState([[residual,.1]],[600.]),kwargs,evidence


def test_clock_bound_is_reconstructed_and_storage_rounding_retained():
    state,kw,clock=clock_case()
    with pytest.raises(DepletionRoundoffError,match='local_ulp'):depletion_writeback(state,**kw)
    result,record,total=depletion_writeback(state,**kw,clock_evidence=clock)
    assert result.amounts_mol[0,0]==0 and record.clock_evidence==clock
    exact=Fraction(clock.start_s)+Fraction(kw['panel_liquid_start_mol'])/-Fraction(clock.liquid_rates_mol_s[0])
    assert record.numerical_clock_inventory_residual_mol==abs(Fraction(clock.liquid_rates_mol_s[0]))*(exact-Fraction(clock.end_s))
    assert total.events==1 and record.vapor_storage_roundoff_mol!=0


@pytest.mark.parametrize('change', ['endpoint','rate','budget'])
def test_forged_clock_evidence_cannot_expand_budget(change):
    state,kw,clock=clock_case()
    if change=='endpoint':clock=replace(clock,end_s=math.nextafter(clock.end_s,-math.inf))
    if change=='rate':clock=replace(clock,liquid_rates_mol_s=(-.002,))
    if change=='budget':clock=replace(clock,time_absolute_s=1e-30)
    with pytest.raises(DepletionRoundoffError):depletion_writeback(state,**kw,clock_evidence=clock)
