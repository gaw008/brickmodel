"""Controlled local CLI path policy (not a hostile concurrent upload service)."""
from pathlib import Path, PurePosixPath
import stat
from model import ROOT


def checked_path(name):
    if not isinstance(name,(str,Path)): raise ValueError('path_type')
    raw=str(name); parts=PurePosixPath(raw).parts
    if not raw or raw.startswith('/') or '\\' in raw or ':' in raw or '..' in parts or not parts:
        raise ValueError('path_rejected')
    p=ROOT
    for component in parts:
        p=p/component
        if p.is_symlink(): raise ValueError('path_symlink')
    if not p.resolve().is_relative_to(ROOT): raise ValueError('path_escape')
    return p


def safe_file(name):
    p=checked_path(name)
    if not p.exists() or not stat.S_ISREG(p.stat().st_mode): raise ValueError('path_not_regular')
    return p


def safe_directory(name):
    p=checked_path(name)
    if not p.is_dir(): raise ValueError('path_not_directory')
    return p


def new_directory(name):
    p=checked_path(name)
    if p.exists(): raise ValueError('output_exists')
    p.mkdir(parents=True,exist_ok=False)
    return p


def relative(p): return str(p.relative_to(ROOT))
