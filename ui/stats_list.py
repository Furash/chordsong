"""UIList for the statistics tab."""

# pyright: reportMissingImports=false
# pylint: disable=import-error,broad-exception-caught

import time

import bpy
from bpy.types import UIList

from ..core import stats_store
from ..utils.addon_package import addon_root_package

# Relative column weights (split factors), not absolute units.
COL_ICON_WIDTH = 1.0
COL_CONVERT_WIDTH = 2.0
COL_INFO_WIDTH = 23.0
COL_HOTKEY_WIDTH = 4.0
COL_COUNT_WIDTH = 2.5
COL_BLACKLIST_WIDTH = 1.0

COL_WIDTHS = (
    COL_ICON_WIDTH,
    COL_CONVERT_WIDTH,
    COL_INFO_WIDTH,
    COL_HOTKEY_WIDTH,
    COL_COUNT_WIDTH,
    COL_BLACKLIST_WIDTH,
)


def _split_columns(layout, widths):
    """Fixed-ratio columns via nested splits (content can't shift them)."""
    cols = []
    container = layout
    remaining = sum(widths)
    for w in widths[:-1]:
        split = container.split(factor=w / remaining, align=True)
        cols.append(split.row(align=True))
        container = split.row(align=True)
        remaining -= w
    cols.append(container)
    return cols


TYPE_ICONS = {
    'chords': 'NODE_SOCKET_SHADER',
    'scripts': 'FILE_SCRIPT',
    'operators': 'SETTINGS',
    'properties': 'RNA',
}


# How long the shared idname -> hotkey map is reused. Keymaps change only
# when the user edits them or toggles an add-on, and the column is purely
# informational, so a short staleness window is a good trade for not
# walking every keymap on every redraw.
_HOTKEY_TTL_SECONDS = 5.0


def invalidate_hotkeys():
    """Force the hotkey column to re-read the keymaps on the next draw."""
    CHORDSONG_UL_Stats._hotkeys = None


class CHORDSONG_UL_Stats(UIList):
    """Statistics rows: type, name, existing hotkey, count, blacklist toggle."""

    # Per-draw-cycle cache (invalidated in filter_items)
    _cached_blacklist: set = set()
    _blacklist_cache_valid = False
    # Shared hotkey map, rebuilt at most every _HOTKEY_TTL_SECONDS
    _hotkeys = None
    _hotkeys_built = 0.0

    @classmethod
    def _get_blacklist(cls, prefs) -> set:
        if not cls._blacklist_cache_valid:
            cls._cached_blacklist = stats_store.parse_blacklist(
                getattr(prefs, "stats_blacklist", "[]")
            )
            cls._blacklist_cache_valid = True
        return cls._cached_blacklist

    @staticmethod
    def _format_hotkey(kmi) -> str:
        parts = []
        if kmi.ctrl:
            parts.append('Ctrl')
        if kmi.alt:
            parts.append('Alt')
        if kmi.shift:
            parts.append('Shift')
        if kmi.oskey:
            parts.append('Cmd' if bpy.app.build_platform == b'Darwin' else 'Win')
        key = (kmi.type or "").replace("_", " ")
        if key and key != 'NONE':
            parts.append(key if len(key) == 1 else key.title())
        return '+'.join(parts) if parts else ""

    @classmethod
    def _hotkey_map(cls) -> dict:
        """idname -> first active binding, for every operator at once.

        Built in a single pass over both keyconfigs. Looking each operator
        up on its own meant walking every keymap item per visible row —
        with a dozen rows on screen and a real keyconfig (thousands of
        items, more with add-ons) that dominated the frame while the
        preferences window was being dragged.

        Kept between draws because keymaps only change when the user edits
        them or toggles an add-on; the column is informational, so a few
        seconds of staleness costs nothing. `invalidate_hotkeys` forces it.
        """
        now = time.monotonic()
        if cls._hotkeys is not None and (now - cls._hotkeys_built) < _HOTKEY_TTL_SECONDS:
            return cls._hotkeys

        found = {}
        try:
            wm = bpy.context.window_manager
            # User config first, then addon: same precedence the per-row
            # lookup had, and the first binding seen for an idname wins.
            for kc in (wm.keyconfigs.user, wm.keyconfigs.addon):
                if not kc:
                    continue
                for km in kc.keymaps:
                    for kmi in km.keymap_items:
                        idname = kmi.idname
                        if not idname or idname in found or not kmi.active:
                            continue
                        hotkey = cls._format_hotkey(kmi)
                        if hotkey:
                            found[idname] = hotkey
        except Exception:
            pass

        cls._hotkeys = found
        cls._hotkeys_built = now
        return found

    @classmethod
    def _get_operator_hotkey(cls, idname: str) -> str:
        """First active keymap binding for an operator, e.g. 'Ctrl+A'."""
        return cls._hotkey_map().get(idname, "")

    def draw_item(self, context, layout, _data, item, _icon, _active_data, _active_propname):
        if self.layout_type == 'GRID':
            layout.alignment = 'CENTER'
            layout.label(text=str(item.count))
            return

        row = layout.row(align=True)
        cols = _split_columns(row, COL_WIDTHS)

        # Type indicator (RNA = property, SETTINGS = operator, ...)
        col = cols[0]
        col.label(text="", icon=TYPE_ICONS.get(item.category, 'BLANK1'))

        # Convert-to-chord button (operators and properties) / chord binding (chords)
        col = cols[1]
        if item.category in ('operators', 'properties'):
            sub = col.row(align=True)
            sub.alignment = 'LEFT'
            op = sub.operator("chordsong.stats_convert_to_chord", text="", icon='EVENT_C')
            op.stats_name = item.name
            op.stats_category = item.category
        elif item.category == 'chords':
            from ..operators.stats_operators import chord_display_text
            col.label(text=chord_display_text(item.name))
        else:
            col.label(text="")

        # Info
        col = cols[2]
        if item.category == 'chords':
            group = item.group or "(Ungrouped)"
            label = item.label or "(No label)"
            col.label(text=f"{group} : {label}")
        elif item.category == 'scripts':
            label = item.label or ""
            col.label(text=f"{item.name}     {label}" if label else item.name)
        elif item.category == 'properties':
            from ..core import stats_manager
            value = stats_manager.get_last_property_value(item.name)
            col.label(text=f"{item.name} = {value}" if value else item.name)
        else:
            col.label(text=item.name)

        # Existing hotkey (operators only)
        col = cols[3]
        col.label(text=self._get_operator_hotkey(item.name) if item.category == 'operators' else "")

        # Count
        col = cols[4]
        col.label(text=str(item.count))

        # Blacklist toggle
        col = cols[5]
        try:
            prefs = context.preferences.addons[addon_root_package(__package__)].preferences
            key = stats_store.blacklist_key(item.category, item.name)
            is_blacklisted = key in self._get_blacklist(prefs)
            op = col.operator(
                "chordsong.stats_blacklist",
                text="",
                icon='CHECKBOX_HLT' if is_blacklisted else 'TRASH',
                emboss=False,
            )
            op.action = 'TOGGLE'
            op.category = item.category
            op.name = item.name
        except (AttributeError, KeyError):
            col.label(text="")

    def filter_items(self, _context, _data, _propname):
        # New draw cycle: the blacklist is cheap to re-read and can change
        # from one draw to the next. The hotkey map is not re-read here —
        # see _hotkey_map for why.
        cls = type(self)
        cls._blacklist_cache_valid = False
        return [], []
