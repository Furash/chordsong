"""Tests for is_script_path_allowed — pure disk-path check, no bpy."""

import sys
import os
import tempfile

sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

from utils.context_path import is_script_path_allowed


def _run():
    passed = 0
    failed = 0

    def check(name, got, want):
        nonlocal passed, failed
        if got == want:
            passed += 1
        else:
            failed += 1
            print(f"FAIL {name}\n  got : {got!r}\n  want: {want!r}")

    # Empty scripts_folder → confinement off, all paths allowed
    check("no_folder_any_path_ok", is_script_path_allowed("C:/anywhere/foo.py", "")[0], True)
    check("none_folder_ok", is_script_path_allowed("C:/anywhere/foo.py", None)[0], True)

    # Empty filepath with non-empty folder → rejected
    allowed, reason = is_script_path_allowed("", "C:/scripts")
    check("empty_filepath_rejected", allowed, False)
    check("empty_filepath_reason", "Empty" in reason, True)

    # Use real tmp paths for realpath-based checks
    with tempfile.TemporaryDirectory() as tmpdir:
        scripts = os.path.join(tmpdir, "scripts")
        os.makedirs(scripts, exist_ok=True)
        outside = os.path.join(tmpdir, "outside")
        os.makedirs(outside, exist_ok=True)

        # Script inside folder → allowed
        inside_path = os.path.join(scripts, "foo.py")
        with open(inside_path, "w") as f:
            f.write("")
        check("inside_folder_allowed", is_script_path_allowed(inside_path, scripts)[0], True)

        # Script in nested subdir → allowed
        nested_dir = os.path.join(scripts, "sub", "nested")
        os.makedirs(nested_dir, exist_ok=True)
        nested_path = os.path.join(nested_dir, "bar.py")
        with open(nested_path, "w") as f:
            f.write("")
        check("nested_subdir_allowed", is_script_path_allowed(nested_path, scripts)[0], True)

        # Script outside folder → rejected
        outside_path = os.path.join(outside, "evil.py")
        with open(outside_path, "w") as f:
            f.write("")
        allowed, reason = is_script_path_allowed(outside_path, scripts)
        check("outside_folder_rejected", allowed, False)
        check("outside_reason_mentions_path", outside_path in reason or "outside" in reason.lower(), True)

        # Parent of folder → rejected (prevents "scripts/../evil.py" trick)
        parent_path = os.path.join(tmpdir, "parent.py")
        with open(parent_path, "w") as f:
            f.write("")
        check("parent_dir_rejected", is_script_path_allowed(parent_path, scripts)[0], False)

        # Traversal via .. resolves to outside → rejected
        traversal = os.path.join(scripts, "..", "outside", "evil.py")
        check("traversal_rejected", is_script_path_allowed(traversal, scripts)[0], False)

        # Folder with trailing slash still works
        scripts_with_slash = scripts + os.sep
        check("folder_trailing_sep_allows_inside", is_script_path_allowed(inside_path, scripts_with_slash)[0], True)

    # Case-insensitivity on Windows (os.path.normcase lowers on Win)
    # On other OSes normcase is a no-op, so this just verifies we don't crash.
    # Build a folder path and a filepath with different case; behavior depends
    # on platform — just check the call doesn't raise.
    try:
        is_script_path_allowed("C:/Scripts/foo.py", "c:/scripts")
        passed += 1
    except Exception as e:
        failed += 1
        print(f"FAIL case_normalization_no_crash: {e}")

    # Non-existent folder → realpath just returns the normalized path; if
    # filepath doesn't match, reject. Caller is responsible for handling
    # "folder not found" separately (we reject rather than pass-through).
    allowed, _ = is_script_path_allowed("C:/random/x.py", "C:/nonexistent/folder")
    check("nonexistent_folder_rejects_unrelated_path", allowed, False)

    print(f"\n{passed} passed, {failed} failed")
    if failed:
        sys.exit(1)


if __name__ == "__main__":
    _run()
