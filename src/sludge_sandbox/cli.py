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
    parser = argparse.ArgumentParser(description='烧结砖物理沙盒；当前入口仅支持明确标记的数值验证案例。')
    commands = parser.add_subparsers(dest='command', required=True)
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
    ui.add_argument('--case', required=True, type=Path)
    ui.add_argument('--water-data', required=True, type=Path)
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
                        port=args.port, maximum_jobs=args.maximum_jobs)
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
