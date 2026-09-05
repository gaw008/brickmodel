"""Independent coefficient and nonautonomous conservative-step tests."""
import importlib.util
import math
import unittest
from scenarios import expand_frozen_manifest
from model import Scenario


class CoefficientTests(unittest.TestCase):
    def test_coefficients_and_stage_times(self):
        self.assertIsNotNone(importlib.util.find_spec('temperature'), 'temperature implementation absent')
        from temperature import evaluate
        from solver import initial_state, step, conductance, euler
        cases = {s.id:s for s in expand_frozen_manifest()}
        for sid in ('W03','L02','C04','R01'):
            s = cases[sid]; d=s.to_dict(); knots=d['temperature']['knots']
            times = sorted(set([k['tau'] for k in knots]+[(a['tau']+b['tau'])/2 for a,b in zip(knots,knots[1:])]))
            for t in times:
                a,b = next((a,b) for a,b in zip(knots,knots[1:]) if a['tau']<=t<=b['tau'])
                T=a['T_K']+(b['T_K']-a['T_K'])*(t-a['tau'])/(b['tau']-a['tau'])
                k=d['reaction']['K_ref']*math.exp(d['reaction']['theta']*(1-600/T))
                diff=d['transport']['d_ref']*(T/600)**d['transport']['m']; ell=d['geometry']['length_ratio']
                expected=(T,k,diff,diff/ell**2,d['transport']['Bi_ref']/ell)
                c=evaluate(s,t)
                for actual, ref in zip((c.T_K,c.K,c.d,c.a_D,c.b),expected):
                    self.assertLessEqual(abs(actual-ref),1e-12*max(1,abs(ref)))
            with self.assertRaises(ValueError): evaluate(s,-.01)
            with self.assertRaises(ValueError): evaluate(s,20.01)
        s=cases['W03']; d=s.to_dict(); d['boundary']['mode']='sealed'; d['transport']['Bi_ref']=0
        s=Scenario.from_dict(d); state=initial_state(s); h=.0001; t=.75
        actual=step(s,state,t,h)
        k0=evaluate(s,t).K; k1=evaluate(s,t+h).K; gamma=2
        u1=1-h*gamma*k0; f1=1-h*k0
        u2=u1-h*gamma*k1*u1*f1; f2=f1-h*k1*u1*f1
        self.assertAlmostEqual(actual.u[0],(1+u2)/2,places=14)
        self.assertAlmostEqual(actual.f[0],(1+f2)/2,places=14)
        # Deliberately frozen stage-time formula is measurably different.
        self.assertGreater(abs(actual.f[0]-(1+f1-h*k0*u1*f1)/2),1e-10)
        self.assertAlmostEqual(actual.generated,2*(1-actual.f[0]),places=14)
        # Finite transfer is signed and conserves body+reservoir independently.
        s=cases['C03']; n=15; h=1e-5
        for body, exterior in ((.2,.8),(.8,.2)):
            state=initial_state(s); state.u=[body]*n; state.v=[1-body]*n; state.f=[0.0]*n
            state.u_res=exterior; state.v_res=1-exterior
            c=evaluate(s,1); g=conductance(c.a_D,c.b,1/n)
            nxt=euler(s,state,c,h,g)
            j=g*(body-exterior)
            self.assertLessEqual(abs(nxt.u_res-exterior-h*j/.25),1e-12)
            self.assertLessEqual(abs(sum(nxt.u)/n+.25*nxt.u_res-body-.25*exterior),1e-12)
            self.assertLessEqual(abs(sum(nxt.v)/n+.25*nxt.v_res-(1-body)-.25*(1-exterior)),1e-12)

if __name__=='__main__': unittest.main()
