"""JSON CLI backed by the same application service as Python clients."""
import argparse
import json
from pathlib import Path
import signal
from contextlib import contextmanager


@contextmanager
def _cancellation():
    requested = False

    def request(signum, frame):
        nonlocal requested
        requested = True

    previous = signal.signal(signal.SIGINT, request)
    try:
        yield lambda: requested
    finally:
        signal.signal(signal.SIGINT, previous)


def main(argv=None):
    parser = argparse.ArgumentParser(description='烧结砖物理沙盒；来源热化学计算与明确标记的数值验证案例。')
    commands = parser.add_subparsers(dest='command', required=True)
    desorption = commands.add_parser('arlabosse95', help='查询95°C原污泥离散活动度、总解吸热及相对摩尔化学势；无插值或动态模拟')
    desorption.add_argument('--source', required=True, type=Path, help='已审核arlabosse95/source.json')
    desorption.add_argument('--assets-root', required=True, type=Path, help='包含原图和来源记录的显式本地根目录')
    desorption.add_argument('--moisture', required=True, help='kg水/kg干物的已提取节点；十进制或分数')
    desorption.add_argument('--temperature', required=True, help='原95°C等温线对应的显式温度')
    desorption.add_argument('--unit', required=True, choices=('K', 'degC'))
    desorption.add_argument('--trace', action='store_true', help='附三项输出的来源依赖注册表')
    calcite = commands.add_parser('calcite-thermochemistry', help='按USGS原式计算纯方解石分解的温变反应焓和指定进度产气量')
    calcite.add_argument('--source-data', required=True, type=Path, help='含已核读facts.json与source.json的目录')
    calcite.add_argument('--temperature-k', required=True, help='显式开尔文温度，298.15至1200 K')
    calcite.add_argument('--extent-mol', default='1', help='指定消耗CaCO3的摩尔数；不代表模型预测的分解进度')
    char = commands.add_parser('char-oxidation-times', help='原文10%氧气条件下污泥预制焦的图示进度达时；不计算热量或氧耗')
    char.add_argument('--source-data', required=True, type=Path, help='含已核读training.json与source_metadata.json的目录')
    char.add_argument('--temperature-c', default='500', help='450至550°C的等温标签；内部温度未求解')
    char.add_argument('--alpha-plot', nargs='+', help='0.1至0.8的图示进度；默认八个预登记水平')
    validate = commands.add_parser('validate', help='校验案例结构；不调用 EOS，不证明材料有效性')
    validate.add_argument('case', type=Path)
    run = commands.add_parser('run', help='运行案例并保存原始输入与求解账本')
    run.add_argument('case', type=Path)
    run.add_argument('--water-data', required=True, type=Path)
    run.add_argument('--evidence-data', type=Path, help='公开方程证据目录；缺少的来源在图中保持 missing')
    run.add_argument('--output', required=True, type=Path)
    source_run = commands.add_parser('source-run', help='运行真实水物性/来源热容试算；当前几何与输运仍为数值验证设定')
    source_run.add_argument('case', type=Path)
    source_run.add_argument('--assets-root', required=True, type=Path, help='显式本地来源资产根目录；输出副本含不可公开再分发的来源缓存')
    source_run.add_argument('--output', required=True, type=Path)
    source_validate = commands.add_parser('source-validate', help='校验来源试算配置及显式资产；不运行物性')
    source_validate.add_argument('case', type=Path)
    source_validate.add_argument('--assets-root', type=Path)
    inspect = commands.add_parser('inspect', help='只读检查标准来源运行包；保留原观测与失败身份')
    inspect.add_argument('run_directory', type=Path)
    inspect.add_argument('--capture-index', type=int)
    inspect.add_argument('--cell', type=int)
    inspect.add_argument('--path', dest='value_path')
    inspect.add_argument('--capture-offset', type=int, default=0)
    inspect.add_argument('--capture-limit', type=int, default=50)
    export = commands.add_parser('export', help='导出标准来源运行包的原始规范记录；不含来源文件，不可单独重放')
    export.add_argument('run_directory', type=Path)
    export.add_argument('--output', type=Path, help='新文件；省略则输出到标准输出')
    trace = commands.add_parser('trace', help='查询保存结果的实现、参数与来源文件')
    trace.add_argument('run_directory', type=Path)
    trace.add_argument('--quantity', required=True)
    replay = commands.add_parser('replay', help='以相同实现从冻结输入重新运行；不会执行保存的代码')
    replay.add_argument('run_directory', type=Path)
    replay.add_argument('--output', required=True, type=Path)
    resume = commands.add_parser('resume', help='从已取消运行的最后接受步继续；保留原始预算和完整账本')
    resume.add_argument('run_directory', type=Path)
    resume.add_argument('--output', required=True, type=Path)
    supervised = commands.add_parser('supervise', help='监督整个运行进程，保存状态并限制总耗时')
    supervised.add_argument('operation', choices=('run', 'source-run', 'replay', 'resume'))
    supervised.add_argument('source', type=Path)
    supervised.add_argument('--job-directory', required=True, type=Path)
    supervised.add_argument('--water-data', type=Path)
    supervised.add_argument('--assets-root', type=Path)
    supervised.add_argument('--evidence-data', type=Path)
    supervised.add_argument('--wall-seconds', required=True, type=float)
    supervised.add_argument('--grace-seconds', default=5., type=float)
    for name, help_text in [('job-status', '读取保存的任务状态；不证明进程仍然存活'),
                            ('cancel-job', '提交取消请求；实际终止由持有进程的监督器确认')]:
        command = commands.add_parser(name, help=help_text)
        command.add_argument('job_directory', type=Path)
    commands.add_parser('resources', help='显示实现与依赖版本；不调用 EOS')
    source_import = commands.add_parser('source-observation-import',
        help='导入一条已保存来源观测；检验完整字段，不重跑物性或恢复整段运行')
    source_import.add_argument('capture_file', type=Path)
    source_import.add_argument('--capture-index', required=True, type=int, help='输入 captures 中从 0 开始的索引')
    source_import.add_argument('--output', required=True, type=Path)
    source_inspect = commands.add_parser('source-observation-inspect',
        help='查看已检验来源观测的状态和来源声明；不证明真实材料有效性')
    source_inspect.add_argument('record', type=Path)
    source_inspect.add_argument('--cell', type=int, help='可选的原空间格索引，从 0 开始')
    study_import = commands.add_parser('source-study-import',
        help='导入完整来源试算与事件证据；保留失败，不重跑物性或恢复实时模型')
    study_import.add_argument('study_file', type=Path)
    study_import.add_argument('--source-format', default='source_multicell_native_v1')
    study_import.add_argument('--output', required=True, type=Path)
    study_inspect = commands.add_parser('source-study-inspect',
        help='查询完整来源记录的阶段、原观测和校验范围')
    study_inspect.add_argument('record', type=Path)
    study_inspect.add_argument('--capture-index', type=int, help='原 captures 顺序中的索引，从 0 开始')
    study_inspect.add_argument('--cell', type=int, help='指定观测中的原空间格索引')
    study_inspect.add_argument('--path', dest='value_path',
        help='保存阶段的字段路径，例如 transition/cell_selected_pressure_gates')
    ui = commands.add_parser('ui', help='启动仅监听本机的中文研究界面')
    ui.add_argument('--case', type=Path)
    ui.add_argument('--water-data', type=Path)
    ui.add_argument('--view-source-run', type=Path, help='由启动者挂载一个已有标准来源运行包；浏览器仅可读')
    ui.add_argument('--evidence-data', type=Path)
    ui.add_argument('--storage', required=True, type=Path)
    ui.add_argument('--port', type=int, default=8765)
    ui.add_argument('--maximum-jobs', type=int, default=20)
    prepare = commands.add_parser('experiment-prepare', help='冻结候选、来源与实验预算；不调用 EOS')
    prepare.add_argument('spec', type=Path)
    prepare.add_argument('--water-data', required=True, type=Path)
    prepare.add_argument('--evidence-data', type=Path)
    prepare.add_argument('--output', required=True, type=Path)
    for name, help_text in [('experiment-run', '按累计预算执行或继续实验'),
                            ('experiment-status', '读取实验与候选保存状态'),
                            ('experiment-cancel', '提交绑定实验身份的取消请求'),
                            ('experiment-compare', '比较已验证结果；不生成产品合格排名')]:
        command = commands.add_parser(name, help=help_text)
        command.add_argument('directory', type=Path)
    sensitivity = commands.add_parser('sensitivity-prepare', help='冻结两水平因子实验；区分设计值与制造参数')
    sensitivity.add_argument('spec', type=Path)
    sensitivity.add_argument('--water-data', required=True, type=Path)
    sensitivity.add_argument('--evidence-data', type=Path)
    sensitivity.add_argument('--output', required=True, type=Path)
    analyze = commands.add_parser('sensitivity-analyze', help='从完整保存结果计算因子对比，不推断现实概率')
    analyze.add_argument('directory', type=Path)
    search = commands.add_parser('search-prepare', help='冻结多代搜索的目标、约束、变量与累计预算')
    search.add_argument('spec', type=Path)
    search.add_argument('--water-data', required=True, type=Path)
    search.add_argument('--evidence-data', type=Path)
    search.add_argument('--output', required=True, type=Path)
    for name in ('search-run', 'search-status'):
        command = commands.add_parser(name)
        command.add_argument('directory', type=Path)
    args = parser.parse_args(argv)
    try:
        if args.command in ('inspect', 'export'):
            from .source_run_view import inspect_source_run, export_source_run
            if args.command == 'inspect':
                value = inspect_source_run(args.run_directory, capture_index=args.capture_index,
                    cell_index=args.cell, value_path=args.value_path,
                    capture_offset=args.capture_offset, capture_limit=args.capture_limit)
            else:
                value = export_source_run(args.run_directory)
            text = json.dumps(value, ensure_ascii=False, allow_nan=False, indent=2)+'\n'
            if args.command == 'export' and args.output is not None:
                with args.output.open('x', encoding='utf-8') as stream:
                    stream.write(text)
                print(json.dumps({'status': 'exported', 'path': str(args.output),
                                  'scope': value.get('export_scope')}, ensure_ascii=False))
            else:
                print(text, end='')
            return 0
        if args.command == 'arlabosse95':
            from fractions import Fraction
            from .arlabosse_desorption95 import ArlabosseDesorption95, DesorptionError
            try:
                moisture, temperature = Fraction(args.moisture), Fraction(args.temperature)
            except (ValueError, ZeroDivisionError) as exc:
                raise DesorptionError('finite_decimal_or_fraction_input_required') from exc
            model = ArlabosseDesorption95(args.source, args.assets_root)
            point = model.at_moisture(moisture, temperature=temperature, unit=args.unit)
            value = {'point': point.to_record()}
            if args.trace:
                value['trace'] = model.registry_payload()
            print(json.dumps(value, ensure_ascii=False, allow_nan=False, indent=2))
            return 0
        if args.command == 'char-oxidation-times':
            from .nowicki_oxidation import calculate_nowicki_oxygen_times
            options = {'conversion_levels': args.alpha_plot} if args.alpha_plot is not None else {}
            value = calculate_nowicki_oxygen_times(args.source_data,
                temperature_c=args.temperature_c, **options)
            print(json.dumps(value, ensure_ascii=False, allow_nan=False, indent=2))
            return 0
        if args.command == 'calcite-thermochemistry':
            from .calcite_thermochemistry import calculate_calcite_thermochemistry
            value = calculate_calcite_thermochemistry(args.source_data,
                temperature_k=args.temperature_k, extent_mol=args.extent_mol)
            print(json.dumps(value, ensure_ascii=False, allow_nan=False, indent=2))
            return 0
        if args.command == 'source-validate':
            from .source_run_config import load_source_run_config, validate_source_run_assets
            from .source_run_service import _read
            config = load_source_run_config(_read(args.case, 1024 * 1024))
            assets = validate_source_run_assets(config, assets_root=args.assets_root) if args.assets_root else None
            value = dict(status='schema_valid', config_sha256=config.sha256,
                asset_manifest_sha256=assets.sha256 if assets else None,
                source_assets_checked=assets is not None, material_qualified=False)
            print(json.dumps(value, ensure_ascii=False, indent=2))
            return 0
        if args.command == 'source-run':
            from .source_run_service import run_source_case
            with _cancellation() as cancel:
                value = run_source_case(args.case, args.assets_root, args.output, cancel=cancel)
            summary = {key: value.get(key) for key in ('status', 'reason', 'case_sha256', 'scientific_status',
                'counts', 'source_record', 'numerical_comparison_completed', 'numerical_event_accepted',
                'material_qualified', 'full_firing_cycle')}
            summary['output'] = str(args.output.resolve())
            print(json.dumps(summary, ensure_ascii=False, allow_nan=False, indent=2))
            return 0 if value['status'] == 'completed' else 1
        if args.command in ('source-study-import', 'source-study-inspect'):
            from .source_study_service import import_source_study, inspect_source_study
            if args.command == 'source-study-import':
                value = import_source_study(args.study_file, args.output, source_format=args.source_format)
            else:
                value = inspect_source_study(args.record, capture_index=args.capture_index,
                    cell_index=args.cell, value_path=args.value_path)
            print(json.dumps(value, ensure_ascii=False, allow_nan=False, indent=2))
            return 0
        if args.command in ('source-observation-import', 'source-observation-inspect'):
            from .source_observation_service import import_source_capture, inspect_source_observation
            if args.command == 'source-observation-import':
                value = import_source_capture(args.capture_file, args.output, capture_index=args.capture_index)
            else:
                value = inspect_source_observation(args.record, cell_index=args.cell)
            print(json.dumps(value, ensure_ascii=False, allow_nan=False, indent=2))
            return 0
        if args.command.startswith('search-'):
            from .search import prepare_search, run_search, read_search
            if args.command == 'search-prepare':
                value = prepare_search(args.spec, args.output, water_directory=args.water_data,
                                       evidence_directory=args.evidence_data)
            elif args.command == 'search-run':
                with _cancellation() as cancel:
                    value = run_search(args.directory, cancel=cancel)
            else:
                value = read_search(args.directory)
            print(json.dumps(value, ensure_ascii=False, allow_nan=False, indent=2))
            return 1 if args.command == 'search-run' and value.get('status') != 'completed' else 0
        if args.command in ('sensitivity-prepare', 'sensitivity-analyze'):
            from .sensitivity import prepare_sensitivity, analyze_sensitivity
            if args.command == 'sensitivity-prepare':
                value = prepare_sensitivity(args.spec, args.output, water_directory=args.water_data,
                                            evidence_directory=args.evidence_data)
            else:
                value = analyze_sensitivity(args.directory)
            print(json.dumps(value, ensure_ascii=False, allow_nan=False, indent=2))
            return 0
        if args.command == 'ui':
            from .local_app import serve_local
            serve_local(case_path=args.case, water_directory=args.water_data,
                        evidence_directory=args.evidence_data, storage_directory=args.storage,
                        port=args.port, maximum_jobs=args.maximum_jobs, view_source_run=args.view_source_run)
            return 0
        if args.command.startswith('experiment-'):
            from .experiments import (prepare_experiment, run_experiment, read_experiment,
                                      request_experiment_cancel, compare_experiment)
            if args.command == 'experiment-prepare':
                value = prepare_experiment(args.spec, args.output, water_directory=args.water_data,
                                           evidence_directory=args.evidence_data)
            elif args.command == 'experiment-run':
                with _cancellation() as cancel:
                    value = run_experiment(args.directory, cancel=cancel)
            else:
                operation = {'experiment-status': read_experiment,
                             'experiment-cancel': request_experiment_cancel,
                             'experiment-compare': compare_experiment}[args.command]
                value = operation(args.directory)
            print(json.dumps(value, ensure_ascii=False, allow_nan=False, indent=2))
            return 1 if args.command == 'experiment-run' and value.get('status') != 'completed' else 0
        from .run_service import run_case, trace_run, replay_run, resume_run, runtime_identity
        if args.command == 'validate':
            from .verification_case import read_case
            case = read_case(args.case)
            value = {'status': 'schema_valid', 'case_id': case.case_id,
                     'case_sha256': case.sha256, 'material_qualified': False,
                     'source_assets': 'not_checked', 'scientific_status': 'manufactured_verification_only'}
        elif args.command == 'run':
            with _cancellation() as cancel:
                value = run_case(args.case, args.water_data, args.output, cancel=cancel,
                                 evidence_directory=args.evidence_data)
        elif args.command == 'trace':
            value = trace_run(args.run_directory, args.quantity)
        elif args.command == 'replay':
            with _cancellation() as cancel:
                value = replay_run(args.run_directory, args.output, cancel=cancel)
        elif args.command == 'resume':
            with _cancellation() as cancel:
                value = resume_run(args.run_directory, args.output, cancel=cancel)
        elif args.command == 'supervise':
            from .job_supervisor import supervise, SupervisionPolicy
            with _cancellation() as cancel:
                value = supervise(args.operation, args.source, args.job_directory,
                                  SupervisionPolicy(args.wall_seconds, args.grace_seconds),
                                  water_directory=args.water_data,
                                  assets_root=args.assets_root,
                                  evidence_directory=args.evidence_data, cancel=cancel)
        elif args.command in ('job-status', 'cancel-job'):
            from .job_supervisor import read_job, request_cancel
            value = (read_job if args.command == 'job-status' else request_cancel)(args.job_directory)
        else:
            value = runtime_identity()
        if args.command in ('run', 'replay', 'resume'):
            # Full results, including accepted prefixes, are in result.json.
            value = {key: value.get(key) for key in ('status', 'reason', 'case_sha256', 'scientific_status')}
            value['output'] = str(args.output.resolve())
        print(json.dumps(value, ensure_ascii=False, allow_nan=False, indent=2))
        return 1 if args.command in ('run', 'replay', 'resume', 'supervise') and value.get('status') != 'completed' else 0
    except (ValueError, OSError) as exc:
        print(json.dumps({'status': 'failed', 'error_type': type(exc).__name__,
                          'code': getattr(exc, 'code', None), 'reason': str(exc)}, ensure_ascii=False))
        return 1


if __name__ == '__main__':
    raise SystemExit(main())
