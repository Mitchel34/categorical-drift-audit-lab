"""Small local wheel backend using only the Python standard library.

Only the five named package modules and wheel metadata enter the archive.
Building reads source bytes; it never imports the package or evaluates an audit.
"""

import base64
import csv
import hashlib
import io
from pathlib import Path
import zipfile


_PACKAGE = "categorical_drift_audit_lab"
_VERSION = "0.1.0"
_DIST_INFO = _PACKAGE + "-" + _VERSION + ".dist-info"
_WHEEL_NAME = _PACKAGE + "-" + _VERSION + "-py3-none-any.whl"
_MODULES = ("__init__.py", "__main__.py", "cli.py", "core.py", "export.py")
_STAMP = (1980, 1, 1, 0, 0, 0)


def get_requires_for_build_wheel(config_settings=None):
    """The backend and installed package require no third-party packages."""
    return []


def _metadata():
    return {
        _DIST_INFO + "/METADATA": (
            "Metadata-Version: 2.1\n"
            "Name: categorical-drift-audit-lab\n"
            "Version: 0.1.0\n"
            "Summary: Descriptive audits of empirical categorical count distributions\n"
            "Requires-Python: >=3.11\n"
            "\n"
            "Original empirical categorical count audits.\n"
        ).encode("ascii"),
        _DIST_INFO + "/WHEEL": (
            "Wheel-Version: 1.0\n"
            "Generator: categorical-drift-audit-lab\n"
            "Root-Is-Purelib: true\n"
            "Tag: py3-none-any\n"
        ).encode("ascii"),
        _DIST_INFO + "/entry_points.txt": (
            "[console_scripts]\n"
            "categorical-drift-audit = categorical_drift_audit_lab.cli:main\n"
        ).encode("ascii"),
    }


def _record(files):
    stream = io.StringIO(newline="")
    writer = csv.writer(stream, lineterminator="\n")
    for name in sorted(files):
        content = files[name]
        digest = base64.urlsafe_b64encode(hashlib.sha256(content).digest())
        writer.writerow((name, "sha256=" + digest.rstrip(b"=").decode("ascii"), len(content)))
    writer.writerow((_DIST_INFO + "/RECORD", "", ""))
    return stream.getvalue().encode("utf-8")


def build_wheel(wheel_directory, config_settings=None, metadata_directory=None):
    """Create one deterministic pure-Python wheel and return its filename."""
    root = Path(__file__).resolve().parent
    package = root / _PACKAGE
    if package.is_symlink() or not package.is_dir():
        raise ValueError("invalid_package_source")
    files = _metadata()
    for module in _MODULES:
        source = package / module
        if source.is_symlink() or not source.is_file():
            raise ValueError("invalid_package_source")
        files[_PACKAGE + "/" + module] = source.read_bytes()
    files[_DIST_INFO + "/RECORD"] = _record(files)
    destination = Path(wheel_directory) / _WHEEL_NAME
    with destination.open("xb") as output:
        with zipfile.ZipFile(output, "w", compression=zipfile.ZIP_STORED) as archive:
            for name in sorted(files):
                info = zipfile.ZipInfo(name, date_time=_STAMP)
                info.create_system = 3
                info.external_attr = 0o100644 << 16
                info.compress_type = zipfile.ZIP_STORED
                archive.writestr(info, files[name])
    return _WHEEL_NAME
