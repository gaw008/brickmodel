"""Ventilated full-cycle approximation, with an explicit condensed-phase boundary.

Gas has quasi-steady throughput and no stored inventory. Pressure is imposed.
The stored system is condensed matter plus pore surface energy, not a sealed
brick. Outer pressure work and pore-gas pressure work cancel except -p dVs.
All thermochemistry uses one formation-enthalpy reference; there is no separate
reaction-heat source. This module does not use the legacy hash/artifact pipeline.
"""
from __future__ import annotations

from collections import Counter
from copy import deepcopy
import json
from pathlib import Path
import time

import numpy as np
from scipy.integrate import solve_ivp

from ..chemistry.formula import parse_formula


def read_parameters(path: str | Path) -> dict:
    config = json.loads(Path(path).read_text())
    entries = list(config["parameters"].items())
    for scenario in config['scenarios']:
        for name, item in scenario['overrides'].items():
            if item['unit'] != config['parameters'][name]['unit']:
                raise ValueError(f'scenario override unit mismatch: {name}')
            entries.append((scenario['id']+'.'+name,item))
    entries += list(config['synthetic_truth_overrides'].items())
    for name, item in entries:
        value = np.asarray(item["value"])
        lower, upper = np.asarray(item["range"])
        if not np.all(np.isfinite(value)) or np.any(value < lower) or np.any(value > upper):
            raise ValueError(f"parameter outside declared range: {name}")
        if item["status"] not in ("literature", "assumed", "measured"):
            raise ValueError(f"unknown parameter identity: {name}")
        if not item["unit"] or item["source"] not in config["sources"]:
            raise ValueError(f"missing unit/source: {name}")
    return config


def changed(config: dict, overrides: dict) -> dict:
    result = deepcopy(config)
    for name, value in overrides.items():
        result["parameters"][name]["value"] = value
    return result


def write_json(path: str | Path, data: dict) -> None:
    Path(path).parent.mkdir(parents=True, exist_ok=True)
    Path(path).write_text(json.dumps(data, ensure_ascii=False, indent=2, allow_nan=False) + "\n")


