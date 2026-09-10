def test_active_chemical_core_and_dry_policy_match_pre_admission_source():
    """Static regression complements no-EOS tests; does not simulate active water."""
    import ast
    from pathlib import Path
    root=Path(__file__).resolve().parents[2]
    import sludge_sandbox.water_phase_transfer as actual_module
    def cls(path):return next(x for x in ast.parse(path.read_text()).body if isinstance(x,ast.ClassDef) and x.name=='WaterPhaseTransfer')
    before=cls(root/'docs/sandbox/research/deforming-wet-admission/baseline/water_phase_transfer.py')
    after=cls(Path(actual_module.__file__))
    def method(c,name):return next(x for x in c.body if isinstance(x,ast.FunctionDef) and x.name==name)
    # evaluate and dry chemistry are wholly unchanged: exact AST, including
    # source direction/zero-vapor/finite chemistry/heat-free component forwarding.
    for name in ('evaluate','_dry_diagnostic','with_depleted_cells'):
        assert ast.dump(method(before,name),include_attributes=False)==ast.dump(method(after,name),include_attributes=False)
    def matching_loop(c):
        constructor=method(c,'__post_init__')
        return next(x for x in constructor.body if isinstance(x,ast.For) and isinstance(x.target,ast.Tuple)
                    and [t.id for t in x.target.elts]==['storage','k','mode'])
    assert ast.dump(matching_loop(before),include_attributes=False)==ast.dump(matching_loop(after),include_attributes=False)
