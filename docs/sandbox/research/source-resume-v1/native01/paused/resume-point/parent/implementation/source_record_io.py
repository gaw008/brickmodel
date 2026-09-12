"""Shared bounded file reads and exclusive publication for source evidence."""
import os
from pathlib import Path
import stat
import tempfile


def read_record_bytes(path, limit, *, size_reason, regular_reason):
    """Read a regular file within a byte limit, without blocking on a FIFO."""
    descriptor = os.open(Path(path), os.O_RDONLY | os.O_NONBLOCK)
    try:
        opened = os.fstat(descriptor)
        if not stat.S_ISREG(opened.st_mode):
            raise ValueError(regular_reason)
        if opened.st_size > limit:
            raise ValueError(size_reason)
        with os.fdopen(descriptor, 'rb', closefd=False) as stream:
            raw = stream.read(limit + 1)
    finally:
        os.close(descriptor)
    if len(raw) > limit:
        raise ValueError(size_reason)
    return raw


def publish_record_bytes(path, raw, *, temporary_prefix):
    """Publish a completed file exclusively; never replace an existing output."""
    path = Path(path)
    temporary = None
    try:
        with tempfile.NamedTemporaryFile(mode='wb', dir=path.parent,
                                         prefix=temporary_prefix, delete=False) as stream:
            temporary = Path(stream.name)
            stream.write(raw)
            stream.flush()
            os.fsync(stream.fileno())
        os.link(temporary, path)
    finally:
        if temporary is not None:
            temporary.unlink(missing_ok=True)