class FullCycle:
    def __init__(self, config: dict):
        self.config = config
        self.used_units: dict[str, str] = {}
        self.ns = [s["id"] for s in config["species"] if s["phase"] == "condensed"]
        self.ng = [s["id"] for s in config["species"] if s["phase"] == "gas"]
        self.names = self.ns + self.ng
        self.elements = list(k.removeprefix("atomic.") for k in config["parameters"] if k.startswith("atomic."))
        formulas = {s["id"]: parse_formula(s["formula"]) for s in config["species"]}
        self.atom = np.array([[formulas[s].get(e, 0) for e in self.elements] for s in self.names])
        self.atomic = np.array([self.p("atomic." + e, "kg/mol") for e in self.elements])
        self.mw = self.atom @ self.atomic
        self.nr = len(config["reactions"])
        self.nu = np.array([[r["stoichiometry"].get(s, 0) for s in self.names] for r in config["reactions"]])
        if np.any(self.nu @ self.atom != 0):
            raise ValueError("reaction stoichiometry does not conserve elements")
        self.snu = self.nu[:, :len(self.ns)]
        self.gnu = self.nu[:, len(self.ns):]
        if np.any(self.gnu.sum(axis=1)<0):
            raise ValueError('the declared partial-pressure bound requires nonnegative net gas production')
        self.reactants = [self.ns.index(r["reactant"]) for r in config["reactions"]]
        self.R = self.p("reference.R", "J/mol/K")
        self.Tr = self.p("reference.temperature", "K")
        self.Pr = self.p("reference.pressure", "Pa")
        self.P = self.p("gas.pressure", "Pa")
        self.storage = self.p("gas.storage", "1")
        self.cp = np.array([self.p(f"species.{s}.cp", "J/mol/K") for s in self.names])
        if np.any(self.cp <= 0) or np.any(self.cp[len(self.ns):] <= self.R):
            raise ValueError('positive condensed Cp and ideal-gas Cv are required')
        self.h0 = np.array([self.p(f"species.{s}.h_ref", "J/mol") for s in self.names])
        self.s0 = np.array([self.p(f"species.{s}.s_ref", "J/mol/K") for s in self.names])
        self.v = np.array([self.p(f"species.{s}.volume", "m3/mol") for s in self.ns])
        self.h0[:len(self.ns)] += (self.P - self.Pr) * self.v
        self.k = self.p("thermal.conductivity", "W/m/K")
        self.h = self.p("thermal.h", "W/m2/K")
        self.emissivity = self.p("thermal.emissivity", "1")
        self.sigma = self.p("reference.sigma", "W/m2/K4")
        self.n = int(self.p("numerics.cells", "1"))
        self.area = self.p("geometry.area", "m2")
        self.length = self.p("geometry.half_thickness", "m")
        self.b0 = self.area * self.length / self.n
        self.md = self.p("material.dry_density", "kg/m3") * self.b0
        self.initial = np.zeros((self.n, len(self.ns)))
        fractions = {s: self.p("recipe." + s, "kg/kg") for s in self.ns if "recipe." + s in config["parameters"]}
        if abs(sum(fractions.values()) - 1) > np.finfo(float).eps * len(fractions):
            raise ValueError("dry recipe fractions must sum to one")
        for s, x in fractions.items():
            self.initial[:, self.ns.index(s)] = self.md * x / self.mw[self.names.index(s)]
        self.initial[:, self.ns.index("water")] = self.md * self.p("material.water_dry_ratio", "kg/kg") / self.mw[self.ns.index("water")]
        self.extent_scale = self.initial[0, self.reactants]
        self.vs0 = self.initial @ self.v
        self.vp0 = self.b0 - self.vs0
        if np.any(self.vp0 <= 0):
            raise ValueError("specified wet condensed volumes do not fit the brick geometry")
        self.gamma = self.p("sintering.gamma", "N/m")
        self.radius = self.p("sintering.radius", "m")
        self.es0 = 3 * self.gamma * self.vp0 / self.radius
        self.A = np.array([self.p("kinetics." + r["id"] + ".A", "1/s") for r in config["reactions"]])
        self.Ea = np.array([self.p("kinetics." + r["id"] + ".E", "J/mol") for r in config["reactions"]])
        self.ks = self.p("sintering.rate_ref", "1/s")
        self.Tsref = self.p("sintering.temperature_ref", "K")
        self.Es = self.p("sintering.E", "J/mol")
        self.inlet = np.array([self.p("gas.inlet." + s, "1") for s in self.ng])
        if abs(self.inlet.sum() - 1) > np.finfo(float).eps * len(self.ng) or np.any(self.inlet <= 0):
            raise ValueError("positive gas inlet fractions must sum to one")
        self.sweep = self.p("gas.sweep", "mol/s/kg") * self.md
        self.capacity = self.p("gas.max_generated_per_carrier", "1")
        self.oxygen_use = self.p("gas.max_oxygen_use_fraction", "1")
        self.oxygen = self.ng.index("O2")
        self.times = np.array([0.] + [self.p("process." + s + ".end", "s") for s in config["stages"]]) * self.p("process.time_scale", "1")
        self.temperatures = np.array([self.p("initial.temperature", "K")] + [self.p("process." + s + ".temperature", "K") for s in config["stages"]])
        if np.any(np.diff(self.times) <= 0):
            raise ValueError("process stage times must increase")
        self.surface_iterations = int(self.p("numerics.surface_iterations", "1"))
        self.nscale = float(self.initial.sum())
        self.escale = float(np.sum(self.initial * self.cp[:len(self.ns)]) * self.Tr)
        self.last = 9 * self.n

    def p(self, key: str, unit: str):
        item = self.config["parameters"][key]
        if item["unit"] != unit:
            raise ValueError(f"dimension mismatch for {key}: expected {unit}, found {item['unit']}")
        self.used_units[key] = unit
        return item["value"]

    def unpack(self, y):
        fields = y[:self.last].reshape(9, self.n)
        T = fields[0] * self.Tr
        conversion = -np.expm1(-fields[1:1+self.nr].T)
        extents = conversion * self.extent_scale
        ns = self.initial + extents @ self.snu
        ns[:, self.reactants] = self.extent_scale * np.exp(-fields[1:1+self.nr].T)
        pore = self.vp0 * np.exp(fields[6])
        bulk = pore + ns @ self.v
        surface_energy = self.es0 * (pore / self.vp0) ** (2/3)
        capillary_pressure = 2/3 * surface_energy / pore
        return fields, T, ns, bulk, pore, surface_energy, capillary_pressure

    def thermo(self, T):
        return self.h0 + (T[..., None] - self.Tr) * self.cp, self.s0 + np.log(T[..., None] / self.Tr) * self.cp

    def rates(self, t, y):
        fields, T, ns, bulk, pore, surface, cap = self.unpack(y)
        tf = float(np.interp(t, self.times, self.temperatures))
        hs, ss = self.thermo(T)
        hin, sin = self.thermo(np.asarray(tf))
        mu = hs - T[:, None] * ss
        # Product partial pressures are bounded above by total pressure. The
        # worst-case oxygen activity follows from the two declared flow caps.
        potential_hazard = self.A * np.exp(-self.Ea / (self.R*T[:, None]))
        potential_rate = potential_hazard * ns[:, self.reactants]
        # For this reaction set total outlet flow is at least the carrier flow.
        # Uninhibited positive production bounds actual product partial pressure,
        # allowing low-temperature drying without solving a gas storage problem.
        partial = np.minimum(1., self.inlet + potential_rate @ np.maximum(self.gnu, 0) / self.sweep) * self.P/self.Pr
        partial[:, self.oxygen] = self.P/self.Pr*self.inlet[self.oxygen]*(1-self.oxygen_use)/(1+self.capacity)
        mu[:, len(self.ns):] += self.R * T[:, None] * np.log(partial)
        dg_bound = mu @ self.nu.T - cap[:, None] * (self.snu @ self.v)
        drive = -np.expm1(np.minimum(dg_bound / (self.R*T[:, None]), 0))
        hazard = potential_hazard * drive
        rate = hazard * ns[:, self.reactants]
        generation = rate @ np.maximum(self.gnu, 0).sum(axis=1)
        oxygen_demand = rate @ (-self.gnu[:, self.oxygen])
        factor = np.minimum(1., self.capacity*self.sweep / np.maximum(generation, np.finfo(float).tiny))
        factor = np.minimum(factor, self.oxygen_use*self.sweep*self.inlet[self.oxygen] / np.maximum(oxygen_demand, np.finfo(float).tiny))
        rate *= factor[:, None]
        hazard *= factor[:, None]
        dn = rate @ self.snu
        fin = np.broadcast_to(self.sweep * self.inlet, (self.n, len(self.ng)))
        fout = fin + rate @ self.gnu
        yf = fout / fout.sum(axis=1)[:, None]
        flow_energy = fin @ hin[len(self.ns):] - np.sum(fout * hs[:, len(self.ns):], axis=1)
        widths = bulk / self.area
        conductance = self.k*self.area / ((widths[:-1] + widths[1:])/2)
        internal = conductance * np.diff(T)
        heat = np.zeros(self.n)
        heat[:-1] += internal
        heat[1:] -= internal
        # Surface conduction and convection/radiation use the same face flux.
        surface_T = float(T[-1])
        resistance = widths[-1] / (2*self.k)
        for _ in range(self.surface_iterations):
            q = self.h*(tf-surface_T) + self.emissivity*self.sigma*(tf**4-surface_T**4)
            residual = surface_T-T[-1]-resistance*q
            slope = 1 + resistance*(self.h+4*self.emissivity*self.sigma*surface_T**3)
            surface_T -= residual/slope
        qext = self.area * (surface_T-T[-1]) / resistance
        heat[-1] += qext
        db = -self.ks * np.exp(-self.Es/self.R*(1/T-1/self.Tsref)) * pore
        dsurf = cap * (db - dn @ self.v)
        dT = (heat + flow_energy - np.sum(hs[:, :len(self.ns)]*dn, axis=1) - dsurf) / (ns @ self.cp[:len(self.ns)])
        entropy_in = sin[len(self.ns):] - self.R*np.log(self.inlet*self.P/self.Pr)
        entropy_out = ss[:, len(self.ns):] - self.R*np.log(yf*self.P/self.Pr)
        sexchange = qext/tf + np.sum(fin @ entropy_in - np.sum(fout*entropy_out, axis=1))
        dS = float(np.sum(dn*ss[:, :len(self.ns)]) + np.sum((ns@self.cp[:len(self.ns)])*dT/T))
        return dT, rate, db, heat, flow_energy, fin, fout, yf, tf, surface_T, dS-sexchange, sexchange, hazard

    def rhs(self, t, y):
        dT, rates, db, heat, flow, fin, fout, _, _, _, production, exchange, hazard = self.rates(t, y)
        dy = np.zeros_like(y)
        d = dy[:self.last].reshape(9, self.n)
        d[0] = dT/self.Tr
        # A zero reactant inventory is an explicitly absent recipe component.
        d[1:6] = (hazard * (self.extent_scale != 0)).T
        pore = self.vp0 * np.exp(y[:self.last].reshape(9, self.n)[6])
        d[6] = (db - (rates@self.snu)@self.v)/pore
        d[7] = heat/self.escale
        d[8] = flow/self.escale
        g = len(self.ng)
        dy[self.last:self.last+g] = fin.sum(axis=0)/self.nscale
        dy[self.last+g:self.last+2*g] = fout.sum(axis=0)/self.nscale
        dy[-2:] = np.array([production, exchange])*self.Tr/self.escale
        return dy

    def initial_state(self):
        y = np.zeros(self.last+2*len(self.ng)+2)
        f = y[:self.last].reshape(9, self.n)
        f[0] = self.temperatures[0]/self.Tr
        return y

    def integrate(self):
        started = time.monotonic()
        step = self.p("numerics.output_step", "s")
        times = np.unique(np.r_[np.arange(0, self.times[-1], step), self.times])
        sol = solve_ivp(self.rhs, (0., self.times[-1]), self.initial_state(), method="BDF", t_eval=times,
                        max_step=self.p("numerics.max_step", "s"), rtol=self.p("numerics.rtol", "1"), atol=self.p("numerics.atol", "1"))
        if not sol.success:
            raise RuntimeError(sol.message)
        report, fields = self.summarize(sol.t, sol.y.T)
        report["elapsed_s"] = time.monotonic()-started
        report["solver"] = {"method":"BDF", "nfev":sol.nfev, "njev":sol.njev, "cells":self.n}
        report["dimension_check"] = {"passed":True, "consumed_parameter_units":self.used_units,
            "identities":["mol*(kg/mol)=kg", "mol*(J/mol)=J", "W*s=J", "Pa*m3=J", "(N/m)*m2=J", "(W/m/K)*m2*K/m=W", "(J/mol)/(R*T)=1"]}
        return report, fields

    def summarize(self, times, states):
        rows=[]; inventories=[]; energies=[]; entropies=[]; gasin=[]; gasout=[]; heat=[]; flow=[]; vs=[]; bulks=[]
        minimum_production = float("inf")
        mw_s=self.mw[:len(self.ns)]; mw_g=self.mw[len(self.ns):]
        for t,y in zip(times,states):
            f,T,ns,bulk,pore,surface,cap=self.unpack(y)
            rate=self.rates(t,y)
            h,s=self.thermo(T)
            energy=float(np.sum(ns*h[:,:len(self.ns)])+surface.sum())
            inventories.append(ns.sum(axis=0)); energies.append(energy); entropies.append(float(np.sum(ns*s[:,:len(self.ns)])))
            g=len(self.ng); gasin.append(y[self.last:self.last+g]*self.nscale); gasout.append(y[self.last+g:self.last+2*g]*self.nscale)
            heat.append(f[7].sum()*self.escale);flow.append(f[8].sum()*self.escale);vs.append(float(np.sum(ns@self.v)));bulks.append(float(bulk.sum()))
            center_T=float((9*T[0]-T[1])/8)
            temperature_span=max(float(T.max()),rate[9],center_T)-min(float(T.min()),rate[9],center_T)
            minimum_production=min(minimum_production,rate[10])
            rows.append({"time_s":float(t),"kiln_temperature_k":rate[8],"temperature_k":T.tolist(),
                "x_m":(np.cumsum(bulk/self.area)-bulk/self.area/2).tolist(),
                "water_kg_per_initial_dry_kg":(ns[:,self.ns.index('water')]*mw_s[self.ns.index('water')]/self.md).tolist(),
                "conversion":{r['id']:(-np.expm1(-f[1+i])).tolist() for i,r in enumerate(self.config['reactions'])},
                "residual_carbon_kg":((ns[:,self.ns.index('organic')]+ns[:,self.ns.index('char')])*self.atomic[self.elements.index('C')]).tolist(),
                "gas_mole_fractions":{s:rate[7][:,i].tolist() for i,s in enumerate(self.ng)},
                "pressure_pa":[self.P]*self.n,"porosity":(pore/bulk).tolist(),"thickness_shrinkage":(1-bulk/self.b0).tolist(),
                "temperature_difference_k":temperature_span,"mass_kg":float(np.sum(ns@mw_s)),
                "net_heat_and_flow_w":float(rate[3].sum()+rate[4].sum()),
                "dsc_endothermic_w_per_initial_dry_kg":float(np.sum((ns@self.cp[:len(self.ns)])*rate[0]) + np.sum(rate[1]*(h@self.nu.T))
                    + np.sum(cap*(rate[2]-(rate[1]@self.snu)@self.v)))/(self.n*self.md),
                "entropy_production_w_k":rate[10]})
        inventories=np.array(inventories); energies=np.array(energies); gasin=np.array(gasin); gasout=np.array(gasout);heat=np.array(heat);flow=np.array(flow);vs=np.array(vs);bulks=np.array(bulks)
        mass=inventories@mw_s; elements=inventories@self.atom[:len(self.ns)]
        gas_balance=gasin-gasout
        balance_threshold=self.p('acceptance.balance_relative','1')
        def balance(i,j):
            di=inventories[i:j+1]-inventories[i]; dg=gas_balance[i:j+1]-gas_balance[i]
            mass_error=di@mw_s-dg@mw_g
            elem_error=di@self.atom[:len(self.ns)]-dg@self.atom[len(self.ns):]
            elem_scale=np.maximum(elements[0], (gasin[j]-gasin[i])@self.atom[len(self.ns):])
            elem_rel=np.divide(np.abs(elem_error),elem_scale,out=np.zeros_like(elem_error),where=elem_scale!=0)
            # Scale by exchanged energy, not huge cancelling formation energies.
            Escale=max(float(np.ptp(heat[i:j+1])+np.ptp(flow[i:j+1])), self.escale)
            eerror=energies[i:j+1]-energies[i]-(heat[i:j+1]-heat[i])-(flow[i:j+1]-flow[i])
            rel={'mass':float(np.max(np.abs(mass_error))/mass[0]),'elements':float(elem_rel.max()),'energy':float(np.max(np.abs(eerror))/Escale)}
            return {'relative_residuals':rel,'passed':max(rel.values())<balance_threshold,'energy_scale_j':Escale,
                'maximum_energy_residual_j':float(np.max(np.abs(eerror))),
                'outer_pressure_work_j':float(-self.P*(bulks[j]-bulks[i])),
                'pore_gas_pressure_work_j':float(self.P*((bulks[j]-vs[j])-(bulks[i]-vs[i]))),
                'condensed_internal_energy_change_j':float(energies[j]-energies[i]-self.P*(vs[j]-vs[i]))}
        stages={}
        for i,name in enumerate(self.config['stages']):
            a=int(np.where(times==self.times[i])[0][0]);b=int(np.where(times==self.times[i+1])[0][0]);stages[name]=balance(a,b)
        final=rows[-1]; phi=float(np.average(final['porosity'],weights=self.unpack(states[-1])[3]))
        density=float(mass[-1]/bulks[-1]); carbon=float(sum(final['residual_carbon_kg']))
        peak=max(r['temperature_difference_k'] for r in rows)
        summary={'mass_kg':float(mass[-1]),'density_kg_m3':density,'loss_on_ignition_dry_fraction':float(1-mass[-1]/(self.n*self.md)),
            'porosity':phi,'residual_carbon_kg':carbon,'shrinkage':float(1-bulks[-1]/bulks[0]),'peak_temperature_difference_k':peak,
            'absorption_kg_kg':self.p('product.connectivity','1')*phi*self.p('product.water_density','kg/m3')/density,
            'strength_pa':self.p('product.dense_strength','Pa')*float(np.exp(-self.p('product.porosity_coefficient','1')*phi)),
            'defect_indicator':float(-np.expm1(-peak/self.p('product.gradient_scale','K'))),
            'minimum_sampled_entropy_production_w_k':minimum_production}
        all_balance=balance(0,len(times)-1)
        drying_index=int(np.where(times==self.times[self.config['stages'].index('drying')+1])[0][0])
        remaining_fraction=max(rows[drying_index]['water_kg_per_initial_dry_kg'])/self.p('material.water_dry_ratio','kg/kg')
        cooled_error=max(abs(t-self.temperatures[-1]) for t in final['temperature_k'])
        report={'schema':'sludge_vme_full_cycle_result_v1','scope':self.config['scope'],'material_applicability':'待实测','real_world_validation':'待实测',
            'gas_approximation':'Quasi-steady local swept pores at imposed pressure. No stored gas, pressure accumulation, Darcy or species diffusion prediction.',
            'summary':summary,'whole_cycle':all_balance,'stages':stages,
            'conservation_passed':all_balance['passed'] and all(s['passed'] for s in stages.values()),
            'thermodynamics':{'minimum_sampled_entropy_production_w_k':minimum_production,'reaction_heat_counted_once':True,
                'entropy_balance_residual_j_k':float(entropies[-1]-entropies[0]-(states[-1,-2:].sum())*self.escale/self.Tr)},
            'parameter_status_counts':dict(Counter(x['status'] for x in self.config['parameters'].values())),
            'state_domain':{'minimum_condensed_moles':float(inventories.min()),'minimum_temperature_k':min(min(r['temperature_k']) for r in rows),
                            'minimum_porosity':min(min(r['porosity']) for r in rows)}}
        report['example_endpoints']={'drying_remaining_fraction':remaining_fraction,'cooling_maximum_temperature_difference_k':cooled_error,
            'passed':bool(remaining_fraction < self.p('acceptance.drying_remaining_fraction','1') and cooled_error < self.p('acceptance.cooling_temperature_difference','K'))}
        report['physical_consistency_passed']=bool(report['conservation_passed'] and report['state_domain']['minimum_condensed_moles']>=0
            and report['state_domain']['minimum_porosity']>0 and minimum_production>=0)
        return report, {'schema':'sludge_vme_full_cycle_fields_v1','cell_count':self.n,'rows':rows}


