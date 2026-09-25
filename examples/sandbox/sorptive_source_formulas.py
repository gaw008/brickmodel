"""Review-side source formulas for the conditional sorptive cell.

No production equilibrium or excess provider is imported. Pure liquid uses
direct IAPWS95 (shared EOS backend); source join uses independent quadrature.
"""
import math
from functools import lru_cache

from iapws import IAPWS95
import numpy as np
from scipy.integrate import quad
from scipy.optimize import brentq, root as solve_root


class SorptiveSource:
    def __init__(self, header, settings):
        self.liquid_at = lambda t,p:IAPWS95(T=t,P=p/1e6)
        if 'liquid_cache_entries' in settings:
            self.liquid_at = lru_cache(maxsize=settings['liquid_cache_entries'])(self.liquid_at)
        self.config = header['parameters']
        self.record = header['sorption_source']
        self.facts = header['water_source']['facts']
        self.thermo = header['thermochemistry']
        self.r = self.thermo['gas_constant']['value_j_mol_k']
        self.mass = self.record['water_molar_mass_kg_mol']
        self.pref = self.config['reference_pressure_pa']
        self.offset = self.facts['gas_formation_h_j_mol']-self.water_ideal(self.facts['reference_temperature_k'])[0]
        t0 = self.record['reference_temperature_k']
        wj, wr = self.record['join']['moisture_kg_kg'], self.record['reference_moisture_kg_kg']
        reference_liquid = self.liquid_at(t0,self.record['reference_liquid_pressure_pa'])
        latent = float((self.ideal('H2O',t0)[0]-reference_liquid.h*1000*self.mass-self.offset)/self.mass)
        curves = self.record['source_curves']
        a = np.array([[p['moisture_kg_kg'],p['value']] for p in curves['activity']])
        q = np.array([[p['moisture_kg_kg'],p['value']] for p in curves['heat']])
        m0 = lambda w: self.r/self.mass*t0*float(np.interp(w,a[:,0],np.log(a[:,1])))
        b0 = lambda w: latent-float(np.interp(w,q[:,0],q[:,1]))
        self.m0, self.b0, self.t0, self.wr = m0,b0,t0,wr
        self.activity_nodes, self.heat_nodes, self.settings = a[:,0],q[:,0],settings
        integrate = lambda f, nodes: quad(f,wr,wj,points=nodes[1:-1],
            epsabs=settings['quad_absolute_tolerance'],epsrel=settings['quad_relative_tolerance'],
            limit=settings['quad_maximum_subintervals'])[0]
        hj, gj = integrate(b0,q[:,0]), integrate(m0,a[:,0])
        sj = (hj-gj)/t0
        self.b, self.c = b0(wj),(b0(wj)-m0(wj))/t0
        self.h0, self.s0 = hj-self.b*wj, sj-self.c*wj-self.r/self.mass*wj
        self.wj = wj

    def excess(self,t,w):
        if w <= self.wj:
            h = self.h0+self.b*w
            s = self.s0+(self.c+self.r/self.mass)*w-self.r/self.mass*w*math.log(w/self.wj) if w else self.s0
            mu = self.mass*(self.b-t*self.c)+self.r*t*math.log(w/self.wj) if w else None
            return h,s,mu
        settings = self.settings
        integrate = lambda f,nodes: quad(f,self.wr,w,points=[x for x in nodes if w<x<self.wr],
            epsabs=settings['quad_absolute_tolerance'],epsrel=settings['quad_relative_tolerance'],
            limit=settings['quad_maximum_subintervals'])[0]
        h,g0 = integrate(self.b0,self.heat_nodes),integrate(self.m0,self.activity_nodes)
        s = (h-g0)/self.t0
        mu = self.mass*(self.b0(w)-t*(self.b0(w)-self.m0(w))/self.t0)
        return h,s,mu

    def water_ideal(self,t):
        c,a = self.facts['iapws_constants'],self.facts['ideal_formula_constants']
        tau = c['T_critical_k']/t
        phi = math.log(self.pref/(c['R_specific_j_kg_k']*t*c['rho_critical_kg_m3']))
        phi += a['n1']+a['n2']*tau+a['n3']*math.log(tau)
        derivative = a['n2']*tau+a['n3']
        for n,g in zip(a['n4_to_n8'],a['gamma4_to_gamma8'],strict=True):
            phi += n*math.log1p(-math.exp(-g*tau))
            derivative += n*g*tau/(math.exp(g*tau)-1)
        native_r = c['R_specific_j_kg_k']*self.mass
        return native_r*t*(1+derivative),native_r*(derivative-phi)

    def ideal(self,key,t):
        if key == 'H2O':
            h,s = self.water_ideal(t)
            return h+self.offset,s
        species=next(p for p in self.thermo['species'] if p['species_id']==key)
        segment=next(p for p in species['segments'] if p['temperature_range_k'][0]<=t<=p['temperature_range_k'][1])
        a,b,c,d,e,f,g,h0=segment['coefficients'];x=t/1000
        return (species['formation_enthalpy_298_j_mol']+1000*(a*x+b*x*x/2+c*x**3/3+d*x**4/4-e/x+f-h0),
                a*math.log(x)+b*x+c*x*x/2+d*x**3/3-e/(2*x*x)+g)

    def reconstruct(self,point):
        config=self.config;md=config['cell']['dry_mass_kg']
        t=point['temperature_k'];nc=point['condensed_water_mol'];w=nc*self.mass/md
        liquid=self.liquid_at(t,point['pressure_pa'])
        vg=config['cell']['available_fluid_volume_m3']-nc*self.mass/liquid.rho
        partial={k:n*self.r*t/vg for k,n in point['amounts_mol'].items()}
        hexcess,sexcess,mu_ex=self.excess(t,w)
        cp=self.record['dry_caloric_relation'];tr=config['cell']['dry_reference_temperature_k']
        a=cp['intercept']-cp['slope_per_degC']*self.record['celsius_zero_k'];b=cp['slope_per_degC']
        dry_u=md*(a*(t-tr)+b*(t*t-tr*tr)/2)
        dry_s=md*(a*math.log(t/tr)+b*(t-tr))
        gas_u=math.fsum(n*(self.ideal(k,t)[0]-self.r*t) for k,n in point['amounts_mol'].items())
        gas_s=math.fsum(n*(self.ideal(k,t)[1]-self.r*math.log(partial[k]/self.pref))
                       for k,n in point['amounts_mol'].items())
        u=gas_u+nc*(liquid.u*1000*self.mass+self.offset)+dry_u+md*hexcess
        entropy=gas_s+nc*liquid.s*1000*self.mass+dry_s+md*sexcess
        mu_v=self.ideal('H2O',t)[0]-t*(self.ideal('H2O',t)[1]-self.r*math.log(partial['H2O']/self.pref))
        mu_c=liquid.h*1000*self.mass+self.offset-t*liquid.s*1000*self.mass+mu_ex if w else None
        return {'internal_energy_j':float(u),'entropy_j_k':float(entropy),'pressure_pa':math.fsum(partial.values()),
            'gas_volume_m3':float(vg),'mu_vapor_minus_condensed_j_mol':float(mu_v-mu_c) if w else None,
            'dry_cp_j_kg_k':a+b*t,'moisture_kg_kg':w}

    def fluxes(self,at_time,point):
        c=self.config;gas=c['transfer'];p=c['boundary_program']['values']
        interpolate=lambda key:float(np.interp(at_time,p['knot_times_s'],p[key]))
        species=p['species_order'];masses=c['molar_masses_kg_mol']
        left={'t':point['temperature_k'],'p':point['pressure_pa'],
              'x':{k:point['amounts_mol'][k]/math.fsum(point['amounts_mol'].values()) for k in species}}
        right={'t':interpolate('gas_temperature_k'),'p':interpolate('total_pressure_pa'),
               'x':{k:float(np.interp(at_time,p['knot_times_s'],np.array(p['mole_fractions'])[:,i])) for i,k in enumerate(species)}}
        return self.connection(left,right,gas)

    def between_states(self,left,right,transfer):
        def endpoint(point):
            total=math.fsum(point['amounts_mol'].values())
            return {'t':point['temperature_k'],'p':point['pressure_pa'],
                    'x':{k:n/total for k,n in point['amounts_mol'].items()}}
        return self.connection(endpoint(left),endpoint(right),transfer)

    def connection(self,left,right,gas):
        species=self.config['boundary_program']['values']['species_order']
        masses=self.config['molar_masses_kg_mol']
        for end in [left,right]:
            mean=math.fsum(end['x'][k]*masses[k] for k in species)
            end['y']={k:end['x'][k]*masses[k]/mean for k in species}
            end['mu_over_t']={k:self.ideal(k,end['t'])[0]/end['t']-self.ideal(k,end['t'])[1]+
                self.r*math.log(end['x'][k]*end['p']/self.pref) for k in species}
        dl,dr=gas['cell_distance_m'],gas['reservoir_distance_m'];weight=dr/(dl+dr)
        tf=weight*left['t']+(1-weight)*right['t'];pf=weight*left['p']+(1-weight)*right['p']
        xf={k:weight*left['x'][k]+(1-weight)*right['x'][k] for k in species}
        total=math.fsum(xf.values());xf={k:v/total for k,v in xf.items()}
        mean=math.fsum(xf[k]*masses[k] for k in species);rho=pf*mean/(self.r*tf)
        star={k:-rho*masses[k]/mean*gas['effective_diffusivities_m2_s'][k]*(right['x'][k]-left['x'][k])/(dl+dr) for k in species}
        total_star=math.fsum(star.values());donor_c=left if total_star<0 else right
        diffuse={k:gas['area_m2']*(star[k]-donor_c['y'][k]*total_star)/masses[k] for k in species}
        velocity=-gas['permeability_m2']*gas['relative_permeability']/gas['viscosity_pa_s']*(right['p']-left['p'])/(dl+dr)
        donor=left if velocity>0 else right
        advect={k:gas['area_m2']*rho*donor['y'][k]*velocity/masses[k] for k in species}
        net={k:diffuse[k]+advect[k] for k in species}
        energy=gas['area_m2']*(left['t']-right['t'])/(dl/gas['cell_conductivity_w_m_k']+dr/gas['reservoir_conductivity_w_m_k'])
        energy+=math.fsum(diffuse[k]*self.ideal(k,tf)[0]+advect[k]*self.ideal(k,donor['t'])[0] for k in species)
        external=energy/right['t']-math.fsum(right['mu_over_t'][k]*net[k] for k in species)
        production=energy*(1/right['t']-1/left['t'])+math.fsum(net[k]*(left['mu_over_t'][k]-right['mu_over_t'][k]) for k in species)
        return {'net_mol_s':net,'energy_out_w':energy,'external_entropy_w_k':external,'production_w_k':production}


