"""Record the restricted reactive gas pore with the same thermal integrator."""
from equilibrium_pore_setup import build
from run_thermal_spherical_pore import main


if __name__ == '__main__':
    main(build)