def make_cycle(config: dict):
    mode = config['parameters']['gas.storage']['value']
    if mode == 0:
        return FullCycle(config)
    if mode == 1 and config['parameters']['solid.thermoelastic']['value'] == 1:
        from .full_cycle_solid import ThermoelasticFullCycle
        return ThermoelasticFullCycle(config)
    if mode == 1 and config['parameters']['solid.thermoelastic']['value'] == 0:
        from .full_cycle_gas import FiniteGasFullCycle
        return FiniteGasFullCycle(config)
    raise ValueError('gas.storage and solid.thermoelastic must explicitly select 0 or 1')


def run_cycle(config: dict):
    return make_cycle(config).integrate()


def run_acceptance(config: dict, out: Path):
    base,fields=run_cycle(config)
    write_json(out/'summary.json',base)
    write_json(out/'fields.json',fields)
    refined_time,_=run_cycle(changed(config,{'numerics.max_step':config['parameters']['numerics.max_step']['value']/2}))
    refined_grid,_=run_cycle(changed(config,{'numerics.cells':2*config['parameters']['numerics.cells']['value']}))
    metrics=['porosity','residual_carbon_kg','shrinkage','peak_temperature_difference_k']
    if config['parameters']['gas.storage']['value'] == 1:
        metrics.append('peak_overpressure_pa')
    differences={kind:{m:abs(base['summary'][m]-r['summary'][m])/max(abs(r['summary'][m]),config['parameters']['acceptance.floor.'+m]['value']) for m in metrics} for kind,r in [('time',refined_time),('grid',refined_grid)]}
    passed=all(v<config['parameters']['acceptance.convergence_relative']['value'] for d in differences.values() for v in d.values())
    result={'passed':passed and all(r['physical_consistency_passed'] and r['example_endpoints']['passed'] for r in (base,refined_time,refined_grid)),
        'relative_differences':differences,'denominator':'max(abs(refined output), predeclared per-metric floor)',
        'refined_time':refined_time,'refined_grid':refined_grid}
    write_json(out/'acceptance.json',result)
    return result
