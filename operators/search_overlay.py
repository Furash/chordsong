"""Search overlay operator for fuzzy chord lookup."""

# pyright: reportMissingImports=false
# pyright: reportMissingModuleSource=false
# pylint: disable=import-error,broad-exception-caught

import bpy  # type: ignore

from ..core.engine import (
    filter_mappings_by_context,
    get_str_attr,
    humanize_chord,
    mapping_matches_search,
    parse_kwargs,
    split_chord,
)
from ..core.history import HistoryEntry, add_to_history
from ..ui.overlay import draw_overlay
from ..utils.fuzzy import fuzzy_match
from .common import prefs, detect_editor_context


def _mapping_to_history_entry(m) -> HistoryEntry:
    """Convert a preferences mapping into a HistoryEntry for execution.

    Reuses the Recents execution path (execute_history_entry_*), so the
    entry carries the same fidelity as a history replay: operator chains,
    script args, and the primary toggle/property context path.
    """
    mapping_type = getattr(m, "mapping_type", "OPERATOR")
    chord_tokens = split_chord(get_str_attr(m, "chord"))
    label = get_str_attr(m, "label") or "(no label)"
    icon = get_str_attr(m, "icon")

    operators = []
    python_file = None
    script_args = None
    context_path = None
    property_value = None

    if mapping_type == "OPERATOR":
        primary_op = get_str_attr(m, "operator").strip()
        if primary_op:
            operators.append({
                "op": primary_op,
                "kwargs": parse_kwargs(getattr(m, "kwargs_json", "{}")),
                "call_ctx": (getattr(m, "call_context", "EXEC_DEFAULT") or "EXEC_DEFAULT").strip(),
            })
        for sub in getattr(m, "sub_operators", []):
            sub_op = get_str_attr(sub, "operator").strip()
            if sub_op:
                operators.append({
                    "op": sub_op,
                    "kwargs": parse_kwargs(getattr(sub, "kwargs_json", "{}")),
                    "call_ctx": (getattr(sub, "call_context", "EXEC_DEFAULT") or "EXEC_DEFAULT").strip(),
                })
    elif mapping_type == "PYTHON_FILE":
        python_file = get_str_attr(m, "python_file").strip()
        all_kwargs_str = getattr(m, "kwargs_json", "") or ""
        for sp in getattr(m, "script_params", []):
            if sp.value.strip():
                if all_kwargs_str and not all_kwargs_str.strip().endswith(","):
                    all_kwargs_str += ", "
                all_kwargs_str += sp.value.strip()
        script_args = parse_kwargs(all_kwargs_str)
    elif mapping_type in ("CONTEXT_TOGGLE", "CONTEXT_PROPERTY"):
        context_path = get_str_attr(m, "context_path").strip()
        if mapping_type == "CONTEXT_PROPERTY":
            property_value = get_str_attr(m, "property_value")

    return HistoryEntry(
        chord_tokens=chord_tokens,
        label=label,
        icon=icon,
        mapping_type=mapping_type,
        operators=operators,
        python_file=python_file,
        script_args=script_args,
        context_path=context_path,
        property_value=property_value,
    )


