"""Full-state review from source records, without production thermochemistry."""
import math


class SourceState:
    def __init__(self,sources):
        cv=sources['calcium_volume_source'];vs=sources['solid_volume_source']
        self.volumes={name:float(row['volume_cm3_mol'])*cv['cubic_metres_per_cubic_centimetre']
                      for name,row in cv['phases'].items()}
        self.volumes['C']=float(vs['graphite']['volume_cm3_mol'])*vs['cubic_metres_per_cubic_centimetre']
        source=sources['carbon_source'];self.r=float(source['gas_constant_j_mol_k']);self.p0=float(source['reference_pressure_pa'])
        self.thermal={}
        for name,phase in source['phases'].items():
            self.thermal[name]=(tuple(map(float,phase['cp_coefficient_strings'])),float(source['reference_temperature_k']),
                float(phase['reference_enthalpy_j_mol']),float(phase['reference_entropy_j_mol_k']))
        for phase in sources['calcite_facts']['species']:
            name=phase['id']
            if name in ['calcite','lime']:
                self.thermal[name]=(tuple(float(phase['cp']['coefficients_nominal'][key]) for key in ['A1','A2','A3','A4','A5']),
                    float(sources['calcite_facts']['reference_state']['temperature_k']),
                    float(phase['reference_298']['hf_kj_mol'])*sources['calcite_parameters']['joules_per_kilojoule'],
                    float(sources['calcite_source']['phases'][name]['entropy_reference_j_mol_k']))
        self.reference={name:self.primitive(data[0],data[1]) for name,data in self.thermal.items()}

    @staticmethod
    def primitive(coefficients,t):
        a,b,c,d,e=coefficients
        return (a*t+b*t*t/2-c/t+2*d*math.sqrt(t)+e*t**3/3,
                a*math.log(t)+b*t-c/(2*t*t)-2*d/math.sqrt(t)+e*t*t/2)

    def reconstruct(self,state,volume,inventory):
        t,p=state['temperature_k'],state['pressure_pa'];n=state['amounts_mol']
        gas={k:n[k] for k in ['CO','CO2','O2','N2']};ng=math.fsum(gas.values());h={};s={};mu={}
        for name,data in self.thermal.items():
            hp,sp=self.primitive(data[0],t);hp0,sp0=self.reference[name]
            h[name]=data[2]+hp-hp0;s[name]=data[3]+sp-sp0
            if name in gas:s[name]-=self.r*math.log(p/self.p0*gas[name]/ng)
            else:h[name]+=(p-self.p0)*self.volumes[name]
            mu[name]=h[name]-t*s[name]
        solid_v=math.fsum(n[k]*v for k,v in self.volumes.items());gas_v=ng*self.r*t/p
        enthalpy=math.fsum(n[k]*h[k] for k in n);entropy=math.fsum(n[k]*s[k] for k in n)
        energy=math.fsum(n[k]*(h[k]-p*self.volumes[k]) for k in self.volumes)
        energy+=math.fsum(n[k]*(h[k]-self.r*t) for k in gas)
        elements=[n['calcite']+n['lime'],math.fsum(n[k] for k in ['calcite','C','CO','CO2']),
                  math.fsum((3*n['calcite'],n['lime'],n['CO'],2*n['CO2'],2*n['O2'])),n['N2']]
        a1=mu['CO']-mu['C']-mu['O2']/2;a2=mu['CO2']-mu['C']-mu['O2']
        ag=mu['CO2']-mu['CO']-mu['O2']/2;ac=mu['lime']+mu['CO2']-mu['calcite']
        ce=max(abs(a1),abs(a2),abs(ag)) if state['carbon_phase']=='graphite_present' else max(0.,a1,a2,abs(ag))
        ae={'calcite':max(0.,-ac),'lime':max(0.,ac),'coexistence':abs(ac)}[state['calcium_phase']]
        errors={'element_mol':max(abs(a-b) for a,b in zip(elements,inventory,strict=True)),
            'pressure_pa':max(abs(p-ng*self.r*t/(volume-solid_v)),abs(math.fsum(state['partial_pressures_pa'].values())-p),
                *(abs(state['partial_pressures_pa'][k]-p*v/ng) for k,v in gas.items())),
            'volume_m3':max(abs(solid_v+gas_v-volume),abs(solid_v-state['solid_volume_m3']),abs(gas_v-state['gas_volume_m3'])),
            'reaction_gibbs_j_mol':max(ce,ae),'source_energy_j':max(abs(energy-state['internal_energy_j']),abs(enthalpy-state['enthalpy_j'])),
            'source_entropy_j_k':abs(entropy-state['entropy_j_k'])}
        return {'temperature_k':t,'internal_energy_j':energy,'entropy_j_k':entropy,'h':h,'mu':mu,'errors':errors,
            'minimum_gas_mol':min(gas.values()),'minimum_solid_mol':min(n[k] for k in self.volumes),
            'element_inventories':elements}


def independent_exchange(left,right,parameters):
    tl,tr=left['temperature_k'],right['temperature_k'];names=parameters['gas_order']
    h={k:(left['h'][k]+right['h'][k])/2 for k in names}
    force={k:math.fsum((left['mu'][k]/tl,-right['mu'][k]/tr,h[k]*(1/tr-1/tl))) for k in names}
    flow={k:parameters['gas_mobilities_mol2_k_j_s'][k]*force[k] for k in names}
    energy=math.fsum([parameters['heat_conductance_w_k']*(tl-tr)]+[h[k]*flow[k] for k in names])
    sl=math.fsum([-energy]+[left['mu'][k]*flow[k] for k in names])/tl
    sr=math.fsum([energy]+[-right['mu'][k]*flow[k] for k in names])/tr
    elemental=[flow['CO']+flow['CO2'],flow['CO']+2*flow['CO2']+2*flow['O2'],flow['N2']]
    dissipation=parameters['heat_conductance_w_k']*(tl-tr)**2/(tl*tr)
    dissipation+=math.fsum(parameters['gas_mobilities_mol2_k_j_s'][k]*force[k]**2 for k in names)
    return {'gas':flow,'inventory':elemental,'energy':energy,'entropy':[sl,sr],
            'production':math.fsum((sl,sr)),'dissipation':dissipation}
