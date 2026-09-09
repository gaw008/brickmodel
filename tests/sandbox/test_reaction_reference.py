"""All numbers are manufactured exact algebra examples, not material data."""
from fractions import Fraction as F
from dataclasses import replace
import pytest
from sludge_sandbox.reaction_reference import Component,Reaction,Anchor,ReactionReferenceNetwork,ReactionReferenceError

S=('manufactured:algebra-v1',)

def network(reactions=None,anchors=()):
    components=tuple(Component(c,'manufactured_solid',(F(1),),S) for c in ('A','B','C'))
    if reactions is None:reactions=(Reaction('AB',(-1,1,0),-10,'kg A consumed',S),Reaction('BC',(0,-1,1),-20,'kg B consumed',S))
    return ReactionReferenceNetwork(('X',),components,reactions,F(300),F(100000),'kg_of_declared_components','declared-common-reference','manufactured_test_fixture','Exact manufactured inputs; no measurement uncertainty asserted',S,anchors)

def test_reference_solution_and_gauge_invariance():
    n=network();s=n.solve()
    assert len(s.nullspace_h0_j_kg)==1 and s.material_qualified is False
    assert s.identified_value((-1,1,0))==-10
    assert s.identified_value((0,-1,1))==-20
    h=s.coordinates((F(123456,7),))
    assert h[1]-h[0]==-10 and h[2]-h[1]==-20
    with pytest.raises(ReactionReferenceError,match='unknown_required_output'):s.identified_value((1,0,0))
    assert s.coordinate_convention=='free_coordinates_zero_for_representation_only'

def test_anchor_and_reaction_energy_storage_change():
    s=network(anchors=(Anchor('A',100,'declared-common-reference',F(300),F(100000),'manufactured_solid',S),)).solve(required_outputs=((0,0,1),))
    assert s.particular_h0_j_kg==(100,90,70) and not s.nullspace_h0_j_kg
    xi=F(2,7);before=(F(1),F(0),F(0));after=(1-xi,xi,F(0))
    change=sum((a-b)*h for a,b,h in zip(after,before,s.particular_h0_j_kg))
    assert change==-10*xi

def test_cycle_consistency_and_inconsistency():
    n=network();ac=Reaction('AC',(-1,0,1),-30,'kg A consumed',S)
    s=replace(n,reactions=n.reactions+(ac,)).solve()
    assert len(s.reaction_cycle_basis)==1
    with pytest.raises(ReactionReferenceError,match='inconsistent_reaction_cycle'):
        replace(n,reactions=n.reactions+(replace(ac,enthalpy_j_per_kg_extent=-31),)).solve()

def test_inconsistent_anchor_and_unbridged_reference():
    a=Anchor('A',0,'declared-common-reference',F(300),F(100000),'manufactured_solid',S);b=Anchor('B',0,'declared-common-reference',F(300),F(100000),'manufactured_solid',S)
    with pytest.raises(ReactionReferenceError,match='inconsistent_anchor_constraints'):network(anchors=(a,b)).solve()
    with pytest.raises(ReactionReferenceError,match='unbridged_anchor_reference'):network(anchors=(replace(a,reference_convention='unrelated-reference'),))

def test_mass_and_elements_are_separate_exact_gates():
    n=network()
    with pytest.raises(ReactionReferenceError,match='mass_unbalanced'):
        replace(n,reactions=(Reaction('missing',(-1,F(9,10),0),0,'kg A consumed',S),))
    components=(Component('A','solid',(1,0),S),Component('B','gas',(0,1),S),Component('C','solid',(F(1,2),F(1,2)),S))
    with pytest.raises(ReactionReferenceError,match='element_unbalanced'):replace(n,elements=('X','Y'),components=components)
    r=Reaction('formation',(-1,-1,2),-40,'kg A consumed with one kg B',S)
    m=replace(n,elements=('X','Y'),components=components,reactions=(r,));s=m.solve()
    assert len(s.nullspace_h0_j_kg)==2 and s.identified_value(r.mass_change_kg_per_kg_extent)==-40
    # Independent conserved-element gauge: shift each h by lambda_X*wX+lambda_Y*wY.
    h=s.particular_h0_j_kg;g=(F(3),F(7),F(5))
    assert sum(b*(x+y) for b,x,y in zip(r.mass_change_kg_per_kg_extent,h,g))==-40

