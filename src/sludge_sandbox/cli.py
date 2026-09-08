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
    supervised.add_argument('operation', choices=('run', 'replay', 'resume'))
    supervised.add_argument('source', type=Path)
    supervised.add_argument('--job-directory', required=True, type=Path)
    supervised.add_argument('--water-data', type=Path)
    supervised.add_argument('--evidence-data', type=Path)
    supervised.add_argument('--wall-seconds', required=True, type=float)
    supervised.add_argument('--grace-seconds', default=5., type=float)
    for name, help_text in [('job-status', '读取保存的任务状态；不证明进程仍然存活'),
                            ('cancel-job', '提交取消请求；实际终止由持有进程的监督器确认')]:
        command = commands.add_parser(name, help=help_text)
        command.add_argument('job_directory', type=Path)
    commands.add_parser('resources', help='显示实现与依赖版本；不调用 EOS')
    ui = commands.add_parser('ui', help='启动仅监听本机的中文研究界面')
    ui.add_argument('--case', required=True, type=Path)
    ui.add_argument('--water-data', required=True, type=Path)
    ui.add_argument('--evidence-data', type=Path)
    ui.add_argument('--storage', required=True, type=Path)
    ui.add_argument('--port', type=int, default=8765)
    ui.add_argument('--maximum-jobs', type=int, default=20)
    args = parser.parse_args(argv)
    try:
        if args.command == 'ui':
            from .local_app import serve_local
            serve_local(case_path=args.case, water_directory=args.water_data,
                        evidence_directory=args.evidence_data, storage_directory=args.storage,
                        port=args.port, maximum_jobs=args.maximum_jobs)
            return 0
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
