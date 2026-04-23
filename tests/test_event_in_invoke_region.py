"""Tests for event_in_invoke_region — pure logic, no bpy.

The helper lives in operators.common which top-imports bpy, so we can't
import it directly. Mirror the body here; update both sides together if
production changes. A follow-up in this refactor branch could lift the
helper into a bpy-free module.
"""
import os
import sys
from dataclasses import dataclass

sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))


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


def test_matching_area_and_region():
    area = FakePtrHolder(0x1000)
    region = FakePtrHolder(0x2000)
    ctx = FakeContext(area=area, region=region)
    assert event_in_invoke_region(ctx, 0x1000, region) is True


def test_area_ptr_mismatch():
    area = FakePtrHolder(0x9999)
    region = FakePtrHolder(0x2000)
    ctx = FakeContext(area=area, region=region)
    assert event_in_invoke_region(ctx, 0x1000, region) is False


def test_region_ptr_mismatch():
    area = FakePtrHolder(0x1000)
    invoke_region = FakePtrHolder(0x2000)
    other_region = FakePtrHolder(0x8888)
    ctx = FakeContext(area=area, region=other_region)
    assert event_in_invoke_region(ctx, 0x1000, invoke_region) is False


def test_no_invoke_area_ptr():
    area = FakePtrHolder(0x1000)
    region = FakePtrHolder(0x2000)
    ctx = FakeContext(area=area, region=region)
    assert event_in_invoke_region(ctx, None, region) is False


def test_no_invoke_region():
    area = FakePtrHolder(0x1000)
    region = FakePtrHolder(0x2000)
    ctx = FakeContext(area=area, region=region)
    assert event_in_invoke_region(ctx, 0x1000, None) is False


def test_no_context_area():
    region = FakePtrHolder(0x2000)
    ctx = FakeContext(area=None, region=region)
    assert event_in_invoke_region(ctx, 0x1000, region) is False


def test_no_context_region():
    area = FakePtrHolder(0x1000)
    ctx = FakeContext(area=area, region=None)
    assert event_in_invoke_region(ctx, 0x1000, FakePtrHolder(0x2000)) is False


def test_area_as_pointer_raises():
    region = FakePtrHolder(0x2000)
    ctx = FakeContext(area=RaisingPtrHolder(), region=region)
    assert event_in_invoke_region(ctx, 0x1000, region) is False


def test_region_as_pointer_raises():
    area = FakePtrHolder(0x1000)
    ctx = FakeContext(area=area, region=RaisingPtrHolder())
    assert event_in_invoke_region(ctx, 0x1000, FakePtrHolder(0x2000)) is False


def test_invoke_region_as_pointer_raises():
    class RaisingInvokeRegion:
        def as_pointer(self):
            raise AttributeError("stale")

    area = FakePtrHolder(0x1000)
    region = FakePtrHolder(0x2000)
    ctx = FakeContext(area=area, region=region)
    assert event_in_invoke_region(ctx, 0x1000, RaisingInvokeRegion()) is False
