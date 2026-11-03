from __future__ import annotations

import ast
import sys
from pathlib import Path

import pytest

pytestmark = pytest.mark.architecture

SRC = Path("src/payment_service")
TESTS = Path("tests")
MAX_FILE_LINES = 200
BANNED_MODULE_NAMES = frozenset(
    {"base.py", "common.py", "utils.py", "helpers.py", "models.py", "types.py"}
)
MULTI_CLASS_ALLOWED = frozenset({"exceptions.py"})


def _module_paths() -> list[Path]:
    return sorted(path for path in SRC.rglob("*.py") if path.name != "__init__.py")


def _top_level_class_names(path: Path) -> list[str]:
    tree = ast.parse(path.read_text(encoding="utf-8"))
    return [node.name for node in tree.body if isinstance(node, ast.ClassDef)]


def _test_module_paths() -> list[Path]:
    return sorted(path for path in TESTS.rglob("*.py") if path.name != "__init__.py")


def _is_fixture_decorator(node: ast.expr) -> bool:
    target = node.func if isinstance(node, ast.Call) else node
    return (
        isinstance(target, ast.Attribute)
        and target.attr == "fixture"
        and isinstance(target.value, ast.Name)
        and target.value.id == "pytest"
    )


def _fixture_names(path: Path) -> list[str]:
    tree = ast.parse(path.read_text(encoding="utf-8"))
    return [
        node.name
        for node in tree.body
        if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef))
        and any(_is_fixture_decorator(decorator) for decorator in node.decorator_list)
    ]


def _imported_roots(path: Path) -> set[str]:
    tree = ast.parse(path.read_text(encoding="utf-8"))
    roots: set[str] = set()
    for node in ast.walk(tree):
        if isinstance(node, ast.ImportFrom):
            if node.level or node.module is None:
                continue
            module = node.module
        elif isinstance(node, ast.Import):
            module = node.names[0].name
        else:
            continue
        roots.add(module.split(".")[0])
    return roots


@pytest.mark.parametrize(
    "path",
    [path for path in _module_paths() if path.name not in MULTI_CLASS_ALLOWED],
    ids=str,
)
def test_module_defines_at_most_one_class(path: Path) -> None:
    class_names = _top_level_class_names(path)

    assert len(class_names) <= 1, f"{path} defines several classes: {class_names}"


def test_no_dumping_ground_module_names() -> None:
    offenders = [str(path) for path in SRC.rglob("*.py") if path.name in BANNED_MODULE_NAMES]

    assert not offenders, f"banned dumping-ground modules: {offenders}"


def test_modules_respect_line_limit() -> None:
    for path in SRC.rglob("*.py"):
        lines = len(path.read_text(encoding="utf-8").splitlines())
        assert lines <= MAX_FILE_LINES, f"{path} has {lines} lines"


def test_packages_declare_dunder_all() -> None:
    offenders: list[str] = []
    for path in SRC.rglob("__init__.py"):
        tree = ast.parse(path.read_text(encoding="utf-8"))
        declares_all = any(
            (
                isinstance(node, ast.Assign)
                and any(
                    isinstance(target, ast.Name) and target.id == "__all__"
                    for target in node.targets
                )
            )
            or (
                isinstance(node, ast.AnnAssign)
                and isinstance(node.target, ast.Name)
                and node.target.id == "__all__"
            )
            for node in tree.body
        )
        if not declares_all:
            offenders.append(str(path))

    assert not offenders, f"packages without __all__: {offenders}"


@pytest.mark.parametrize("path", _test_module_paths(), ids=str)
def test_test_module_defines_at_most_one_class(path: Path) -> None:
    class_names = _top_level_class_names(path)

    assert len(class_names) <= 1, f"{path} defines several classes: {class_names}"


def test_test_modules_respect_line_limit() -> None:
    for path in TESTS.rglob("*.py"):
        lines = len(path.read_text(encoding="utf-8").splitlines())
        assert lines <= MAX_FILE_LINES, f"{path} has {lines} lines"


@pytest.mark.parametrize(
    "path",
    sorted(TESTS.rglob("test_*.py")),
    ids=str,
)
def test_fixtures_live_in_conftest(path: Path) -> None:
    fixture_names = _fixture_names(path)

    assert not fixture_names, f"{path} defines local fixtures: {fixture_names}"


def test_domain_depends_only_on_stdlib() -> None:
    forbidden: dict[str, set[str]] = {}
    for path in (SRC / "domain").rglob("*.py"):
        external = {
            root
            for root in _imported_roots(path)
            if root != "payment_service" and root not in sys.stdlib_module_names
        }
        if external:
            forbidden[str(path)] = external

    assert not forbidden, f"domain imports non-stdlib modules: {forbidden}"
