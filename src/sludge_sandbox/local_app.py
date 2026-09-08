"""Loopback-only browser boundary over the shared, bounded job supervisor.

Startup paths are trusted operator configuration, never browser parameters.
Persisted observations and owned Python-worker liveness are separate facts.
This interface provides manufactured verification, not material admission.
"""
from __future__ import annotations

from dataclasses import dataclass
import hashlib
import hmac
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
import json
import math
from pathlib import Path, PurePosixPath
import secrets
import threading
from typing import Any
from urllib.parse import parse_qs, urlsplit
import uuid

from .job_supervisor import SupervisionPolicy, read_job, request_cancel, supervise
from .run_service import read_run, trace_run
from .verification_case import read_case

_MAX_BYTES = 1024*1024
_UNKNOWN = [
    '当前仅为明确标记的制造验证案例，A/B 固相、反应动力学、载气和输运系数没有真实污泥材料准入证据。',
    '变形是预先规定的运动，不是由自由烧结或应力平衡预测的收缩。',
    '目前不覆盖完整烧制周期、真实窑炉边界和成品强度预测；结果不能作为生产控制或训练合格数据。',
    '水物性具有来源绑定，但案例误差包络不等于实验置信区间。']


class LocalAppError(ValueError):
    def __init__(self, reason: str, status: int = 400) -> None:
        super().__init__(reason)
        self.status = status


def _uuid(value: str) -> str:
    try:
        if str(uuid.UUID(value)) != value:
            raise ValueError
    except (ValueError, AttributeError, TypeError) as exc:
        raise LocalAppError('invalid_job_id', 404) from exc
    return value


def _pairs(pairs: list[tuple[str, Any]]) -> dict[str, Any]:
    result: dict[str, Any] = {}
    for key, value in pairs:
        if key in result:
            raise LocalAppError('duplicate_json_key')
        result[key] = value
    return result


def _nonfinite(value: str) -> None:
    raise LocalAppError('nonfinite_json_number')


def _json_float(value: str) -> float:
    number = float(value)
    if not math.isfinite(number):
        raise LocalAppError('nonfinite_json_number')
    return number


def _positive(value: Any, maximum: float, name: str) -> float:
    try:
        valid = type(value) in (int, float) and math.isfinite(value) and 0 < value <= maximum
    except OverflowError:
        valid = False
    if not valid:
        raise LocalAppError('invalid_'+name)
    return float(value)


@dataclass
class _OwnedWorker:
    directory: Path
    cancel: threading.Event
    thread: threading.Thread | None = None
    error: str | None = None


