
from pathlib import Path
from datetime import datetime
# from hashlib import sha256
import typing as t
import typing_extensions as tx
from .machine import Machine
from dataclasses import dataclass

class PathInfo(tx.TypedDict):
    '''
    Info about a path:

    posix-style path relative to protocol root
    full path in OS style (used for HTS files to IMX)
    last modified timestamp in isoformat

    example:

    {
      "path": "automation_v5.0/7_W_3X_beforeStains_leaves10ul_PBS.LHC",
      "full": "C:\\ProgramData\\BioTek\\Liquid Handling Control 2.22\\Protocols\\automation_v5.0\\7_W_3X_beforeStains_leaves10ul_PBS.LHC",
      "modified": "2022-02-15 10:57:50",
    }
    '''
    path: str
    full: str
    modified: str

@dataclass
class DirList(Machine):
    root_dir: str
    ext: str
    enable_hts_mod: bool=False

    @property
    def root(self) -> Path:
        return Path(self.root_dir)

    def list(self) -> t.List[PathInfo]:
        value: t.List[PathInfo] = []
        for lhc in self.root.glob(f'**/*.{self.ext}'):
            path = str(lhc.relative_to(self.root)).replace('\\', '/')
            mtime = lhc.stat().st_mtime
            modified = str(datetime.fromtimestamp(mtime).replace(microsecond=0))
            value += [
                PathInfo(
                    path=path,
                    full=str(lhc.resolve()),
                    modified=modified,
                    # 'sha256': sha256(lhc.read_bytes()).hexdigest(),
                )
            ]
        return value

    def hts_mod(self, path: str, experiment_set: str, experiment_base_name: str):
        assert self.enable_hts_mod
        full_path = (self.root / Path(path)).resolve()
        lines = full_path.read_bytes().splitlines(keepends=True)
        assert lines[1].startswith(b'"stExperimentSet", "'), lines[:3]
        assert lines[2].startswith(b'"stDataFile", "'), lines[:3]
        assert lines[1].endswith(b'"\r\n'), lines[:3]
        assert lines[2].endswith(b'"\r\n'), lines[:3]
        lines[1] = f'"stExperimentSet", "{experiment_set}"\r\n'.encode('ascii')
        lines[2] = f'"stDataFile", "{experiment_base_name}"\r\n'.encode('ascii')
        assert lines[1].startswith(b'"stExperimentSet", "'), lines[:3]
        assert lines[2].startswith(b'"stDataFile", "'), lines[:3]
        assert lines[1].endswith(b'"\r\n'), lines[:3]
        assert lines[2].endswith(b'"\r\n'), lines[:3]
        # now save it in the same dir but with a new filename based on base name
        for i in range(10000):
            si = f' ({i})' if i else ''
            new_full_path = full_path.with_name(experiment_base_name + si + '.HTS')
            new_rel_path = new_full_path.relative_to(self.root)
            if not new_full_path.exists():
                new_full_path.write_bytes(b''.join(lines))
                return {
                    'path': str(new_rel_path).replace('\\', '/'),
                    'full': str(new_full_path),
                }
        else:
            raise ValueError('error could not make a filename for file')
