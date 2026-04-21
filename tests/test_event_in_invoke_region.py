"""Tests for event_in_invoke_region — pure logic, no bpy import.

The helper lives in operators.common which top-imports bpy, so we can't import
the operators package directly without bpy-mock. Instead, we inline-copy the
function under test here and keep the real source as the single source of
truth for production. If the production implementation changes, update the
mirrored body below too.

A cleaner fix would be to lift event_in_invoke_region into a bpy-free module;
tracked as a follow-up in the refactor branch.
"""

import sys
import os
from dataclasses import dataclass

sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))


# Mirror of operators.common.event_in_invoke_region (see docstring above).
def event_in_invoke_region(context, invoke_area_ptr, invoke_region):
    if invoke_area_ptr is None or context.area is None:
        return False
    try:
        if context.area.as_pointer() != invoke_area_ptr:
            return False
    except (AttributeError, ReferenceError, RuntimeError):
        return False
    if invoke_region is None or context.region is None:
        return False
    try:
        if context.region.as_pointer() != invoke_region.as_pointer():
            return False
    except (AttributeError, ReferenceError, RuntimeError):
        return False
    return True


@dataclass
class FakePtrHolder:
    ptr: int
    def as_pointer(self):
        return self.ptr


class RaisingPtrHolder:
    def as_pointer(self):
        raise ReferenceError("area has been freed")


@dataclass
class FakeContext:
    area: object = None
    region: object = None


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

    area = FakePtrHolder(0x1000)
    region = FakePtrHolder(0x2000)
    ctx = FakeContext(area=area, region=region)

    # Happy path: both area and region match
    check("matching_area_and_region", event_in_invoke_region(ctx, 0x1000, region), True)

    # Area pointer mismatch (e.g. click fired in a different area of same space type)
    other_area = FakePtrHolder(0x9999)
    ctx_other_area = FakeContext(area=other_area, region=region)
    check("area_ptr_mismatch", event_in_invoke_region(ctx_other_area, 0x1000, region), False)

    # Region pointer mismatch (click in N-panel of same area vs. invoke window region)
    other_region = FakePtrHolder(0x8888)
    ctx_other_region = FakeContext(area=area, region=other_region)
    check("region_ptr_mismatch", event_in_invoke_region(ctx_other_region, 0x1000, region), False)

    # None inputs
    check("no_invoke_area_ptr", event_in_invoke_region(ctx, None, region), False)
    check("no_invoke_region", event_in_invoke_region(ctx, 0x1000, None), False)
    check("no_context_area", event_in_invoke_region(FakeContext(area=None, region=region), 0x1000, region), False)
    check("no_context_region", event_in_invoke_region(FakeContext(area=area, region=None), 0x1000, region), False)

    # as_pointer() raises (stale bpy reference)
    raising_area = RaisingPtrHolder()
    ctx_raising = FakeContext(area=raising_area, region=region)
    check("area_as_pointer_raises", event_in_invoke_region(ctx_raising, 0x1000, region), False)

    # Region as_pointer() raises
    raising_region = RaisingPtrHolder()
    ctx_raising_reg = FakeContext(area=area, region=raising_region)
    check("region_as_pointer_raises", event_in_invoke_region(ctx_raising_reg, 0x1000, region), False)

    # invoke_region.as_pointer() raises
    class RaisingInvokeRegion:
        def as_pointer(self):
            raise AttributeError("stale")
    check(
        "invoke_region_as_pointer_raises",
        event_in_invoke_region(ctx, 0x1000, RaisingInvokeRegion()),
        False,
    )

    print(f"\n{passed} passed, {failed} failed")
    if failed:
        sys.exit(1)


if __name__ == "__main__":
    _run()
