"""Stage 8: validated local JSON with atomic file replacement.

Single-user/local-filesystem scope. Snapshot checks reject sequential stale
sessions; this is not a locked multi-process database transaction.
"""
import json
import os
from pathlib import Path
import tempfile

from data_model import State, ValidationError

PROJECT = Path(__file__).resolve().parent
SAMPLE_PATH = PROJECT / 'data' / 'sample.json'
DEFAULT_STATE_PATH = PROJECT / 'data' / 'current_state.json'


class StorageError(RuntimeError):
    """Loading or committing state failed; never silently reset to sample."""


class StorageConflict(StorageError):
    """The saved state differs from the caller's expected snapshot."""


class JsonStore:
    def __init__(self, path=DEFAULT_STATE_PATH):
        self.path = Path(path).expanduser().absolute()
        self._check_target()

    def _check_target(self):
        if self.path.suffix.lower() != '.json' or self.path.is_symlink():
            raise StorageError('State must use a separate JSON file, not a sample, reference or symlink')
        try:
            # Non-strict resolve can leave a symlink loop unresolved. The parent
            # must already exist, so strict resolution exposes loops/missing dirs.
            parent = self.path.parent.resolve(strict=True)
            if not parent.is_dir():
                raise StorageError('The state destination parent must be a directory')
            resolved = self.path.resolve()
        except (OSError, RuntimeError) as error:
            raise StorageError(f'Cannot resolve state path: {error}') from error
        if (resolved == SAMPLE_PATH.resolve()
                or resolved.is_relative_to((PROJECT / 'docs' / 'reference').resolve())
                or resolved.is_relative_to((PROJECT.parent / 'sources').resolve())):
            raise StorageError('State must use a separate JSON file, not a sample, reference or symlink')

    def load(self):
        self._check_target()
        try:
            return State.from_json(self.path.read_text(encoding='utf-8'))
        except (OSError, UnicodeError, ValidationError) as error:
            raise StorageError(f'Cannot load state from {self.path}: {error}') from error

    @staticmethod
    def _payload(state):
        if not isinstance(state, State):
            raise StorageError('Only a validated State can be saved')
        try:
            checked = State.from_dict(state.to_dict())
            return json.dumps(checked.to_dict(), ensure_ascii=True, indent=2, sort_keys=True) + '\n'
        except (ValueError, TypeError) as error:
            raise StorageError(f'Cannot serialize state: {error}') from error

    def initialize(self, sample):
        """Explicit first-run creation. Never overwrite an existing/corrupt file."""
        self._check_target()
        payload = self._payload(sample)
        self._write_atomic(payload, create_only=True)

    def commit(self, expected, candidate):
        """Save one complete transition, only if disk still matches expected."""
        self._check_target()
        if not isinstance(expected, State) or not isinstance(candidate, State):
            raise StorageError('Commit requires validated source and candidate states')
        if candidate.revision != expected.revision + 1:
            raise StorageError('A commit must advance revision exactly once')
        for catalog in ('items', 'warehouses', 'stores'):
            if set(getattr(expected, catalog)) != set(getattr(candidate, catalog)):
                raise StorageError('A commit cannot add or remove catalog IDs')
        payload = self._payload(candidate)
        if self.load() != expected:
            raise StorageConflict('Saved state changed; reload and create a new preview')
        self._write_atomic(payload, create_only=False)

    def _write_atomic(self, payload, *, create_only):
        temp_path = None
        try:
            # Same directory keeps replacement on the same filesystem. Parents
            # must already exist; a bad destination must not silently create one.
            with tempfile.NamedTemporaryFile(mode='w', encoding='utf-8',
                    dir=self.path.parent, prefix=f'.{self.path.name}.', suffix='.tmp',
                    delete=False) as stream:
                temp_path = Path(stream.name)
                stream.write(payload)
                stream.flush()
                os.fsync(stream.fileno())
            if create_only:
                # Atomic no-clobber publication, including initialization races.
                os.link(temp_path, self.path)
            else:
                os.replace(temp_path, self.path)
            # No fallible durability operation after publication: a later error
            # must not incorrectly tell the caller that this commit was rejected.
        except OSError as error:
            raise StorageError(f'Cannot save state to {self.path}: {error}') from error
        finally:
            if temp_path is not None:
                try:
                    temp_path.unlink(missing_ok=True)
                except OSError:
                    # A leftover temp is not active state. Cleanup failure must
                    # not turn a successfully published state into a failed commit.
                    pass