class JobManager:
    def __init__(self, *, case_path: str | Path, water_directory: str | Path,
                 evidence_directory: str | Path | None, storage_directory: str | Path,
                 maximum_jobs: int) -> None:
        if type(maximum_jobs) is not int or maximum_jobs < 1:
            raise LocalAppError('invalid_maximum_jobs')
        self.case = read_case(case_path)
        self.water_directory = Path(water_directory).resolve()
        self.evidence_directory = None if evidence_directory is None else Path(evidence_directory).resolve()
        self.storage_directory = Path(storage_directory).resolve()
        self.storage_directory.mkdir(parents=True, exist_ok=True)
        self.jobs_directory = self.storage_directory/'jobs'
        self.cases_directory = self.storage_directory/'cases'
        for path in (self.jobs_directory, self.cases_directory):
            if path.is_symlink():
                raise LocalAppError('invalid_storage_subdirectory')
            path.mkdir(exist_ok=True)
        self.maximum_jobs = maximum_jobs
        self._lock = threading.RLock()
        self._workers: dict[str, _OwnedWorker] = {}
        self._closing = False

    def config(self) -> dict[str, Any]:
        return {'case': self.case.payload, 'case_sha256': self.case.sha256,
                'scientific_status': 'manufactured_verification_only',
                'material_qualified': False, 'unknowns': list(_UNKNOWN),
                'maximum_jobs': self.maximum_jobs}

    def _ids(self) -> list[str]:
        ids = set(self._workers)
        for path in self.jobs_directory.iterdir():
            if not path.is_dir() or path.is_symlink():
                continue
            try:
                ids.add(_uuid(path.name))
            except LocalAppError:
                continue
        return sorted(ids)

    def _directory(self, identifier: str) -> Path:
        identifier = _uuid(identifier)
        directory = self.jobs_directory/identifier
        if directory.is_symlink() or (identifier not in self._workers and not directory.is_dir()):
            raise LocalAppError('job_not_found', 404)
        return directory

    def _observation(self, identifier: str) -> dict[str, Any]:
        directory = self._directory(identifier)
        worker = self._workers.get(identifier)
        active = bool(worker and worker.thread and worker.thread.is_alive())
        error = worker.error if worker else None
        job = None
        try:
            job = read_job(directory)
        except ValueError as exc:
            if not active or (directory/'job.json').exists():
                error = str(exc)
        return {'id': identifier, 'job': job, 'owned_worker_active': active, 'error': error}

    def list_jobs(self) -> dict[str, Any]:
        with self._lock:
            return {'jobs': [self._observation(identifier) for identifier in self._ids()]}

    def detail(self, identifier: str) -> dict[str, Any]:
        with self._lock:
            result = self._observation(identifier)
            directory = self._directory(identifier)
        result['result'] = None
        if (directory/'run'/'manifest.json').is_file():
            try:
                result['result'], _ = read_run(directory/'run')
            except ValueError as exc:
                result['error'] = str(exc)
        return result

    def _save_case(self, payload: Any, *, retain: bool) -> tuple[Path, str]:
        if type(payload) is not dict:
            raise LocalAppError('case_object_required')
        path = self.cases_directory/(str(uuid.uuid4())+'.json')
        valid = False
        try:
            raw = (json.dumps(payload, ensure_ascii=False, allow_nan=False, indent=2)+'\n').encode()
            if len(raw) > _MAX_BYTES:
                raise LocalAppError('case_too_large', 413)
            with path.open('xb') as stream:
                stream.write(raw)
            case = read_case(path)
            valid = True
            return path, case.sha256
        finally:
            if not retain or not valid:
                path.unlink(missing_ok=True)

    def validate(self, payload: Any) -> dict[str, str]:
        _, digest = self._save_case(payload, retain=False)
        return {'status': 'schema_valid', 'case_sha256': digest}

    def launch(self, payload: dict[str, Any]) -> dict[str, str]:
        if set(payload) != {'case', 'wall_seconds', 'grace_seconds'}:
            raise LocalAppError('invalid_job_fields')
        policy = SupervisionPolicy(_positive(payload['wall_seconds'], 120, 'wall_seconds'),
                                   _positive(payload['grace_seconds'], 5, 'grace_seconds'))
        with self._lock:
            self._available()
            path: Path | None = None
            try:
                path, _ = self._save_case(payload['case'], retain=True)
                return self._launch('run', path, policy)
            except BaseException:
                if path is not None:
                    path.unlink(missing_ok=True)
                raise

    def continue_job(self, identifier: str, operation: str) -> dict[str, str]:
        if operation not in ('replay', 'resume'):
            raise LocalAppError('invalid_operation')
        with self._lock:
            self._available()
            directory = self._directory(identifier)
            read_run(directory/'run')
            return self._launch(operation, directory/'run', SupervisionPolicy(120, 5))

    def _available(self) -> None:
        if self._closing:
            raise LocalAppError('server_shutting_down', 503)
        if any(worker.thread and worker.thread.is_alive() for worker in self._workers.values()):
            raise LocalAppError('owned_worker_busy', 409)
        if len(self._ids()) >= self.maximum_jobs:
            raise LocalAppError('maximum_jobs_reached', 409)

    def _launch(self, operation: str, source: Path, policy: SupervisionPolicy) -> dict[str, str]:
        identifier = str(uuid.uuid4())
        worker = _OwnedWorker(self.jobs_directory/identifier, threading.Event())

        def work() -> None:
            try:
                kwargs: dict[str, Any] = {'cancel': worker.cancel.is_set}
                if operation == 'run':
                    kwargs.update(water_directory=self.water_directory,
                                  evidence_directory=self.evidence_directory)
                supervise(operation, source, worker.directory, policy, **kwargs)
            except BaseException as exc:
                with self._lock:
                    worker.error = type(exc).__name__+': '+str(exc)

        worker.thread = threading.Thread(target=work, name='sandbox-job-'+identifier, daemon=False)
        self._workers[identifier] = worker
        try:
            worker.thread.start()
        except BaseException:
            del self._workers[identifier]
            raise
        return {'id': identifier}

    def cancel_job(self, identifier: str) -> dict[str, Any]:
        with self._lock:
            directory = self._directory(identifier)
            worker = self._workers.get(identifier)
            active = bool(worker and worker.thread and worker.thread.is_alive())
            if active:
                worker.cancel.set()
            if (directory/'job.json').is_file():
                request = request_cancel(directory)
            elif active:
                request = {'status': 'owned_worker_cancel_event_set_before_job_record'}
            else:
                raise LocalAppError('job_record_unavailable', 409)
            return {'id': identifier, 'request': request, 'owned_worker_active': active}

    def export(self, identifier: str) -> dict[str, Any]:
        with self._lock:
            directory = self._directory(identifier)
        result, manifest = read_run(directory/'run')
        return {'result': result, 'manifest': manifest}

    def trace(self, identifier: str, quantity: str) -> dict[str, Any]:
        with self._lock:
            directory = self._directory(identifier)
        return trace_run(directory/'run', quantity)

    def artifact(self, identifier: str, name: str) -> dict[str, str]:
        with self._lock:
            directory = self._directory(identifier)/'run'
        _, manifest = read_run(directory)
        relative = PurePosixPath(name)
        if (not name or relative.is_absolute() or '..' in relative.parts or '\\' in name or
                str(relative) != name or name not in manifest['files']):
            raise LocalAppError('artifact_not_recorded', 404)
        path = directory/name
        if path.is_symlink() or not path.resolve().is_relative_to(directory.resolve()):
            raise LocalAppError('invalid_artifact_path')
        if path.stat().st_size > _MAX_BYTES:
            raise LocalAppError('artifact_too_large', 413)
        with path.open('rb') as stream:
            raw = stream.read(_MAX_BYTES+1)
        if len(raw) > _MAX_BYTES:
            raise LocalAppError('artifact_too_large', 413)
        digest = hashlib.sha256(raw).hexdigest()
        if digest != manifest['files'][name]:
            raise LocalAppError('artifact_changed_after_verification', 409)
        try:
            text = raw.decode('utf-8')
        except UnicodeDecodeError as exc:
            raise LocalAppError('artifact_is_not_utf8_text', 415) from exc
        return {'path': name, 'text': text, 'sha256': digest}

    def close(self) -> None:
        with self._lock:
            self._closing = True
            workers = list(self._workers.values())
            for worker in workers:
                worker.cancel.set()
        # Only one owned worker can run. Its supervisor owns SIGINT/kill/reap.
        for worker in workers:
            if worker.thread is not None:
                worker.thread.join(timeout=126)
                if worker.thread.is_alive():
                    raise LocalAppError('owned_worker_shutdown_not_confirmed', 503)


