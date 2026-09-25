"""Original binary-viscosity H system within the independent DGM equations."""
import numpy as np

from dusty_gas_column_reference import ColumnReference


class KineticColumnReference(ColumnReference):
    def __init__(self, header):
        super().__init__(header)
        self.a_star = float(self.settings['mixture_viscosity']['cross_section_row']['A_star'])
        self.interaction = (self.products[0, 1]/self.rt
            / ((3/5)*(1/self.masses[0]+1/self.masses[1])*self.a_star))

    def mixture_viscosity(self, fractions):
        h = np.zeros((*fractions.shape[:-1], 2, 2))
        for i, j in [(0, 1), (1, 0)]:
            coefficient = (2*fractions[..., i]*fractions[..., j]*self.masses[i]*self.masses[j]
                / (self.interaction*(self.masses[i]+self.masses[j])**2))
            h[..., i, i] = (fractions[..., i]**2/self.viscosities[i]
                + coefficient*(5/(3*self.a_star)+self.masses[j]/self.masses[i]))
            h[..., i, j] = -coefficient*(5/(3*self.a_star)-1)
        response = np.linalg.solve(h, fractions[..., None])[..., 0]
        return np.sum(fractions*response, axis=-1)
