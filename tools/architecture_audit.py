import ast
from pathlib import Path
import sys


ROOT = Path(__file__).resolve().parents[1]
EXCLUDED_PARTS = {".git", ".venv", "__pycache__", "build", "artifacts"}
EXCLUDED_FILES = {"commands/cmd_skilldebug.py", "diretest.py"}
SKILL_HELPER_IMPORT_EXCEPTIONS = {"world/systems/skills.py", "engine/services/skill_service.py"}


def iter_python_files():
    for path in ROOT.rglob("*.py"):
        if any(part in EXCLUDED_PARTS for part in path.parts):
            continue
        if module_path(path) in EXCLUDED_FILES:
            continue
        yield path


def module_path(path):
    return path.relative_to(ROOT).as_posix()


def is_command_module(rel_path):
    return rel_path.startswith("commands/")


def is_domain_module(rel_path):
    return rel_path.startswith("domain/")


def audit_file(path):
    rel_path = module_path(path)
    try:
        source = path.read_text(encoding="utf-8-sig")
        tree = ast.parse(source, filename=rel_path)
    except SyntaxError as exc:
        return [(int(getattr(exc, "lineno", 1) or 1), f"syntax error prevents audit: {exc.msg}")]
    findings = []

    for node in ast.walk(tree):
        if isinstance(node, ast.ImportFrom):
            module = node.module or ""
            imported_names = {alias.name for alias in node.names}
            if is_command_module(rel_path) and module.startswith("domain"):
                findings.append((node.lineno, "commands must not import domain"))
            if is_domain_module(rel_path) and module.startswith("commands"):
                findings.append((node.lineno, "domain must not import commands"))
            if module == "world.systems.skills" and {"award_exp_skill", "award_xp", "train"} & imported_names:
                if rel_path not in SKILL_HELPER_IMPORT_EXCEPTIONS:
                    findings.append((node.lineno, "import SkillService instead of world.systems.skills XP helpers"))

        if isinstance(node, ast.Call):
            if isinstance(node.func, ast.Name) and node.func.id == "delay":
                if rel_path != "world/systems/scheduler.py":
                    findings.append((node.lineno, "delay() is forbidden outside world/systems/scheduler.py"))

    return findings


def main():
    failures = []
    for path in iter_python_files():
        findings = audit_file(path)
        if not findings:
            continue
        rel_path = module_path(path)
        for line_no, message in findings:
            failures.append(f"{rel_path}:{line_no}: {message}")

    if failures:
        print("Architecture audit failed:")
        for failure in failures:
            print(f"- {failure}")
        return 1

    print("Architecture audit passed.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())