"""Immutable Git evidence store, separate from the current development tree."""
from contextlib import contextmanager
import hashlib
import io
import os
from pathlib import Path
import subprocess
import tempfile

HISTORICAL_REVISION = '879d15b8fa267010217d9310b72d1066fda74f99'
HISTORICAL_TREE = 'b9d324aac007ddb663984151bb1a5081a22001cf'


def environment():
    env = os.environ.copy()
    for key in ('PYTHONPATH', 'PYTHONHOME', 'LOGICWRITE_CORE_CODE_ROOT',
                'GIT_DIR', 'GIT_WORK_TREE', 'GIT_INDEX_FILE', 'GIT_OBJECT_DIRECTORY',
                'GIT_ALTERNATE_OBJECT_DIRECTORIES'):
        env.pop(key, None)
    env['PYTHONDONTWRITEBYTECODE'] = '1'
    return env


def digest(raw):
    return hashlib.sha256(raw).hexdigest()


class EvidenceStore:
    def __init__(self, repository):
        self.repository = Path(repository).resolve()
        tree = self.git('rev-parse', HISTORICAL_REVISION + '^{tree}').decode().strip()
        if tree != HISTORICAL_TREE:
            raise ValueError('historical tree identity mismatch')
        listing = self.git('ls-tree', '-rz', '--full-tree', HISTORICAL_REVISION)
        objects = []
        for record in listing.split(b'\0'):
            if not record:
                continue
            meta, path = record.split(b'\t', 1)
            mode, kind, oid = meta.decode().split()
            name = path.decode('utf-8')
            if (mode not in {'100644', '100755'} or kind != 'blob'
                    or Path(name).is_absolute() or '..' in Path(name).parts):
                raise ValueError('unsupported historical object')
            objects.append((name, oid))
        raw = self.git('cat-file', '--batch', input=('\n'.join(oid for _, oid in objects)+'\n').encode())
        stream = io.BytesIO(raw)
        self.blobs = {}
        for name, oid in objects:
            fields = stream.readline().decode().split()
            if len(fields) != 3 or fields[:2] != [oid, 'blob']:
                raise ValueError('historical blob unavailable: ' + name)
            size = int(fields[2]); content = stream.read(size)
            if len(content) != size or stream.read(1) != b'\n':
                raise ValueError('historical blob truncated: ' + name)
            # Verify object identity too, rather than accepting a claimed cat-file header.
            actual = hashlib.sha1(b'blob '+str(size).encode()+b'\0'+content).hexdigest()
            if actual != oid:
                raise ValueError('historical blob identity mismatch: ' + name)
            self.blobs[name] = content
        self.protected_paths = tuple(name for name in self.blobs
            if name.startswith(('evaluation/', 'tests/fixtures/')))

    def git(self, *args, input=None):
        proc = subprocess.run(['git', '--no-replace-objects', '-C', str(self.repository), *args],
                              input=input, capture_output=True, env=environment())
        if proc.returncode:
            raise ValueError('historical Git objects unavailable; full local history required')
        return proc.stdout

    def _verify(self, root, names, label):
        root = Path(root).resolve()
        for name in names:
            path = root / name
            if any(p.is_symlink() for p in [path, *path.parents] if p != root and root in p.parents):
                raise ValueError(label + ' symlink: ' + name)
            try:
                actual = path.read_bytes()
            except OSError as exc:
                raise ValueError(label + ' missing: ' + name) from exc
            if actual != self.blobs[name]:
                raise ValueError(label + ' changed: ' + name)
        return {'historical_revision': HISTORICAL_REVISION, 'historical_tree': HISTORICAL_TREE,
                'verified_files': len(names)}

    def verify_evidence(self, root=None):
        return self._verify(root or self.repository, self.protected_paths, 'evidence')

    def verify_snapshot(self, root):
        return self._verify(root, tuple(self.blobs), 'historical snapshot')

    @contextmanager
    def snapshot(self):
        """Local clone retains Git ancestry; never runs modified historical validators."""
        with tempfile.TemporaryDirectory(prefix='logicwrite-historical-evidence-') as temporary:
            target = Path(temporary) / 'snapshot'
            common = self.git('rev-parse', '--path-format=absolute', '--git-common-dir').decode().strip()
            clone = subprocess.run(['git', '-c', 'core.hooksPath=/dev/null', 'clone', '--shared',
                                    '--no-checkout', '--quiet', '--', common, str(target)],
                                   capture_output=True, env=environment())
            if clone.returncode:
                raise ValueError('historical snapshot clone failed')
            checkout = subprocess.run(['git', '--no-replace-objects', '-C', str(target),
                '-c', 'core.autocrlf=false', '-c', 'core.hooksPath=/dev/null', 'checkout',
                '--quiet', '--detach', HISTORICAL_REVISION], capture_output=True, env=environment())
            if checkout.returncode:
                raise ValueError('historical snapshot checkout failed')
            self.verify_snapshot(target)
            yield target