class FreeWaterSource(SorptiveSource):
    """Independent direct-liquid and integrated end-line reference equations."""
    def __init__(self, header, settings):
        super().__init__(header, settings)
        self.m_end, self.b_end = self.m0(self.wr), self.b0(self.wr)
        self.m_slope = (self.m_end-self.m0(self.activity_nodes[-2]))/(self.wr-self.activity_nodes[-2])
        self.b_slope = (self.b_end-self.b0(self.heat_nodes[-2]))/(self.wr-self.heat_nodes[-2])

    def phase_partition(self, t, w):
        def mu(wb):
            b = self.b_end+self.b_slope*(wb-self.wr)
            m = self.m_end+self.m_slope*(wb-self.wr)
            return b-t*(b-m)/self.t0
        policy = self.settings['phase_partition_root']
        ws = brentq(mu,self.wr,self.record['model_domain']['moisture_kg_kg'][1],
                    xtol=policy['moisture_absolute_tolerance_kg_kg'],
                    rtol=policy['relative_tolerance'],maxiter=policy['maximum_iterations'])
        return min(w,ws),max(0.,w-ws),mu

    def excess(self,t,w):
        if w <= self.wr:
            return super().excess(t,w)
        bound,free,mu = self.phase_partition(t,w)
        settings = self.settings
        integrate = lambda f:quad(f,self.wr,bound,
            epsabs=settings['quad_absolute_tolerance'],epsrel=settings['quad_relative_tolerance'],
            limit=settings['quad_maximum_subintervals'])[0]
        h = integrate(lambda x:self.b_end+self.b_slope*(x-self.wr))
        g0 = integrate(lambda x:self.m_end+self.m_slope*(x-self.wr))
        return h,(h-g0)/self.t0,0. if free>0 else self.mass*mu(bound)

    def reconstruct(self,point):
        result = super().reconstruct(point)
        bound,free,_ = self.phase_partition(point['temperature_k'],point['moisture_kg_kg_dry'])
        scale = self.config['cell']['dry_mass_kg']/self.mass
        result.update(sorbed_water_mol=bound*scale,free_water_mol=free*scale)
        return result


