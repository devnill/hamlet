"""Verify version strings stay in sync across package and plugin manifest."""
import json
import re
from pathlib import Path

REPO_ROOT = Path(__file__).parent.parent
_VERSION_RE = re.compile(r"""^(\w+)\s*=\s*['"]([^'"]+)['"]""")


def _extract_version(path: Path, var_name: str) -> str:
    """Extract a version variable from a Python file."""
    for line in path.read_text().splitlines():
        m = _VERSION_RE.match(line)
        if m and m.group(1) == var_name:
            return m.group(2)
    raise AssertionError(f"{var_name} not found in {path}")


def _get_package_version() -> str:
    return _extract_version(REPO_ROOT / "src" / "hamlet" / "__init__.py", "__version__")


def test_plugin_json_version_matches_package():
    plugin_json = REPO_ROOT / ".claude-plugin" / "plugin.json"
    plugin_version = json.loads(plugin_json.read_text())["version"]
    package_version = _get_package_version()

    assert plugin_version == package_version, (
        f"plugin.json version ({plugin_version}) != "
        f"__init__.py version ({package_version}). "
        "Update .claude-plugin/plugin.json to match."
    )


def test_hook_version_matches_package():
    hook_version = _extract_version(
        REPO_ROOT / "hooks" / "hamlet_hook_utils.py", "HOOK_VERSION"
    )
    package_version = _get_package_version()

    assert hook_version == package_version, (
        f"HOOK_VERSION ({hook_version}) != "
        f"__init__.py version ({package_version}). "
        "Update hooks/hamlet_hook_utils.py HOOK_VERSION to match."
    )


def test_pyproject_toml_version_matches_package():
    pyproject = REPO_ROOT / "pyproject.toml"
    toml_version = None
    for line in pyproject.read_text().splitlines():
        m = re.match(r'^version\s*=\s*"([^"]+)"', line)
        if m:
            toml_version = m.group(1)
            break

    assert toml_version is not None, "version not found in pyproject.toml"

    package_version = _get_package_version()
    assert toml_version == package_version, (
        f"pyproject.toml version ({toml_version}) != "
        f"__init__.py version ({package_version}). "
        "Update pyproject.toml to match."
    )
