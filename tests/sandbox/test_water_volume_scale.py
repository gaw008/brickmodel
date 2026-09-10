from decimal import Decimal as D
from unittest.mock import patch
import unittest
from sludge_sandbox.water_interval_eos import Interval, I
from sludge_sandbox.water_coupled_rectangle import enclose_local_root


class VolumeScale(unittest.TestCase):
    def test_nonunit_scale_changes_the_root_without_changing_gas_moles(self):
        # Independent analytic model p_liquid=rho, T=Ng=Rg=Nl=V=1:
        # rho*(1-scale/rho)=1 implies rho=1+scale.
        def analytic(source, sha, temperature, rho, **kw):
            return rho, I(1)
        with patch('sludge_sandbox.water_coupled_rectangle.pressure_interval',analytic):
            result=enclose_local_root('unused','analytic',temperature=I(1),
                liquid_molar_density=Interval(D('1.4'),D('1.6')),
                effective_available_volume=I(1),liquid_mol=1,gas_mol=1,
                gas_constant=1,liquid_volume_scale=D('.5'))
        self.assertLess(result.pressure.lo,D('1.5'))
        self.assertGreater(result.pressure.hi,D('1.5'))
        self.assertLess(result.pressure.hi,D(2))
        self.assertGreater(result.total_residual_derivative.lo,D(1))

    def test_scale_is_explicit_positive_input(self):
        inputs=dict(temperature=I(1),liquid_molar_density=Interval(D(2),D(3)),
            effective_available_volume=I(1),liquid_mol=1,gas_mol=1,gas_constant=1)
        with self.assertRaises(TypeError):
            enclose_local_root('unused','unused',**inputs)
        with self.assertRaises(ValueError):
            enclose_local_root('unused','unused',liquid_volume_scale=0,**inputs)


if __name__=='__main__':
    unittest.main()