class MobileWaterSource(SorptiveSource):
    """Reconstruct full condensed mu/h and its additional internal face rate."""
    def condensed_fields(self,point):
        t,p,w=point['temperature_k'],point['pressure_pa'],point['moisture_kg_kg_dry']
        liquid=self.liquid_at(t,p)
        _,_,mu=self.excess(t,w)
        b=self.b if w<=self.wj else self.b0(w)
        return {'condensed_chemical_potential_j_mol':float(liquid.h*1000*self.mass+self.offset-t*liquid.s*1000*self.mass+mu),
                'condensed_partial_enthalpy_j_mol':float(liquid.h*1000*self.mass+self.offset+self.mass*b)}

    def reconstruct(self,point):
        return {**super().reconstruct(point),**self.condensed_fields(point)}

    def between_states(self,left,right,transfer):
        gas=super().between_states(left,right,transfer)
        condensed=self.condensed_between_states(left,right,transfer)
        net={**gas['net_mol_s'],'H2O':gas['net_mol_s']['H2O']+condensed['flow_mol_s']}
        return {**gas,'net_mol_s':net,'energy_out_w':gas['energy_out_w']+condensed['energy_w'],
                'external_entropy_w_k':gas['external_entropy_w_k']+condensed['external_entropy_w_k'],
                'production_w_k':gas['production_w_k']+condensed['production_w_k']}

    def condensed_between_states(self,left,right,transfer):
        a,b=self.condensed_fields(left),self.condensed_fields(right)
        tl,tr=left['temperature_k'],right['temperature_k']
        h=(a['condensed_partial_enthalpy_j_mol']+b['condensed_partial_enthalpy_j_mol'])/2
        force=a['condensed_chemical_potential_j_mol']/tl-b['condensed_chemical_potential_j_mol']/tr+h*(1/tr-1/tl)
        length=transfer['cell_distance_m']+transfer['reservoir_distance_m']
        mobility=transfer['area_m2']/length*self.config['condensed_transfer']['mobility_density_mol2_k_j_s_m']
        flow=mobility*force;energy=flow*h
        return {'flow_mol_s':flow,'energy_w':energy,
                'external_entropy_w_k':(energy-b['condensed_chemical_potential_j_mol']*flow)/tr,
                'production_w_k':flow*force}


