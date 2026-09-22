"""Reconstruct control-volume geometry directly from recorded root inputs.

This review-side arithmetic does not import the runtime column construction.
The two schemas describe different physical models, not interchangeable meshes.
"""


def review_geometry(config, count):
    area = config['geometry']['area_m2']
    transfer = config['transfer']
    if config['schema'] == 'equilibrium_water_column_v1':
        bulk = count
        dx = config['geometry']['length_m']/bulk
        volumes = [area*dx]*count
        solids = [config['solid']['total_mol']/count]*count
        distances = [dx/2]*count
        conductivities = [transfer['conductivity_w_m_k']]*count
        wall_distance, wall_k = dx/2, transfer['conductivity_w_m_k']
        roles = ['bulk']*count
    elif config['schema'] == 'fixed_surface_storage_column_v1':
        storage = config['surface_storage']
        bulk = count-1
        dx = config['geometry']['length_m']/bulk
        volumes = [area*dx]*bulk+[storage['fluid_volume_m3']]
        solids = [config['solid']['total_mol']/bulk]*bulk+[storage['solid_mol']]
        distances = [dx/2]*bulk+[storage['contact_distance_m']]
        conductivities = [transfer['conductivity_w_m_k']]*bulk+[storage['conductivity_w_m_k']]
        wall_distance, wall_k = storage['wall_distance_m'], storage['conductivity_w_m_k']
        roles = ['bulk']*bulk+['surface_storage']
    else:
        raise ValueError('unknown spatial model schema: '+config['schema'])
    links = [dict(left_distance_m=distances[i], right_distance_m=distances[i+1],
                  left_conductivity_w_m_k=conductivities[i],
                  right_conductivity_w_m_k=conductivities[i+1]) for i in range(count-1)]
    links.append(dict(left_distance_m=wall_distance, right_distance_m=transfer['external_distance_m'],
                      left_conductivity_w_m_k=wall_k,
                      right_conductivity_w_m_k=transfer['external_conductivity_w_m_k']))
    return {'volumes_m3': volumes, 'solid_amounts_mol': solids, 'roles': roles,
            'bulk_cells': bulk, 'bulk_dx_m': dx, 'links': links,
            'wall_distance_m': wall_distance, 'wall_conductivity_w_m_k': wall_k}
