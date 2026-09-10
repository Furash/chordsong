"""Timer callbacks in leader.py must not touch `self` methods/attrs.

bpy.app.timers callbacks fire after modal() has returned FINISHED, at which
point the operator's StructRNA is freed. Any `self.<attr>` access then raises
`ReferenceError: StructRNA of type CHORDSONG_OT_Leader has been removed`
(regression: toggle redraw after CONTEXT_TOGGLE). The only sanctioned use of
`self` inside a timer closure is passing it to `_safe_report`, which guards
the freed-operator case itself.
"""
import ast
import os
import sys

sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

LEADER = os.path.join(os.path.dirname(__file__), "..", "operators", "leader.py")


def _timer_closure_names(tree):
    names = set()
    for node in ast.walk(tree):
        if (
            isinstance(node, ast.Call)
            and isinstance(node.func, ast.Attribute)
            and node.func.attr == "register"
            and node.args
            and isinstance(node.args[0], ast.Name)
        ):
            names.add(node.args[0].id)
    return names


def _self_uses(func):
    """Yield (lineno, desc) for every `self` use except `_safe_report(self, ...)`."""
    allowed = set()
    for node in ast.walk(func):
        if (
            isinstance(node, ast.Call)
            and isinstance(node.func, ast.Name)
            and node.func.id == "_safe_report"
        ):
            for a in node.args:
                if isinstance(a, ast.Name) and a.id == "self":
                    allowed.add(id(a))
    for node in ast.walk(func):
        if isinstance(node, ast.Name) and node.id == "self" and id(node) not in allowed:
            yield node.lineno


def test_timer_closures_do_not_touch_self():
    with open(LEADER, encoding="utf-8") as f:
        tree = ast.parse(f.read())
    closure_names = _timer_closure_names(tree)
    assert closure_names, "no bpy.app.timers.register(<name>) calls found"
    offenders = []
    for node in ast.walk(tree):
        if isinstance(node, ast.FunctionDef) and node.name in closure_names:
            for ln in _self_uses(node):
                offenders.append(f"{node.name}: line {ln}")
    assert not offenders, "timer closures touch freed `self`:\n  " + "\n  ".join(offenders)
