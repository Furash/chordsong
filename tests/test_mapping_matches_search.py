"""Tests for mapping_matches_search — the shared Chord Search filter."""
import os
import sys

sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

from core.engine import mapping_matches_search


class FakeSub:
    def __init__(self, **kw):
        for k, v in kw.items():
            setattr(self, k, v)


class FakeMapping:
    def __init__(self, chord="", label="", mapping_type="OPERATOR", **kw):
        self.chord = chord
        self.label = label
        self.mapping_type = mapping_type
        self.operator = ""
        self.context_path = ""
        self.property_value = ""
        self.python_file = ""
        self.sub_operators = []
        self.sub_items = []
        for k, v in kw.items():
            setattr(self, k, v)


OP = FakeMapping("s a", "Select All", operator="mesh.select_all",
                 sub_operators=[FakeSub(operator="mesh.select_less")])
TOG = FakeMapping("s w", "Wireframe", mapping_type="CONTEXT_TOGGLE",
                  context_path="space_data.overlay.show_wireframes",
                  sub_items=[FakeSub(path="space_data.show_gizmo", value="")])
PROP = FakeMapping("s f", "Frame", mapping_type="CONTEXT_PROPERTY",
                   context_path="scene.frame_current", property_value="42",
                   sub_items=[FakeSub(path="scene.frame_end", value="250")])
SCR = FakeMapping("s s", "Runner", mapping_type="PYTHON_FILE",
                  python_file="D:\\scripts\\do_thing.py")


def test_empty_query_matches_all():
    for m in (OP, TOG, PROP, SCR):
        assert mapping_matches_search(m, "")


def test_unprefixed_searches_all_fields():
    assert mapping_matches_search(OP, "select")        # label + operator
    assert mapping_matches_search(OP, "s a")           # chord
    assert mapping_matches_search(TOG, "wireframes")   # toggle path
    assert mapping_matches_search(PROP, "42")          # property value
    assert mapping_matches_search(SCR, "do_thing")     # script path
    assert not mapping_matches_search(OP, "nomatch")


def test_chord_prefix():
    assert mapping_matches_search(OP, "c:s a")
    assert not mapping_matches_search(OP, "c:select")  # label ignored


def test_label_prefix():
    assert mapping_matches_search(OP, "l:select")
    assert not mapping_matches_search(OP, "l:mesh.select_all")  # operator ignored


def test_operator_prefix_and_sub_operators():
    assert mapping_matches_search(OP, "o:mesh.select_all")
    assert mapping_matches_search(OP, "o:select_less")  # sub-operator
    assert not mapping_matches_search(TOG, "o:wireframes")  # wrong type


def test_toggle_prefix_and_sub_items():
    assert mapping_matches_search(TOG, "t:show_wireframes")
    assert mapping_matches_search(TOG, "t:show_gizmo")  # sub-item
    assert not mapping_matches_search(OP, "t:select")


def test_property_prefix_paths_values_and_sub_items():
    assert mapping_matches_search(PROP, "p:frame_current")
    assert mapping_matches_search(PROP, "p:42")
    assert mapping_matches_search(PROP, "p:frame_end")  # sub-item path
    assert mapping_matches_search(PROP, "p:250")        # sub-item value
    assert not mapping_matches_search(OP, "p:select")


def test_script_prefix():
    assert mapping_matches_search(SCR, "s:do_thing")
    assert not mapping_matches_search(OP, "s:select")


def test_bare_prefix_shows_all_of_type():
    assert mapping_matches_search(OP, "o:")
    assert mapping_matches_search(TOG, "t:")
    assert mapping_matches_search(PROP, "p:")
    assert mapping_matches_search(SCR, "s:")
    assert not mapping_matches_search(OP, "t:")
    assert not mapping_matches_search(TOG, "o:")
