from decimal import Decimal as D, localcontext
from pathlib import Path
import json
import unittest
from sludge_sandbox.water_coupled_rectangle import enclose_local_root, Interval

ROOT = Path(__file__).parent/'fixtures/water-interval-primitives-v1'
SHA = 'a10a0da6c55e623cccc1f56a70cb348c772d8fc1710a6a142b459abb0dec4586'


def parameters(radius):
    # Original saved native observation used only to select a numerical search
    # bracket. Uniform signs and derivative, not that seed, certify local roots.
    r = json.loads((ROOT/'saved-initial-forward.json').read_bytes())
    s = json.loads((ROOT/'saved-initial.json').read_bytes())[0]
    with localcontext() as c:
        c.prec = 60
        nl = D(s['liquid_water_mol'])
        rho = nl/D(r['fluid']['mechanical']['liquid_volume_m3'])
        available = D(.001)-sum((D(m)*D(v) for m,v in zip(s['solid_mass_kg'],(.001,.0005))),D(0))
        return dict(temperature=Interval(D('299.999999'),D('300.000001')),
            liquid_molar_density=Interval(rho-D(radius),rho+D(radius)),
            effective_available_volume=Interval(available-D('1e-17'),available+D('1e-17')),
            liquid_mol=nl,gas_mol=sum(map(D,s['gas_amounts_mol']),D(0)),
            gas_constant=D(r['fluid']['mechanical']['gas_constant_j_mol_k']),
            liquid_volume_scale=D(1))


class Coupled(unittest.TestCase):
    def test_original_tight_bracket_still_rejects(self):
        with self.assertRaisesRegex(ValueError,'uniform_root_face'):
            enclose_local_root(ROOT/'heos-water.json',SHA,**parameters('.01'))

    def test_explicit_wider_bracket_has_uniform_sign_and_compliance(self):
        p = parameters('.2')
        out = enclose_local_root(ROOT/'heos-water.json',SHA,**p)
        self.assertLess(out.lower_residual.hi,0)
        self.assertGreater(out.upper_residual.lo,0)
        self.assertGreater(out.liquid_pressure_derivative.lo,0)
        self.assertGreater(out.total_residual_derivative.lo,0)
        self.assertLess(out.pressure.hi-out.pressure.lo,D('.02'))
        # Native observation is a descriptive cross-check, not root evidence.
        native = D(json.loads((ROOT/'saved-initial-forward.json').read_bytes())['fluid']['mechanical']['pressure_pa'])
        self.assertLess(out.pressure.lo,native)
        self.assertLess(native,out.pressure.hi)


if __name__ == '__main__':
    unittest.main()