class LocalServer(ThreadingHTTPServer):
    daemon_threads = True
    manager: JobManager
    token: str
    _serving_thread: int | None = None

    def serve_forever(self, poll_interval: float = 0.1) -> None:
        self._serving_thread = threading.get_ident()
        try:
            super().serve_forever(poll_interval=poll_interval)
        finally:
            self._serving_thread = None

    def server_close(self) -> None:
        try:
            manager = getattr(self, 'manager', None)
            if manager is not None:
                manager.close()
        finally:
            super().server_close()

    def close(self) -> None:
        if self._serving_thread is not None and self._serving_thread != threading.get_ident():
            self.shutdown()
        self.server_close()


class _Handler(BaseHTTPRequestHandler):
    server: LocalServer
    protocol_version = 'HTTP/1.0'

    def setup(self) -> None:
        super().setup()
        self.connection.settimeout(10.0)

    def log_message(self, format: str, *args: Any) -> None:
        # Avoid writing query/token-bearing browser input to a shared terminal.
        return

    def _send(self, status: int, raw: bytes, content_type: str) -> None:
        self.send_response(status)
        self.send_header('Content-Type', content_type)
        self.send_header('Content-Length', str(len(raw)))
        self.send_header('Cache-Control', 'no-store')
        self.send_header('X-Content-Type-Options', 'nosniff')
        self.send_header('Referrer-Policy', 'no-referrer')
        self.send_header('Content-Security-Policy', "default-src 'self'; script-src 'self'; style-src 'self'; connect-src 'self'; img-src 'self'; object-src 'none'; base-uri 'none'; frame-ancestors 'none'")
        self.end_headers()
        self.wfile.write(raw)

    def _json(self, status: int, value: Any) -> None:
        self._send(status, json.dumps(value, ensure_ascii=False, allow_nan=False).encode(),
                   'application/json; charset=utf-8')

    def _guard(self, *, api: bool) -> None:
        host = '127.0.0.1:'+str(self.server.server_port)
        if self.headers.get_all('Host', []) != [host]:
            raise LocalAppError('invalid_host', 403)
        origins = self.headers.get_all('Origin', [])
        if origins and origins != ['http://'+host]:
            raise LocalAppError('invalid_origin', 403)
        if api:
            tokens = self.headers.get_all('X-Sandbox-Token', [])
            if len(tokens) != 1 or not hmac.compare_digest(tokens[0].encode(), self.server.token.encode()):
                raise LocalAppError('invalid_token', 403)

    def _body(self) -> dict[str, Any]:
        lengths = self.headers.get_all('Content-Length', [])
        if self.headers.get_all('Transfer-Encoding', []) or len(lengths) != 1:
            raise LocalAppError('content_length_required')
        try:
            length = int(lengths[0])
        except ValueError as exc:
            raise LocalAppError('invalid_content_length') from exc
        if length < 0 or length > _MAX_BYTES:
            raise LocalAppError('request_too_large', 413)
        if self.headers.get_content_type() != 'application/json':
            raise LocalAppError('json_content_type_required', 415)
        raw = self.rfile.read(length)
        if len(raw) != length:
            raise LocalAppError('incomplete_request')
        try:
            value = json.loads(raw, object_pairs_hook=_pairs, parse_constant=_nonfinite,
                               parse_float=_json_float)
        except (ValueError, UnicodeDecodeError, RecursionError) as exc:
            raise LocalAppError('invalid_json') from exc
        if type(value) is not dict:
            raise LocalAppError('json_object_required')
        return value

    def _route(self, method: str) -> None:
        parsed = urlsplit(self.path)
        if parsed.scheme or parsed.netloc or parsed.fragment:
            raise LocalAppError('invalid_request_target')
        path = parsed.path
        api = path.startswith('/api/')
        self._guard(api=api)
        if not api:
            assets = {'/': ('index.html', 'text/html; charset=utf-8'),
                      '/index.html': ('index.html', 'text/html; charset=utf-8'),
                      '/app.js': ('app.js', 'text/javascript; charset=utf-8'),
                      '/app.css': ('app.css', 'text/css; charset=utf-8')}
            if method != 'GET' or path not in assets or parsed.query:
                raise LocalAppError('not_found', 404)
            filename, content_type = assets[path]
            raw = (Path(__file__).parent/'assets'/filename).read_bytes()
            if filename == 'index.html':
                raw = raw.replace(b'__APP_TOKEN__', self.server.token.encode())
            self._send(200, raw, content_type)
            return
        query = parse_qs(parsed.query, keep_blank_values=True, strict_parsing=True)
        manager = self.server.manager
        body = self._body() if method == 'POST' else None
        if path == '/api/config' and method == 'GET' and not query:
            value = manager.config()
        elif path == '/api/jobs' and method == 'GET' and not query:
            value = manager.list_jobs()
        elif path == '/api/validate' and method == 'POST' and not query:
            if set(body) != {'case'}:
                raise LocalAppError('invalid_validation_fields')
            value = manager.validate(body['case'])
        elif path == '/api/jobs' and method == 'POST' and not query:
            value = manager.launch(body)
        else:
            parts = path.split('/')
            if len(parts) not in (4, 5) or parts[:3] != ['', 'api', 'jobs']:
                raise LocalAppError('not_found', 404)
            identifier = _uuid(parts[3])
            action = parts[4] if len(parts) == 5 else None
            if action is None and method == 'GET' and not query:
                value = manager.detail(identifier)
            elif action in ('cancel', 'replay', 'resume') and method == 'POST' and not query and body == {}:
                value = manager.cancel_job(identifier) if action == 'cancel' else manager.continue_job(identifier, action)
            elif action == 'export' and method == 'GET' and not query:
                value = manager.export(identifier)
            elif action in ('trace', 'artifact') and method == 'GET':
                key = 'quantity' if action == 'trace' else 'path'
                if set(query) != {key} or len(query[key]) != 1:
                    raise LocalAppError('invalid_query')
                value = manager.trace(identifier, query[key][0]) if action == 'trace' else manager.artifact(identifier, query[key][0])
            else:
                raise LocalAppError('not_found', 404)
        self._json(200, value)

    def _handle(self, method: str) -> None:
        try:
            self._route(method)
        except (ValueError, OSError, RecursionError) as exc:
            self._json(getattr(exc, 'status', 400), {'status': 'failed',
                       'reason': str(exc), 'error_type': type(exc).__name__,
                       'code': getattr(exc, 'code', None)})

    def do_GET(self) -> None:
        self._handle('GET')

    def do_POST(self) -> None:
        self._handle('POST')


def make_server(*, case_path: str | Path, water_directory: str | Path,
                storage_directory: str | Path, evidence_directory: str | Path | None = None,
                port: int = 0, maximum_jobs: int = 20) -> LocalServer:
    if type(port) is not int or not 0 <= port <= 65535:
        raise LocalAppError('invalid_port')
    manager = JobManager(case_path=case_path, water_directory=water_directory,
                         evidence_directory=evidence_directory, storage_directory=storage_directory,
                         maximum_jobs=maximum_jobs)
    server = LocalServer(('127.0.0.1', port), _Handler)
    server.manager = manager
    server.token = secrets.token_hex(32)
    return server


def close_server(server: LocalServer) -> None:
    """Cancel/reap owned work and close sockets after stopping serve_forever."""
    server.close()


def serve_local(**kwargs: Any) -> None:
    server = make_server(**kwargs)
    print('http://127.0.0.1:'+str(server.server_port), flush=True)
    try:
        server.serve_forever(poll_interval=0.1)
    finally:
        server.close()