class CHORDSONG_OT_SearchOverlay(bpy.types.Operator):
    """Fuzzy-search chord labels and execute the selected chord"""

    bl_idname = "chordsong.search"
    bl_label = "Search Chords"
    bl_options = set()

    # Class-level defaults are immutable sentinels; invoke rebinds on `self`.
    # _cancel_requested intentionally stays class-level as a shared signal
    # for re-invocation to request the active instance to stop (toggle).
    _draw_handles = None
    _text_buffer = ""
    _all_mappings = None
    _filtered_mappings = None
    _invoke_area_ptr = None
    _panel_states = None
    _cancel_requested = False  # Shared across invocations by design
    _hover_key = None

    def _ensure_draw_handler(self, context: bpy.types.Context):
        p = prefs(context)
        if not p.overlay_enabled or self._draw_handles:
            return

        area = getattr(self, '_override_area', None) or context.area
        region = getattr(self, '_override_region', None) or context.region

        self._invoke_area_ptr = area.as_pointer() if area else None
        self._area = area
        self._region = region

        self._draw_handles = {}
        supported_types = [
            bpy.types.SpaceView3D,
            bpy.types.SpaceNodeEditor,
            bpy.types.SpaceImageEditor,
            bpy.types.SpaceSequenceEditor,
        ]
        for st in supported_types:
            handle = st.draw_handler_add(self._draw_callback, (), "WINDOW", "POST_PIXEL")
            self._draw_handles[st] = handle

    def _remove_draw_handler(self):
        if not self._draw_handles:
            return
        for st, handle in self._draw_handles.items():
            try:
                st.draw_handler_remove(handle, "WINDOW")
            except Exception:
                pass
        self._draw_handles = {}

    def _tag_redraw(self):
        """Tag all relevant areas for redraw."""
        try:
            for window in bpy.context.window_manager.windows:
                try:
                    screen = window.screen
                    if not screen:
                        continue
                    for area in screen.areas:
                        try:
                            area.tag_redraw()
                        except Exception:
                            pass
                except Exception:
                    pass
        except Exception:
            pass

    def _filter_mappings(self):
        """Filter mappings against the text buffer.

        Supports the same prefix syntax as the Preferences Chord Search
        field (c:/l:/o:/p:/t:/s: field-scoped substring matching); plain
        queries fall back to fuzzy matching on label and group.
        """
        query = self._text_buffer.lower()
        if not query:
            self._filtered_mappings = list(self._all_mappings)
            return

        # Prefixed query: same semantics as the Chord Search field,
        # keeping the mappings' original order like the prefs list does.
        if len(query) >= 2 and query[1] == ':' and query[0] in ('c', 'l', 'o', 'p', 't', 's'):
            self._filtered_mappings = [
                m for m in self._all_mappings if mapping_matches_search(m, query)
            ]
            return

        scored = []
        for m in self._all_mappings:
            label = get_str_attr(m, "label")
            group = get_str_attr(m, "group")
            haystack = f"{label} {group}" if group else label
            matched, score = fuzzy_match(query, haystack)
            if matched:
                scored.append((score, m))

        scored.sort(key=lambda x: x[0])
        self._filtered_mappings = [m for _, m in scored]

    def _draw_callback(self):
        try:
            self._draw_callback_safe()
        except ReferenceError:
            # Operator's StructRNA freed mid-callback (blinker hot reload).
            return
        except Exception:
            # Defence in depth: never raise from a draw callback.
            return

    def _draw_callback_safe(self):
        from .leader import _is_reloading
        if _is_reloading():
            return
        context = bpy.context
        try:
            p = prefs(context)
        except (KeyError, AttributeError):
            return
        if not p.overlay_enabled:
            return

        if not hasattr(self, '_filtered_mappings') or self._filtered_mappings is None:
            self._remove_draw_handler()
            return

        # Only draw in the area where the overlay was invoked
        if self._invoke_area_ptr is not None and context.area is not None:
            try:
                if context.area.as_pointer() != self._invoke_area_ptr:
                    return
            except Exception:
                pass

        if hasattr(self, '_region') and self._region:
            from ..utils.render import ContextWithRegion
            context = ContextWithRegion(bpy.context, self._region, self._area)

        self._filter_mappings()

        class FakeMapping:
            def __init__(self, chord, label, icon, group, hit_key, source_mapping):
                self.chord = chord
                self.label = label
                self.icon = icon
                self.group = group
                self.context = "ALL"
                self.mapping_type = "OPERATOR"
                self.operator = ""
                # The hover/hit machinery keys rows on python_file; give each
                # row a unique synthetic key and carry the real mapping along.
                self.python_file = hit_key
                self.source_mapping = source_mapping
                self.enabled = True
                self.kwargs_json = ""
                self.call_context = "EXEC_DEFAULT"
                self.sub_items = []
                self.sub_operators = []
                self.script_params = []

        buffer_tokens = self._text_buffer.split() if self._text_buffer else []
        max_items = p.scripts_overlay_max_items

        fake_mappings = []
        for i, m in enumerate(self._filtered_mappings):
            if i >= max_items:
                break

            # First 9 results get an executable digit chord; the rest are
            # display-only until filtering brings them into the top 9.
            if i < 9:
                chord_num = str(i + 1)
                chord = f"{self._text_buffer} {chord_num}" if self._text_buffer else chord_num
            else:
                chord = ""

            # Show the real chord as secondary text so the user can learn it.
            # "::" splits into label_extra in build_overlay_rows.
            real_chord = humanize_chord(split_chord(get_str_attr(m, "chord")))
            label = f"{get_str_attr(m, 'label')} :: {real_chord}"
            fake_mappings.append(FakeMapping(
                chord, label, get_str_attr(m, "icon"), get_str_attr(m, "group"),
                hit_key=f"search://{i}", source_mapping=m,
            ))

        total = len(self._filtered_mappings)
        header_text = f"Search — {total} Chord{'s' if total != 1 else ''}"

        scripts_overlay_settings = {
            "column_rows": p.scripts_overlay_column_rows,
            "max_label_length": p.scripts_overlay_max_label_length,
            "gap": p.scripts_overlay_gap,
            "column_gap": p.scripts_overlay_column_gap,
            "hover_script_path": self._hover_key,
            "run_labels": ("Run chord", "Run + keep overlay open"),
        }

        draw_overlay(context, p, buffer_tokens, fake_mappings,
                     custom_header=header_text,
                     scripts_overlay_settings=scripts_overlay_settings)

    def _find_viewport_area(self, context):
        """Find a suitable viewport area when invoked from a non-viewport context."""
        supported = {'VIEW_3D', 'NODE_EDITOR', 'IMAGE_EDITOR', 'SEQUENCE_EDITOR'}
        for window in context.window_manager.windows:
            try:
                screen = window.screen
                if not screen:
                    continue
                for area in screen.areas:
                    if area.type in supported:
                        for region in area.regions:
                            if region.type == 'WINDOW':
                                return area, region
            except Exception:
                continue
        return None, None

    def invoke(self, context: bpy.types.Context, _event: bpy.types.Event):
        """Start search overlay modal operation."""
        # If already running, request cancellation (acts as toggle)
        if CHORDSONG_OT_SearchOverlay._draw_handles:
            CHORDSONG_OT_SearchOverlay._cancel_requested = True
            self._tag_redraw()
            return {'CANCELLED'}

        p = prefs(context)
        p.ensure_defaults()

        supported = {'VIEW_3D', 'NODE_EDITOR', 'IMAGE_EDITOR', 'SEQUENCE_EDITOR'}
        area = context.area
        region = context.region
        if area and area.type not in supported:
            area, region = self._find_viewport_area(context)
            if not area:
                self.report({'WARNING'}, "No viewport area found for overlay")
                return {'CANCELLED'}
        self._override_area = area
        self._override_region = region

        # Pick up a panel stash from Leader if it handed off, else hide fresh.
        from ..utils.panels import hide_panels, take_panel_states
        stashed = take_panel_states()
        if stashed:
            self._panel_states = stashed
        else:
            self._panel_states = hide_panels(context, p.overlay_hide_panels)

        context_type = detect_editor_context(context)
        self._all_mappings = [
            m for m in filter_mappings_by_context(p.mappings, context_type)
            if getattr(m, "enabled", True) and get_str_attr(m, "chord").strip()
        ]

        if not self._all_mappings:
            self.report({'INFO'}, "No chords available in this context")
            self._restore_panels(context)
            return {'CANCELLED'}

        self._text_buffer = ""
        self._filtered_mappings = []
        self._hover_key = None
        self._filter_mappings()  # Initial filter (shows all)
        self._ensure_draw_handler(context)
        context.window_manager.modal_handler_add(self)
        self._tag_redraw()
        return {"RUNNING_MODAL"}

    def _finish(self, context: bpy.types.Context):
        CHORDSONG_OT_SearchOverlay._cancel_requested = False
        self._restore_panels(context)
        self._remove_draw_handler()
        self._tag_redraw()

    def cancel(self, context: bpy.types.Context):
        """Clean up when operator is interrupted."""
        self._finish(context)

    def _restore_panels(self, context: bpy.types.Context):
        """Restore panels captured during invoke, then clear local state."""
        from ..utils.panels import restore_panels
        restore_panels(context, self._panel_states)
        self._panel_states = {}

    def modal(self, context: bpy.types.Context, event: bpy.types.Event):
        try:
            return self._modal_inner(context, event)
        except Exception:
            import traceback
            traceback.print_exc()
            print("Chord Song Search: modal crashed, cleaning up to prevent busy state.")
            try:
                self._finish(context)
            except Exception:
                self._remove_draw_handler()
            return {"CANCELLED"}

    def _modal_inner(self, context: bpy.types.Context, event: bpy.types.Event):
        from .leader import _is_reloading
        if _is_reloading():
            self._finish(context)
            return {"CANCELLED"}
        if CHORDSONG_OT_SearchOverlay._cancel_requested:
            CHORDSONG_OT_SearchOverlay._cancel_requested = False
            self._finish(context)
            return {"CANCELLED"}

        if event.type in {"ESC", "RIGHTMOUSE"} and event.value == "PRESS":
            self._finish(context)
            return {"CANCELLED"}

        # Hover tracking: highlight the row under the cursor (same pattern
        # as the scripts overlay; coords are only valid in the invoke region).
        if event.type == "MOUSEMOVE":
            from .common import event_in_invoke_region
            new_key = None
            if event_in_invoke_region(context, self._invoke_area_ptr, getattr(self, "_region", None)):
                try:
                    from ..ui.overlay import find_hit
                    hit = find_hit(event.mouse_region_x, event.mouse_region_y)
                except Exception:
                    hit = None
                if hit and hit["kind"] == "script":
                    ref = hit["payload"].get("mapping_ref")
                    new_key = getattr(ref, "python_file", None) if ref is not None else None
            if new_key != self._hover_key:
                self._hover_key = new_key
                self._tag_redraw()
            return {"RUNNING_MODAL"}

        # LEFTMOUSE: plain click executes + closes; CTRL+click executes + stays open.
        if event.type == "LEFTMOUSE" and event.value == "PRESS":
            from .common import event_in_invoke_region
            if event_in_invoke_region(context, self._invoke_area_ptr, getattr(self, "_region", None)):
                try:
                    from ..ui.overlay import find_hit
                    hit = find_hit(event.mouse_region_x, event.mouse_region_y)
                except Exception:
                    hit = None
                if hit and hit["kind"] == "script":
                    ref = hit["payload"].get("mapping_ref")
                    source = getattr(ref, "source_mapping", None) if ref is not None else None
                    if source is not None:
                        if event.ctrl:
                            self._execute_mapping(context, source, close=False)
                            return {"RUNNING_MODAL"}
                        self._execute_mapping(context, source)
                        return {"FINISHED"}
            return {"RUNNING_MODAL"}

        if event.type == "BACK_SPACE" and event.value == "PRESS":
            if self._text_buffer:
                self._text_buffer = self._text_buffer[:-1]
                self._invalidate_hit_boxes()
                self._tag_redraw()
                return {"RUNNING_MODAL"}
            else:
                self._finish(context)
                return {"CANCELLED"}

        if event.value != "PRESS":
            return {"RUNNING_MODAL"}

        number_key_map = {
            "ZERO": 0, "ONE": 1, "TWO": 2, "THREE": 3, "FOUR": 4,
            "FIVE": 5, "SIX": 6, "SEVEN": 7, "EIGHT": 8, "NINE": 9,
            **{f"NUMPAD_{i}": i for i in range(10)},
            **{f"{i}": i for i in range(10)},
        }

        if event.type in number_key_map:
            chord_num = number_key_map[event.type]

            # Modifier held: digit goes into the filter text instead
            if event.ctrl or event.alt or event.shift:
                self._text_buffer += str(chord_num)
                self._invalidate_hit_boxes()
                self._tag_redraw()
                return {"RUNNING_MODAL"}

            if chord_num == 0:
                return {"RUNNING_MODAL"}
            idx = chord_num - 1
            if idx < len(self._filtered_mappings) and idx < 9:
                self._execute_mapping(context, self._filtered_mappings[idx])
                return {"FINISHED"}
            return {"RUNNING_MODAL"}

        elif event.type == "SPACE":
            self._text_buffer += " "
            self._invalidate_hit_boxes()
            self._tag_redraw()
            return {"RUNNING_MODAL"}

        elif event.type in {chr(i) for i in range(ord('A'), ord('Z') + 1)}:
            self._text_buffer += event.type.lower()
            self._invalidate_hit_boxes()
            self._tag_redraw()
            return {"RUNNING_MODAL"}

        # Punctuation needed for Chord Search prefix syntax (o:mesh.select_all)
        elif event.type == "SEMI_COLON":
            self._text_buffer += ":"
            self._invalidate_hit_boxes()
            self._tag_redraw()
            return {"RUNNING_MODAL"}

        elif event.type == "PERIOD":
            self._text_buffer += "."
            self._invalidate_hit_boxes()
            self._tag_redraw()
            return {"RUNNING_MODAL"}

        elif event.type == "MINUS":
            self._text_buffer += "_" if event.shift else "-"
            self._invalidate_hit_boxes()
            self._tag_redraw()
            return {"RUNNING_MODAL"}

        return {"RUNNING_MODAL"}

    def _invalidate_hit_boxes(self):
        try:
            from ..ui.overlay import clear_hit_boxes
            clear_hit_boxes()
        except Exception:
            pass

    def _execute_mapping(self, context, m, close=True):
        """Execute the selected mapping via a timer, closing unless told not to.

        Converts the mapping to a HistoryEntry and dispatches through the
        same helpers Recents uses, so all mapping types behave identically
        to a history replay. With close=False (Ctrl+click) the overlay stays
        open for chaining; the fading confirmation and history write are
        skipped, matching the scripts overlay's stay-open behavior.
        """
        from .leader import _show_fading_overlay
        from ..utils.render import (
            capture_viewport_context,
            validate_viewport_context,
            ContextWrapper,
            execute_history_entry_operator,
            execute_history_entry_script,
            execute_history_entry_toggle,
            execute_history_entry_property,
        )

        p = prefs(context)
        if getattr(m, "mapping_type", "OPERATOR") == "PYTHON_FILE" and not p.allow_custom_user_scripts:
            self.report({"ERROR"}, "Script execution is disabled. Enable 'Allow Custom User Scripts' in Preferences.")
            self._finish(context)
            return

        entry = _mapping_to_history_entry(m)

        # Capture viewport context BEFORE finishing the modal
        ctx_viewport = capture_viewport_context(context)
        entry.execution_context = ctx_viewport
        if close:
            self._finish(context)

        def execute_delayed():
            try:
                valid_ctx = validate_viewport_context(ctx_viewport) if ctx_viewport else None
                ctx_wrapper = ContextWrapper(valid_ctx) if valid_ctx else bpy.context

                if entry.mapping_type == "OPERATOR":
                    success, result = execute_history_entry_operator(ctx_wrapper, entry)
                    fade_label = entry.label if success else result
                elif entry.mapping_type == "PYTHON_FILE":
                    success, result = execute_history_entry_script(ctx_wrapper, entry)
                    fade_label = entry.label if success else result
                elif entry.mapping_type == "CONTEXT_TOGGLE":
                    success, result = execute_history_entry_toggle(ctx_wrapper, entry)
                    if success and result is not None:
                        fade_label = f"{entry.label} ({'ON' if result else 'OFF'})"
                    else:
                        fade_label = result if isinstance(result, str) else entry.label
                elif entry.mapping_type == "CONTEXT_PROPERTY":
                    success, result = execute_history_entry_property(ctx_wrapper, entry)
                    fade_label = f"{entry.label}: {entry.property_value}" if success else result
                else:
                    return None

                if not close:
                    # Stay-open path: no fade, no history — the user keeps
                    # chaining commands from the open overlay.
                    return None

                if success:
                    _show_fading_overlay(bpy.context, entry.chord_tokens, fade_label, entry.icon)
                    add_to_history(
                        chord_tokens=entry.chord_tokens,
                        label=entry.label,
                        icon=entry.icon,
                        mapping_type=entry.mapping_type,
                        operators=entry.operators,
                        python_file=entry.python_file,
                        script_args=entry.script_args,
                        context_path=entry.context_path,
                        property_value=entry.property_value,
                        execution_context=ctx_viewport,
                    )
                elif fade_label:
                    _show_fading_overlay(bpy.context, entry.chord_tokens, fade_label, "CANCEL")
            except Exception:
                import traceback
                traceback.print_exc()
            return None

        bpy.app.timers.register(execute_delayed, first_interval=0.01)
