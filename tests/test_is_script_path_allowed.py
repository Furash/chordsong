"""Tests for is_script_path_allowed — pure disk-path check, no bpy."""
import os
import sys
import tempfile

sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

from utils.context_path import is_script_path_allowed


def test_empty_folder_allows_any_path():
    allowed, _ = is_script_path_allowed("C:/anywhere/foo.py", "")
    assert allowed is True


def test_none_folder_allows_any_path():
    allowed, _ = is_script_path_allowed("C:/anywhere/foo.py", None)
    assert allowed is True


def test_empty_filepath_rejected():
    allowed, reason = is_script_path_allowed("", "C:/scripts")
    assert allowed is False
    assert "Empty" in reason


def test_script_inside_folder_allowed():
    with tempfile.TemporaryDirectory() as base:
        scripts = os.path.join(base, "scripts")
        os.makedirs(scripts)
        inside = os.path.join(scripts, "foo.py")
        with open(inside, "w") as f:
            f.write("")
        allowed, _ = is_script_path_allowed(inside, scripts)
        assert allowed is True


def test_nested_subdir_allowed():
    with tempfile.TemporaryDirectory() as base:
        scripts = os.path.join(base, "scripts")
        nested_dir = os.path.join(scripts, "sub", "nested")
        os.makedirs(nested_dir)
        nested = os.path.join(nested_dir, "bar.py")
        with open(nested, "w") as f:
            f.write("")
        allowed, _ = is_script_path_allowed(nested, scripts)
        assert allowed is True


def test_script_outside_folder_rejected():
    with tempfile.TemporaryDirectory() as base:
        scripts = os.path.join(base, "scripts")
        outside = os.path.join(base, "outside")
        os.makedirs(scripts)
        os.makedirs(outside)
        evil = os.path.join(outside, "evil.py")
        with open(evil, "w") as f:
            f.write("")
        allowed, reason = is_script_path_allowed(evil, scripts)
        assert allowed is False
        assert "outside" in reason.lower() or evil in reason


def test_parent_dir_rejected():
    with tempfile.TemporaryDirectory() as base:
        scripts = os.path.join(base, "scripts")
        os.makedirs(scripts)
        parent_path = os.path.join(base, "parent.py")
        with open(parent_path, "w") as f:
            f.write("")
        allowed, _ = is_script_path_allowed(parent_path, scripts)
        assert allowed is False


def test_dotdot_traversal_rejected():
    with tempfile.TemporaryDirectory() as base:
        scripts = os.path.join(base, "scripts")
        outside = os.path.join(base, "outside")
        os.makedirs(scripts)
        os.makedirs(outside)
        traversal = os.path.join(scripts, "..", "outside", "evil.py")
        allowed, _ = is_script_path_allowed(traversal, scripts)
        assert allowed is False


def test_trailing_separator_on_folder():
    with tempfile.TemporaryDirectory() as base:
        scripts = os.path.join(base, "scripts")
        os.makedirs(scripts)
        inside = os.path.join(scripts, "foo.py")
        with open(inside, "w") as f:
            f.write("")
        allowed, _ = is_script_path_allowed(inside, scripts + os.sep)
        assert allowed is True


def test_nonexistent_folder_rejects_unrelated_path():
    allowed, _ = is_script_path_allowed("C:/random/x.py", "C:/nonexistent/folder")
    assert allowed is False


def test_case_normalization_does_not_crash():
    # On Windows this is a meaningful case-insensitive match; on POSIX it's
    # a no-op. Just verify the call doesn't raise.
    is_script_path_allowed("C:/Scripts/foo.py", "c:/scripts")
