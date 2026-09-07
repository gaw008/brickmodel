"""Native-unit calls to the already source-verified Python IAPWS-95 backend.

This private dispatcher performs no physics, conversion, caching or validation.
The caller retains those responsibilities and supplies its current native objects
on every call, so replaced factories and faulty methods cannot evade validation.
No alternative backend is admitted by this module.
"""


class PythonIAPWS95Calls:
    """Stateless dispatch; never retain a factory or a mutable native model."""

    __slots__ = ()

    @staticmethod
    def solver_identity(backend):
        return backend.IAPWS95

    @staticmethod
    def solve(backend, **inputs):
        return backend.IAPWS95(**inputs)

    @staticmethod
    def helmholtz(model, density, temperature):
        return model._Helmholtz(density, temperature)

    @staticmethod
    def residual(model, tau, delta):
        return model._phir(tau, delta)

    @staticmethod
    def ideal(model, tau, delta):
        return model._phi0(tau, delta)
