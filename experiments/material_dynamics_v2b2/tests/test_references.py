"""Independent references are checked algebraically before solver comparison."""
import importlib.util
import unittest
import math


class ReferenceTests(unittest.TestCase):
    def test_independent_closed_and_diffusion_oracles(self):
        self.assertIsNotNone(importlib.util.find_spec('reference.oracle'),'independent reference absent')
        from reference.oracle import sealed_state, exposure, diffusion_cell
        knots=[{'tau':0,'T_K':600},{'tau':20,'T_K':600}]
        h,trace=exposure(knots,20,1,6)
        self.assertAlmostEqual(h,20,places=12)
        self.assertTrue(trace[-1]['change']<=1e-9)
        for gamma in (.25,1,2):
            u,v,f=sealed_state(gamma,0)
            self.assertEqual((u,v,f),(1.,0.,1.))
            u,v,f=sealed_state(gamma,100)
            self.assertAlmostEqual(u+v,1,places=14)
            self.assertAlmostEqual(gamma*f+v,gamma,places=14)
        self.assertAlmostEqual(sealed_state(2,100)[2],.5,places=12)
        self.assertAlmostEqual(sealed_state(1,100)[2],1/101,places=14)
        self.assertAlmostEqual(diffusion_cell(31,0,20,128),1,places=12)

if __name__=='__main__': unittest.main()
