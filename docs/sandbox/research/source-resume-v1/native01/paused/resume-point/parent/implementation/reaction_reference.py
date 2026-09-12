"""Exact nominal mass-basis reaction-reference algebra; no material qualification.

B[:,j] is kg component change per kg of the explicitly declared reaction extent.
q[j] is product-minus-reactant reference enthalpy in J per kg extent.
Exact arithmetic certifies consistency of supplied nominal numbers only.
"""
from dataclasses import dataclass
from fractions import Fraction

F=Fraction

class ReactionReferenceError(ValueError):pass

def require(ok,message):
    if not ok:raise ReactionReferenceError(message)

def rational(x):
    require(type(x) in (int,F),'exact_rational_required')
    return F(x)

def text(x):require(type(x) is str and bool(x.strip()),'explicit_text_required')

def ids(x):
    require(type(x) is tuple and bool(x),'source_ids_required')
    for value in x:text(value)
    require(len(set(x))==len(x),'duplicate_source_ids')

def vector(x,n=None):
    require(type(x) is tuple and (n is None or len(x)==n),'exact_vector_shape')
    return tuple(rational(v) for v in x)

@dataclass(frozen=True)
class Component:
    component_id:str
    phase:str
    element_mass_fractions:tuple
    source_ids:tuple
    def __post_init__(self):
        text(self.component_id);text(self.phase);ids(self.source_ids)
        row=vector(self.element_mass_fractions)
        require(bool(row) and all(v>=0 for v in row) and sum(row)==1,'complete_element_mass_composition_required')
        object.__setattr__(self,'element_mass_fractions',row)

@dataclass(frozen=True)
class Reaction:
    reaction_id:str
    mass_change_kg_per_kg_extent:tuple
    enthalpy_j_per_kg_extent:F|None
    extent_basis:str
    source_ids:tuple
    def __post_init__(self):
        text(self.reaction_id);text(self.extent_basis);ids(self.source_ids)
        row=vector(self.mass_change_kg_per_kg_extent)
        require(any(v<0 for v in row) and any(v>0 for v in row),'reactants_and_products_required')
        object.__setattr__(self,'mass_change_kg_per_kg_extent',row)
        if self.enthalpy_j_per_kg_extent is not None:
            object.__setattr__(self,'enthalpy_j_per_kg_extent',rational(self.enthalpy_j_per_kg_extent))

@dataclass(frozen=True)
class Anchor:
    component_id:str
    h0_j_kg:F
    reference_convention:str
    reference_temperature_k:F
    reference_pressure_pa:F
    phase:str
    source_ids:tuple
    def __post_init__(self):
        text(self.component_id);text(self.reference_convention);text(self.phase);ids(self.source_ids)
        for field in ('reference_temperature_k','reference_pressure_pa'):
            value=rational(getattr(self,field));require(value>0,'positive_anchor_reference_state');object.__setattr__(self,field,value)
        object.__setattr__(self,'h0_j_kg',rational(self.h0_j_kg))


def rref_solve(rows,values,n):
    """Return a particular coordinate and exact nullspace; never infer data."""
    a=[list(vector(tuple(row),n)) + [rational(value)] for row,value in zip(rows,values)]
    require(len(rows)==len(values),'linear_system_shape')
    pivots=[];r=0
    for col in range(n):
        selected=next((i for i in range(r,len(a)) if a[i][col]),None)
        if selected is None:continue
        a[r],a[selected]=a[selected],a[r];d=a[r][col];a[r]=[x/d for x in a[r]]
        for i in range(len(a)):
            if i!=r:
                d=a[i][col];a[i]=[x-d*y for x,y in zip(a[i],a[r])]
        pivots.append(col);r+=1
        if r==len(a):break
    require(not any(not any(row[:n]) and row[n] for row in a),'inconsistent_linear_constraints')
    particular=[F()]*n
    for i,col in enumerate(pivots):particular[col]=a[i][n]
    nullspace=[]
    for col in range(n):
        if col in pivots:continue
        v=[F()]*n;v[col]=F(1)
        for i,pivot in enumerate(pivots):v[pivot]=-a[i][col]
        nullspace.append(tuple(v))
    return tuple(particular),tuple(nullspace),tuple(pivots)


def dot(a,b):return sum((x*y for x,y in zip(a,b)),F())