def test_unknown_needed_reaction_not_filled_with_zero():
    n=network();n=replace(n,reactions=(n.reactions[0],replace(n.reactions[1],enthalpy_j_per_kg_extent=None)))
    with pytest.raises(ReactionReferenceError,match='unknown_required_output'):n.solve(required_outputs=((0,-1,1),))
    assert n.solve().known_reaction_ids==('AB',)
    # An unknown duplicate direction is identifiable through an existing heat.
    duplicate=Reaction('AB_unknown',(-2,2,0),None,'kg half-of-A basis explicitly doubled',S)
    s=replace(n,reactions=(n.reactions[0],duplicate)).solve(required_outputs=((-2,2,0),))
    assert s.identified_value((-2,2,0))==-20

@pytest.mark.parametrize('bad',[True,1.,'1',float('nan')])
def test_no_implicit_numeric_conversion(bad):
    with pytest.raises(ReactionReferenceError):Reaction('bad',(-1,1,0),bad,'kg A consumed',S)

def test_incomplete_composition_and_missing_sources_rejected():
    with pytest.raises(ReactionReferenceError):Component('A','solid',(F(9,10),),S)
    with pytest.raises(ReactionReferenceError):Component('A','solid',(1,),())
    with pytest.raises(ReactionReferenceError):replace(network(),reference_temperature_k=0)


@pytest.mark.parametrize('change',[{'reference_temperature_k':F(301)},{'reference_pressure_pa':F(200000)},{'phase':'gas'}])
def test_anchor_declared_state_cannot_be_silently_bridged(change):
    a=Anchor('A',100,'declared-common-reference',F(300),F(100000),'manufactured_solid',S)
    with pytest.raises(ReactionReferenceError,match='anchor_.*mismatch'):
        network(anchors=(replace(a,**change),))


def test_solution_retains_exact_immutable_network_and_unknown_provenance():
    from dataclasses import FrozenInstanceError
    original=network()
    unknown=replace(original.reactions[1],enthalpy_j_per_kg_extent=None,source_ids=('manufactured:explicit-unknown-heat',))
    original=replace(original,reactions=(original.reactions[0],unknown),uncertainty_statement='Unknown measurement uncertainty; exact manufactured nominal arithmetic only')
    solution=original.solve()
    assert solution.network is original
    assert solution.network.reference_temperature_k==F(300)
    assert solution.network.reference_pressure_pa==F(100000)
    assert solution.network.inventory_basis=='kg_of_declared_components'
    assert solution.network.components[0].phase=='manufactured_solid'
    assert solution.network.reactions[1].enthalpy_j_per_kg_extent is None
    assert solution.network.reactions[1].source_ids==('manufactured:explicit-unknown-heat',)
    assert solution.network.uncertainty_statement.startswith('Unknown')
    assert solution.identified_value((-1,1,0))==-10
    assert solution.qualification=='exact_nominal_constraint_solution_not_measured_component_enthalpies'
    with pytest.raises(FrozenInstanceError):solution.network=network()
    with pytest.raises(FrozenInstanceError):solution.network.reference_temperature_k=F(999)
    with pytest.raises(FrozenInstanceError):solution.network.reactions[1].enthalpy_j_per_kg_extent=F()
    with pytest.raises(TypeError):solution.network.reactions[1].source_ids[0]='altered'
    with pytest.raises(ReactionReferenceError,match='unknown_required_output'):solution.identified_value((0,-1,1))

def test_solution_retains_anchor_source_and_declared_reference_state():
    anchor=Anchor('A',100,'declared-common-reference',F(300),F(100000),'manufactured_solid',('manufactured:anchor',))
    original=network(anchors=(anchor,));solution=original.solve()
    assert solution.network is original and solution.network.anchors[0] is anchor
    assert solution.network.anchors[0].source_ids==('manufactured:anchor',)
    assert solution.network.anchors[0].reference_convention==original.reference_convention
