"""mapping_signature: context-independent identity used by Convert to Global."""
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from core.chord_serialization import mapping_signature  # noqa: E402


class Sub:
    def __init__(self, **kw):
        self.operator = kw.get("operator", "")
        self.call_context = kw.get("call_context", "EXEC_DEFAULT")
        self.kwargs_json = kw.get("kwargs_json", "")
        self.path = kw.get("path", "")
        self.value = kw.get("value", "")


class M:
    def __init__(self, **kw):
        self.chord = kw.get("chord", "x")
        self.label = kw.get("label", "Scripts")
        self.icon = kw.get("icon", "")
        self.group = kw.get("group", "Chord Song")
        self.context = kw.get("context", "VIEW_3D")
        self.mapping_type = kw.get("mapping_type", "OPERATOR")
        self.enabled = kw.get("enabled", True)
        self.operator = kw.get("operator", "chordsong.scripts_overlay")
        self.call_context = kw.get("call_context", "INVOKE_DEFAULT")
        self.kwargs_json = kw.get("kwargs_json", "")
        self.sub_operators = kw.get("sub_operators", [])
        self.python_file = ""
        self.context_path = kw.get("context_path", "")
        self.property_value = ""
        self.sync_toggles = False
        self.script_params = []
        self.sub_items = kw.get("sub_items", [])


def test_same_chord_in_different_contexts_matches():
    a = M(context="VIEW_3D")
    b = M(context="SEQUENCE_EDITOR")
    assert mapping_signature(a) == mapping_signature(b)
    assert hash(mapping_signature(a)) == hash(mapping_signature(b))


def test_action_differences_break_the_match():
    base = M()
    assert mapping_signature(M(chord="y")) != mapping_signature(base)
    assert mapping_signature(M(operator="chordsong.search")) != mapping_signature(base)
    assert mapping_signature(M(kwargs_json="a=1")) != mapping_signature(base)
    assert mapping_signature(M(mapping_type="PYTHON_FILE")) != mapping_signature(base)


def test_presentation_differences_keep_the_match():
    # Renaming a copy, giving it an icon or a group, or switching it off
    # must not change the answer to "is this chord already in that editor?"
    # — the Contexts dialog pairs copies with this signature, and a false
    # negative both under-reports and then creates a duplicate.
    base = M()
    for variant in (M(label="Other"), M(icon="X"), M(group="Elsewhere"),
                    M(enabled=False), M(context="SEQUENCE_EDITOR")):
        assert mapping_signature(variant) == mapping_signature(base)


def test_operator_chain_and_toggle_paths_participate():
    chain = M(sub_operators=[Sub(operator="wm.redraw_timer")])
    assert mapping_signature(chain) != mapping_signature(M())
    t1 = M(mapping_type="CONTEXT_TOGGLE", context_path="space_data.overlay.show_floor")
    t2 = M(mapping_type="CONTEXT_TOGGLE", context_path="space_data.overlay.show_floor", context="ALL")
    t3 = M(mapping_type="CONTEXT_TOGGLE", context_path="space_data.overlay.show_axis_x")
    assert mapping_signature(t1) == mapping_signature(t2)
    assert mapping_signature(t1) != mapping_signature(t3)
