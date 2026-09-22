"""Review-side source formulas for the conditional sorptive cell.

No production equilibrium or excess provider is imported. Pure liquid uses
direct IAPWS95 (shared EOS backend); source join uses independent quadrature.
"""
import math

from iapws import IAPWS95
import numpy as np
from scipy.integrate import quad


class SorptiveSource:
    def __init__(self, header, settings):
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
        reference_liquid = IAPWS95(T=t0,P=self.record['reference_liquid_pressure_pa']/1e6)
        latent = float((self.ideal('H2O',t0)[0]-reference_liquid.h*1000*self.mass-self.offset)/self.mass)
        curves = self.record['source_curves']
        a = np.array([[p['moisture_kg_kg'],p['value']] for p in curves['activity']])
        q = np.array([[p['moisture_kg_kg'],p['value']] for p in curves['heat']])
        m0 = lambda w: self.r/self.mass*t0*float(np.interp(w,a[:,0],np.log(a[:,1])))
        b0 = lambda w: latent-float(np.interp(w,q[:,0],q[:,1]))
        integrate = lambda f, nodes: quad(f,wr,wj,points=nodes[1:-1],
            epsabs=settings['quad_absolute_tolerance'],epsrel=settings['quad_relative_tolerance'],
            limit=settings['quad_maximum_subintervals'])[0]
        hj, gj = integrate(b0,q[:,0]), integrate(m0,a[:,0])
        sj = (hj-gj)/t0
        self.b, self.c = b0(wj),(b0(wj)-m0(wj))/t0
        self.h0, self.s0 = hj-self.b*wj, sj-self.c*wj-self.r/self.mass*wj
        self.wj = wj

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
        liquid=IAPWS95(T=t,P=point['pressure_pa']/1e6)
        vg=config['cell']['available_fluid_volume_m3']-nc*self.mass/liquid.rho
        partial={k:n*self.r*t/vg for k,n in point['amounts_mol'].items()}
        hexcess=self.h0+self.b*w
        sexcess=self.s0+(self.c+self.r/self.mass)*w-self.r/self.mass*w*math.log(w/self.wj) if w else self.s0
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
        mu_ex=self.mass*(self.b-t*self.c)+self.r*t*math.log(w/self.wj) if w else None
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
