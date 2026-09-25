"""Central local differences with explicit zero cumulative-ledger feedback.

Twelve independent groups evaluate two-sided perturbations. The dense total
entropy-production row is recovered from separate local face contributions,
so distant cells need not receive separate full-column perturbations.
"""
import math

import numpy as np
from scipy.integrate._ivp.common import num_jac
from scipy.sparse import bmat, csc_matrix, lil_matrix


class OpenColumnColoredJacobian:
    def __init__(self, column, numerics):
        self.column = column
        self.numerics = numerics

    def __call__(self, at, values):
        count, body = self.column.count, 4*self.column.count
        steps = np.empty(body)
        for i in range(count):
            steps[4*i:4*i+3] = (np.abs(values[4*i:4*i+3])
                                * self.numerics['inventory_relative_step'])
            steps[4*i+3] = self.numerics['temperature_step_k']
        matrix = lil_matrix((body+5, body+5))
        for group in range(3*4):
            columns = np.arange(group, body, 3*4)
            if not len(columns):
                continue
            plus, minus = values.copy(), values.copy()
            plus[columns] += steps[columns]
            minus[columns] -= steps[columns]
            rates_plus, parts_plus = self.column.rate_components(at, plus)
            rates_minus, parts_minus = self.column.rate_components(at, minus)
            difference, production_difference = rates_plus-rates_minus, parts_plus-parts_minus
            for index in columns:
                cell = index//4
                denominator = plus[index]-minus[index]
                begin, end = 4*max(0, cell-1), 4*min(count, cell+2)
                matrix[begin:end, index] = (difference[begin:end]/denominator).reshape(-1, 1)
                faces = list(range(max(0, cell-1), min(count-1, cell+1)))
                if cell == count-1:
                    faces.append(count-1)
                    for ledger in (0, 1, 3, 4):
                        matrix[body+ledger, index] = difference[body+ledger]/denominator
                matrix[body+2, index] = math.fsum(production_difference[face] for face in faces)/denominator
        return matrix.tocsc()


class OpenColumnAdaptiveBodyJacobian:
    """Use the established adaptive body differences; color the ledger pieces.

    The same SciPy num_jac backend already used by the temperature-column
    formulation operates only on physical coordinates here. Ledger zero
    columns are inserted explicitly and never enter its step adaptation.
    """
    def __init__(self, column, body_absolute_tolerances, ledger_numerics):
        self.column = column
        self.threshold = body_absolute_tolerances
        self.body_size = 4*column.count
        self.factor = None
        self.structure = column.numerical_jacobian_sparsity()[:self.body_size, :self.body_size]
        self.groups = np.arange(self.body_size) % (3*4)
        self.ledger_difference = OpenColumnColoredJacobian(column, ledger_numerics)

    def __call__(self, at, values):
        body_size = self.body_size
        rates = self.column.rates(at, values)

        def vectorized(time, columns):
            return np.column_stack([self.column.rates(time,
                np.concatenate((body, values[body_size:])))[:body_size] for body in columns.T])

        body, self.factor = num_jac(vectorized, at, values[:body_size], rates[:body_size],
            self.threshold, self.factor, (self.structure, self.groups))
        ledger = self.ledger_difference(at, values)[body_size:, :body_size]
        return bmat([[body, csc_matrix((body_size, 5))],
                     [ledger, csc_matrix((5, 5))]], format='csc')