class EvaporatingSurfaceSource(MobileWaterSource):
    """Direct-IAPWS surface root with independent connection/source equations."""
    def __init__(self,header,settings):
        super().__init__(header,settings)
        c=self.config;self.surface_policy=c['surface_equilibrium']
        half=c['geometry']['length_m']/header['cell_count']/2
        film=c['transfer']['reservoir_distance_m']
        kin,kout=c['transfer']['cell_conductivity_w_m_k'],c['transfer']['reservoir_conductivity_w_m_k']
        self.inner_surface={**c['transfer'],'area_m2':c['geometry']['face_area_m2'],
            'cell_distance_m':half/2,'reservoir_distance_m':half/2,
            'cell_conductivity_w_m_k':kin,'reservoir_conductivity_w_m_k':kin}
        self.outer_surface={**c['transfer'],'area_m2':c['geometry']['face_area_m2'],
            'cell_distance_m':film/2,'reservoir_distance_m':film/2,
            'cell_conductivity_w_m_k':kout,'reservoir_conductivity_w_m_k':kout}

    def fluxes(self,at_time,point):
        policy=self.surface_policy;program=self.config['boundary_program']['values']
        species=program['species_order'];total=math.fsum(point['amounts_mol'].values())
        left={'t':point['temperature_k'],'p':point['pressure_pa'],'x':{k:v/total for k,v in point['amounts_mol'].items()}}
        right={'t':float(np.interp(at_time,program['knot_times_s'],program['gas_temperature_k'])),
               'p':float(np.interp(at_time,program['knot_times_s'],program['total_pressure_pa'])),
               'x':{k:float(np.interp(at_time,program['knot_times_s'],np.array(program['mole_fractions'])[:,i])) for i,k in enumerate(species)}}
        references=np.array([self.ideal(k,policy['residual_reference_temperature_k'])[0] for k in species])
        scales=np.array([policy['inventory_residual_scale_mol_s']]*len(species)+[policy['energy_residual_scale_w']])
        x0=[point['temperature_k']/policy['temperature_coordinate_scale_k'],point['pressure_pa']/policy['pressure_coordinate_scale_pa'],
            math.log(point['moisture_kg_kg_dry']),math.log(left['x']['O2']/left['x']['N2'])]

        def evaluate(coordinates):
            t=float(coordinates[0])*policy['temperature_coordinate_scale_k'];p=float(coordinates[1])*policy['pressure_coordinate_scale_pa']
            w=math.exp(float(coordinates[2]));fraction=1/(1+math.exp(-float(coordinates[3])))
            surface={'temperature_k':t,'pressure_pa':p,'moisture_kg_kg_dry':w}
            fields=self.condensed_fields(surface)
            vapor_mu0=self.ideal('H2O',t)[0]-t*self.ideal('H2O',t)[1]
            xv=self.pref/p*math.exp((fields['condensed_chemical_potential_j_mol']-vapor_mu0)/(self.r*t))
            endpoint={'t':t,'p':p,'x':{'O2':(1-xv)*fraction,'N2':(1-xv)*(1-fraction),'H2O':xv}}
            gas_in=self.connection(left,endpoint,self.inner_surface)
            liquid_in=self.condensed_between_states(point,surface,self.inner_surface)
            gas_out=self.connection(endpoint,right,self.outer_surface)
            net={**gas_in['net_mol_s'],'H2O':gas_in['net_mol_s']['H2O']+liquid_in['flow_mol_s']}
            energy=gas_in['energy_out_w']+liquid_in['energy_w']
            differences=np.array([net[k]-gas_out['net_mol_s'][k] for k in species]+[energy-gas_out['energy_out_w']])
            result={'net_mol_s':net,'energy_out_w':energy,'external_entropy_w_k':gas_out['external_entropy_w_k'],
                'production_w_k':gas_in['production_w_k']+liquid_in['production_w_k']+gas_out['production_w_k'],
                'surface_state':{**surface,**fields,'gas_mole_fractions':endpoint['x']},
                'surface_inventory_residuals_mol_s':dict(zip(species,map(float,differences[:-1]),strict=True)),
                'surface_energy_residual_w':float(differences[-1]),
                'individual_productions_w_k':[gas_in['production_w_k'],liquid_in['production_w_k'],gas_out['production_w_k']]}
            return result,differences

        def residual(coordinates):
            differences=evaluate(coordinates)[1].copy();differences[-1]-=differences[:-1]@references
            return differences/scales

        solution=solve_root(residual,x0,method=policy['method'],options={
            'xtol':policy['coordinate_tolerance'],'maxfev':policy['maximum_function_evaluations']})
        if not solution.success:
            raise RuntimeError('independent surface root did not converge: '+solution.message)
        return evaluate(solution.x)[0]


def source_for_column(header,settings):
    return {'source_sorptive_common_gas_column_v1':SorptiveSource,
            'source_sorptive_mobile_column_v1':MobileWaterSource,
            'sorptive_evaporating_surface_column_v1':EvaporatingSurfaceSource,
            'sorptive_free_water_column_v1':FreeWaterSource}[header['parameters']['schema']](header,settings)
