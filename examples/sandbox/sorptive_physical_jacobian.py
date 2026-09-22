"""Differentiate feedback states; construct nonfeedback ledger blocks exactly.

Uses the pinned SciPy BDF numerical-Jacobian routine for the physical block.
The exterior integrals do not enter any rate. Their columns are exactly zero,
and their derivative rows are minus the sum of matching cell-species/U rows.
"""
import numpy as np
import scipy
from scipy.integrate._ivp.common import num_jac
from scipy.optimize._numdiff import group_columns
from scipy.sparse import bmat, csc_matrix, lil_matrix


class PhysicalColumnJacobian:
    def __init__(self, rhs, cell_count, width, sparsity, atol, policy):
        self.rhs=rhs;self.count=cell_count*width;self.width=width
        self.structure=sparsity[:self.count,:self.count].tocsc()
        self.groups=group_columns(self.structure,order=policy['column_grouping_seed'])
        self.atol=atol[:self.count];self.factor=None;self.calls=0
        sums=lil_matrix((width,self.count))
        for i in range(cell_count):
            for k in range(width):
                sums[k,i*width+k]=1.
        self.sums=sums.tocsc()
        self.record={'policy':policy,'scipy_version':scipy.__version__,
            'feedback_variables':self.count,'nonfeedback_ledger_variables':width,
            'finite_difference_columns':self.count,
            'implementation':'Pinned scipy.integrate._ivp.common.num_jac and scipy.optimize._numdiff.group_columns; private API dependency recorded.',
            'ledger_derivative':'zero ledger columns; ledger rows = -sum of corresponding physical cell rows'}

    def __call__(self, at_time, vector):
        physical=vector[:self.count]
        baseline=self.rhs(at_time,vector)[:self.count]
        def vectorized(t, columns):
            return np.column_stack([self.rhs(t,np.concatenate((column,vector[self.count:])))[:self.count]
                                    for column in columns.T])
        block,self.factor=num_jac(vectorized,at_time,physical,baseline,self.atol,self.factor,
                                  (self.structure,self.groups))
        self.calls+=1
        return bmat([[block,csc_matrix((self.count,self.width))],
                     [-self.sums@block,csc_matrix((self.width,self.width))]],format='csc')