@dataclass(frozen=True)
class ReferenceSolution:
    component_ids:tuple
    particular_h0_j_kg:tuple
    nullspace_h0_j_kg:tuple
    pivots:tuple
    reaction_cycle_basis:tuple
    known_reaction_ids:tuple
    source_ids:tuple
    network:'ReactionReferenceNetwork'
    coordinate_convention:str='free_coordinates_zero_for_representation_only'
    qualification:str='exact_nominal_constraint_solution_not_measured_component_enthalpies'
    material_qualified:bool=False
    def identified_value(self,coefficients):
        row=vector(coefficients,len(self.component_ids))
        require(all(dot(row,g)==0 for g in self.nullspace_h0_j_kg),'unknown_required_output')
        return dot(row,self.particular_h0_j_kg)
    def coordinates(self,free_parameters):
        parameters=vector(free_parameters,len(self.nullspace_h0_j_kg))
        return tuple(h+sum((c*g[i] for c,g in zip(parameters,self.nullspace_h0_j_kg)),F()) for i,h in enumerate(self.particular_h0_j_kg))

@dataclass(frozen=True)
class ReactionReferenceNetwork:
    elements:tuple
    components:tuple
    reactions:tuple
    reference_temperature_k:F
    reference_pressure_pa:F
    inventory_basis:str
    reference_convention:str
    input_classification:str
    uncertainty_statement:str
    source_ids:tuple
    anchors:tuple=()
    def __post_init__(self):
        require(type(self.elements) is tuple and bool(self.elements),'elements_required')
        for e in self.elements:text(e)
        require(len(set(self.elements))==len(self.elements),'duplicate_elements')
        for field,cls in ((self.components,Component),(self.reactions,Reaction),(self.anchors,Anchor)):
            require(type(field) is tuple and all(type(x) is cls for x in field),'typed_network_entries')
        require(bool(self.components) and bool(self.reactions),'nonempty_network')
        ci=tuple(c.component_id for c in self.components);ri=tuple(r.reaction_id for r in self.reactions)
        require(len(set(ci))==len(ci) and len(set(ri))==len(ri),'duplicate_component_or_reaction')
        require(self.inventory_basis=='kg_of_declared_components','mass_inventory_basis_required')
        for value in (self.reference_convention,self.input_classification,self.uncertainty_statement):text(value)
        require(self.input_classification in ('manufactured_test_fixture','externally_sourced_unqualified'),'explicit_input_classification')
        ids(self.source_ids)
        for field in ('reference_temperature_k','reference_pressure_pa'):
            value=rational(getattr(self,field));require(value>0,'positive_reference_state');object.__setattr__(self,field,value)
        require(all(len(c.element_mass_fractions)==len(self.elements) for c in self.components),'element_shape')
        for r in self.reactions:
            b=vector(r.mass_change_kg_per_kg_extent,len(ci))
            require(sum(b)==0,'mass_unbalanced:'+r.reaction_id)
            for k,element in enumerate(self.elements):
                require(sum((b[i]*c.element_mass_fractions[k] for i,c in enumerate(self.components)),F())==0,'element_unbalanced:'+r.reaction_id+':'+element)
        for anchor in self.anchors:
            require(anchor.component_id in ci,'unknown_anchor_component')
            require(anchor.reference_convention==self.reference_convention,'unbridged_anchor_reference')
            require(anchor.reference_temperature_k==self.reference_temperature_k and anchor.reference_pressure_pa==self.reference_pressure_pa,'anchor_reference_state_mismatch')
            require(anchor.phase==self.components[ci.index(anchor.component_id)].phase,'anchor_phase_mismatch')
    def solve(self,*,required_outputs=()):
        n=len(self.components);known=tuple(r for r in self.reactions if r.enthalpy_j_per_kg_extent is not None)
        b=[r.mass_change_kg_per_kg_extent for r in known];q=[r.enthalpy_j_per_kg_extent for r in known]
        # Cycles use known reaction columns only. Unknown reaction heats remain
        # unknown unless their mass-change functional is fixed by constraints.
        transposed=[tuple(row[i] for row in b) for i in range(n)]
        _,cycles,_=rref_solve(transposed,[F()]*n,len(known))
        require(all(dot(c,q)==0 for c in cycles),'inconsistent_reaction_cycle')
        rows=list(b);values=list(q);ci=tuple(c.component_id for c in self.components)
        for anchor in self.anchors:
            rows.append(tuple(F(i==ci.index(anchor.component_id)) for i in range(n)));values.append(anchor.h0_j_kg)
        try:particular,nullspace,pivots=rref_solve(rows,values,n)
        except ReactionReferenceError as exc:raise ReactionReferenceError('inconsistent_anchor_constraints') from exc
        sources=tuple(sorted(set(self.source_ids).union(*(set(x.source_ids) for x in self.components+self.reactions+self.anchors))))
        solution=ReferenceSolution(ci,particular,nullspace,pivots,cycles,tuple(r.reaction_id for r in known),sources,self)
        require(type(required_outputs) is tuple,'required_outputs_tuple')
        for row in required_outputs:solution.identified_value(row)
        return solution
