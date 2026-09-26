"""Use the existing USGS thermal pore and molecular-flow source contracts."""
import json

from thermal_pore_setup import build as closed_build
from sludge_sandbox.effusive_spherical_pore import EffusiveSphericalPore


def build(root, settings):
    closed, sources = closed_build(root,settings)
    for name in ['effusion_source','molecular_source']:
        sources[name] = json.loads((root/settings[name]).read_text())
    return EffusiveSphericalPore(closed,settings['reservoir'],settings['connection'],
                                sources['molecular_source']),sources
