"""Independent high-precision energy-gradient reference for the coupled system."""
import mpmath as mp

from thermal_pore_reference import ThermalPoreReference


class EffusivePoreReference:
    def __init__(self, settings, sources):
        self.settings, self.sources = settings, sources
        self.p = {k:mp.mpf(str(v)) for k,v in settings['model'].items()}
        self.reservoir = {k:mp.mpf(str(v)) for k,v in settings['reservoir'].items()}
        self.r = self.p['gas_constant_j_mol_k']
        self.thermal = ThermalPoreReference(settings,sources,0)
        molecular = sources['molecular_source']
        row = molecular['species'][settings['gas_species']]
        self.mass = mp.mpf(row['molar_mass_g_mol'])*mp.mpf(molecular['constants']['gram_kg'])
        self.area = mp.pi*mp.mpf(str(settings['connection']['aperture_radius_m']))**2

    def gas(self,t,n,v):
        h,s0 = self.thermal.standard(t)
        pressure = n*self.r*t/v
        s = s0-self.r*mp.log(pressure/self.p['standard_pressure_pa'])
        return {'h':h,'s':s,'mu':h-t*s,'u':h-self.r*t,'pressure':pressure,
                'cv':n*(self.thermal.cp(t)-self.r)}

    def energy_entropy(self,a,tp,tr,npore,nreservoir):
        pore = self.gas(tp,npore,4*mp.pi*a**3/3)
        reservoir = self.gas(tr,nreservoir,self.reservoir['volume_m3'])
        cp = self.thermal.capacity
        cr = self.reservoir['body_heat_capacity_j_k']
        t0 = self.p['reference_temperature_k']
        u = npore*pore['u']+nreservoir*reservoir['u']+cp*(tp-t0)+cr*(tr-t0)+4*mp.pi*self.p['surface_tension_n_m']*a*a
        s = npore*pore['s']+nreservoir*reservoir['s']+cp*mp.log(tp/t0)+cr*mp.log(tr/t0)
        return u,s

    def at_state(self,a,tp,tr,npore,nreservoir,boundary):
        b = {k:mp.mpf(str(v)) for k,v in boundary.items()}
        source = ThermalPoreReference(self.settings,self.sources,npore)
        mechanical = source.at_state(a,tp,b['pore_bath_temperature_k'],b['pore_heat_conductance_w_k'])
        pore = self.gas(tp,npore,4*mp.pi*a**3/3)
        reservoir = self.gas(tr,nreservoir,self.reservoir['volume_m3'])
        out = self.area*pore['pressure']/mp.sqrt(2*mp.pi*self.mass*self.r*tp)
        into = self.area*reservoir['pressure']/mp.sqrt(2*mp.pi*self.mass*self.r*tr)
        flow = out-into
        energy = out*(pore['h']-self.r*tp/2)-into*(reservoir['h']-self.r*tr/2)
        qp = b['pore_heat_conductance_w_k']*(b['pore_bath_temperature_k']-tp)
        qr = b['reservoir_heat_conductance_w_k']*(b['reservoir_bath_temperature_k']-tr)
        adot = mechanical['radius_rate_m_s']
        work = mechanical['external_work_in_w']
        surface_rate = 8*mp.pi*self.p['surface_tension_n_m']*a*adot
        tpdot = (qp+work-energy-surface_rate+pore['u']*flow)/(pore['cv']+self.thermal.capacity)
        trdot = (qr+energy-reservoir['u']*flow)/(reservoir['cv']+self.reservoir['body_heat_capacity_j_k'])
        effusion_entropy = energy*(1/tr-1/tp)+flow*(pore['mu']/tp-reservoir['mu']/tr)
        heat_entropy = qp*(1/tp-1/b['pore_bath_temperature_k'])+qr*(1/tr-1/b['reservoir_bath_temperature_k'])
        production = mechanical['viscous_dissipation_w']/tp+heat_entropy+effusion_entropy
        u,s = self.energy_entropy(a,tp,tr,npore,nreservoir)
        return {'radius_rate_m_s':adot,'pore_temperature_rate_k_s':tpdot,
                'reservoir_temperature_rate_k_s':trdot,'gas_transfer_mol_s':flow,
                'effusive_energy_w':energy,'internal_energy_j':u,'entropy_j_k':s,
                'pore_pressure_pa':pore['pressure'],'reservoir_pressure_pa':reservoir['pressure'],
                'external_work_in_w':work,'pore_heat_in_w':qp,'reservoir_heat_in_w':qr,
                'viscous_dissipation_w':mechanical['viscous_dissipation_w'],
                'bath_entropy_rate_w_k':-qp/b['pore_bath_temperature_k']-qr/b['reservoir_bath_temperature_k'],
                'entropy_production_w_k':production,'effusion_entropy_production_w_k':effusion_entropy,
                'heat_entropy_production_w_k':heat_entropy}
