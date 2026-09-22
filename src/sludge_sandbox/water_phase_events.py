"""Locate resolved phase crossings on one numerical trajectory segment.

The signed criterion is the equilibrium partition's all-vapor pressure excess,
not actual wet-state supersaturation. Nodes can miss touching roots or an even
number of crossings between them; caller-specified scanning and ODE refinement
are reported separately from bisection precision. No state is modified here.
"""
def phase_scores(points):
    cells = [p['all_vapor_pressure_departure_pa'] for p in points]
    return [*cells, max(cells)]


def locate_crossings(evaluate_score, left_time, right_time, left_scores, right_scores, policy):
    """Return cell and column transitions bracketed by these two sample nodes.

    evaluate_score(t, index) returns one scalar. The final index is max(cell scores),
    so its transition describes the presence of liquid anywhere in the column.
    Bisection bounds the crossing of this numerical interpolant only.
    """
    crossings = []
    for index, (first, last) in enumerate(zip(left_scores, right_scores, strict=True)):
        if (first > 0) == (last > 0):
            continue
        left, right, fl, fr = left_time, right_time, first, last
        iterations = 0
        while right-left > policy['absolute_time_tolerance_s']:
            if iterations == policy['maximum_iterations']:
                raise RuntimeError('phase-event bisection did not reach its time tolerance')
            midpoint = (left+right)/2
            fm = evaluate_score(midpoint, index)
            if (fm > 0) == (fl > 0):
                left, fl = midpoint, fm
            else:
                right, fr = midpoint, fm
            iterations += 1
        time = (left+right)/2
        crossings.append({
            'scope': 'column' if index == len(left_scores)-1 else 'cell',
            'cell_index': None if index == len(left_scores)-1 else index,
            'transition': 'liquid_depleted' if first > 0 else 'liquid_appeared',
            'time_s': time, 'time_bracket_s': [left, right],
            'criterion_bracket_pa': [fl, fr],
            'initial_detection_bracket_s': [left_time, right_time],
            'bisection_iterations': iterations,
            'criterion_at_reported_time_pa': evaluate_score(time, index),
        })
    return sorted(crossings, key=lambda e: e['time_s'])
