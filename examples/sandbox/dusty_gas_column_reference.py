"""Independent original nonsymmetric Dusty Gas equations for column review.

Production uses a symmetric velocity-friction solve and adds Darcy advection.
This reference solves the full original equations directly for the total molar
flux. It retains pore-volume storage and density-dependent ideal-gas entropy.
"""
import numpy as np
from numpy.polynomial.legendre import leggauss


class ColumnReference:
    def __init__(self, header):
        self.settings = header['settings']
        self.count = header['cell_count']
        self.gas_constant = header['gas_constant_j_mol_k']
        self.temperature = self.settings['temperature_k']
        self.rt = self.gas_constant*self.temperature
        self.masses = np.asarray(header['molar_masses_kg_mol'])
        self.viscosities = np.asarray(header['pure_viscosities_pa_s'])
        self.products = np.asarray(header['diffusivity_pressure_products_pa_m2_s'])
        self.species_count = len(self.masses)
        self.pore = self.settings['pore']
        self.scale = self.pore['porosity']/self.pore['tortuosity']
        self.knudsen = (2/3*self.pore['mean_pore_radius_m']*self.scale
            *np.sqrt(8*self.rt/(np.pi*self.masses)))
        self.phi = np.array([[(1+np.sqrt(self.viscosities[i]/self.viscosities[j])
            *(self.masses[j]/self.masses[i])**0.25)**2/np.sqrt(8*(1+self.masses[i]/self.masses[j]))
            for j in range(self.species_count)] for i in range(self.species_count)])
        self.area = self.settings['geometry']['area_m2']
        self.width = self.settings['geometry']['length_m']/self.count
        self.volume = self.pore['porosity']*self.area*self.width
        self.reference_concentration = self.settings['entropy_reference_pressure_pa']/self.rt
        nodes, weights = leggauss(self.settings['verification']['reference_face_quadrature_order'])
        self.nodes, self.weights = (nodes+1)/2, weights/2

    def mixture_viscosity(self, fractions):
        return np.sum(fractions*self.viscosities/(fractions@self.phi.T), axis=2)

    def evaluate(self, values):
        species = self.species_count
        concentrations = np.asarray(values).reshape(self.count, species)
        inventories = self.volume*concentrations
        entropy = -self.gas_constant*np.sum(inventories*np.log(concentrations/self.reference_concentration), axis=1)
        jump = np.diff(np.log(concentrations), axis=0)
        c = np.exp(np.log(concentrations[:-1])[:, None, :]+self.nodes[None, :, None]*jump[:, None, :])
        total = np.sum(c, axis=2, keepdims=True)
        x = c/total
        gradient = jump[:, None, :]/self.width
        pressure_gradient = self.rt*np.sum(c*gradient, axis=2)
        viscosity = self.mixture_viscosity(x)
        matrix = np.zeros((*c.shape[:2], species, species))
        for i in range(species):
            for j in range(species):
                matrix[:, :, i, j] = (1/self.knudsen[i]
                    +sum(self.rt*c[:, :, k]/(self.products[i, k]*self.scale) for k in range(species) if k != i)
                    if i == j else -self.rt*c[:, :, i]/(self.products[i, j]*self.scale))
        darcy_velocity = -self.pore['permeability_m2']*pressure_gradient/viscosity
        rhs = -c*gradient+c/self.knudsen*darcy_velocity[:, :, None]
        point_flux = np.linalg.solve(matrix, rhs[..., None])[..., 0]
        darcy_flux = c*darcy_velocity[:, :, None]
        diffusive_flux = point_flux-darcy_flux
        velocity = diffusive_flux/c
        residual = point_flux/self.knudsen+c*gradient-c/self.knudsen*darcy_velocity[:, :, None]
        molecular = np.zeros(c.shape[:2])
        for i in range(species):
            for j in range(i+1, species):
                effective = self.products[i,j]*self.scale/(self.rt*total[:, :, 0])
                numerator = x[:, :, j]*point_flux[:, :, i]-x[:, :, i]*point_flux[:, :, j]
                residual[:, :, i] += numerator/effective
                residual[:, :, j] -= numerator/effective
                molecular += (self.gas_constant*total[:, :, 0]*x[:, :, i]*x[:, :, j]
                    *(velocity[:, :, i]-velocity[:, :, j])**2/effective)
        wall = self.gas_constant*np.sum(c*velocity**2/self.knudsen, axis=2)
        darcy = self.pore['permeability_m2']*pressure_gradient**2/(viscosity*self.temperature)
        internal_flux = np.sum(point_flux*self.weights[None, :, None], axis=1)
        flux = np.zeros((self.count+1, species))
        flux[1:-1] = internal_flux
        inventory_rate = self.area*(flux[:-1]-flux[1:])
        entropy_rate = -self.gas_constant*np.sum((np.log(concentrations/self.reference_concentration)+1)*inventory_rate, axis=1)
        production = -self.gas_constant*self.area*np.sum(internal_flux*jump, axis=1)
        entropy_parts = self.area*self.width*np.stack([
            np.sum(part*self.weights[None, :], axis=1) for part in [molecular, wall, darcy]], axis=1)
        return {'concentrations': concentrations, 'inventories': inventories, 'entropy': entropy,
            'partial_pressures': self.rt*concentrations, 'flux': internal_flux,
            'diffusive_flux': np.sum(diffusive_flux*self.weights[None, :, None], axis=1),
            'darcy_flux': np.sum(darcy_flux*self.weights[None, :, None], axis=1),
            'inventory_rate': inventory_rate, 'entropy_rate': entropy_rate,
            'production': production, 'path_production': np.sum(entropy_parts, axis=1),
            'entropy_parts': entropy_parts,
            'original_equation_residual_mol_m4': float(np.max(np.abs(residual)))}
