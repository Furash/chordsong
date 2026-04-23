"""Test runner for Chord Song.

Pytest's rootpath walker tries to import the addon's top-level __init__.py
(which requires bpy) whenever collecting anything under tests/, so pytest is
unusable here without either stubbing bpy or relocating the entry point.
This runner sidesteps that fight: each test file is loaded by file path via
importlib, every top-level `test_*` callable is invoked with no arguments,
and a pass/fail count is printed at the end. Exit code is non-zero on any
failure — suitable for CI.

Tests that need a tmpdir create one inline with tempfile.TemporaryDirectory;
no pytest fixtures are supported. If a file defines `_run()` (legacy style)
and no `test_*` functions, the runner calls `_run()` instead.
"""
import importlib.util
import os
import sys
import traceback

TESTS_DIR = os.path.dirname(os.path.abspath(__file__))
REPO_ROOT = os.path.dirname(TESTS_DIR)
if REPO_ROOT not in sys.path:
    sys.path.insert(0, REPO_ROOT)


def _load_module(path):
    name = f"_chordsong_tests_{os.path.splitext(os.path.basename(path))[0]}"
    spec = importlib.util.spec_from_file_location(name, path)
    if spec is None or spec.loader is None:
        raise ImportError(f"could not load spec for {path}")
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod


def _discover_tests(mod):
    return [
        (n, getattr(mod, n))
        for n in sorted(dir(mod))
        if n.startswith("test_") and callable(getattr(mod, n))
    ]


def main():
    test_files = sorted(
        os.path.join(TESTS_DIR, f)
        for f in os.listdir(TESTS_DIR)
        if f.startswith("test_") and f.endswith(".py")
    )

    passed = 0
    failed = 0
    failures = []

    for path in test_files:
        rel = os.path.relpath(path, REPO_ROOT).replace(os.sep, "/")
        try:
            mod = _load_module(path)
        except Exception:
            failed += 1
            failures.append((rel, "<import>", traceback.format_exc()))
            continue

        tests = _discover_tests(mod)
        if tests:
            for name, fn in tests:
                try:
                    fn()
                    passed += 1
                except Exception:
                    failed += 1
                    failures.append((rel, name, traceback.format_exc()))
            continue

        # Legacy: file exposes a single _run() entry point (bare-assert style
        # with its own pass/fail counter) — invoke it as one unit.
        run_fn = getattr(mod, "_run", None)
        if callable(run_fn):
            try:
                run_fn()
                passed += 1
            except SystemExit as exc:
                if exc.code not in (None, 0):
                    failed += 1
                    failures.append((rel, "_run", f"SystemExit({exc.code})"))
                else:
                    passed += 1
            except Exception:
                failed += 1
                failures.append((rel, "_run", traceback.format_exc()))
            continue

        # No tests found in this file — ignore silently; empty test file is
        # not a failure.

    print(f"\n{passed} passed, {failed} failed")
    for rel, name, tb in failures:
        print(f"\n--- FAIL {rel}::{name} ---\n{tb}")
    sys.exit(0 if failed == 0 else 1)


if __name__ == "__main__":
    main()
