"""UIList for the statistics tab."""

# pyright: reportMissingImports=false
# pylint: disable=import-error,broad-exception-caught

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


class CHORDSONG_UL_Stats(UIList):
    """Statistics rows: type, name, existing hotkey, count, blacklist toggle."""

    # Per-draw-cycle caches (invalidated in filter_items)
    _cached_blacklist: set = set()
    _blacklist_cache_valid = False
    _cached_hotkeys: dict = {}

    @classmethod
    def _get_blacklist(cls, prefs) -> set:
        if not cls._blacklist_cache_valid:
            cls._cached_blacklist = stats_store.parse_blacklist(
                getattr(prefs, "stats_blacklist", "[]")
            )
            cls._blacklist_cache_valid = True
        return cls._cached_blacklist

    @classmethod
    def _get_operator_hotkey(cls, idname: str) -> str:
        """First active keymap binding for an operator, e.g. 'Ctrl+A'."""
        if idname in cls._cached_hotkeys:
            return cls._cached_hotkeys[idname]

        hotkey = ""
        try:
            wm = bpy.context.window_manager
            for kc in (wm.keyconfigs.user, wm.keyconfigs.addon):
                if not kc:
                    continue
                for km in kc.keymaps:
                    for kmi in km.keymap_items:
                        if kmi.idname != idname or not kmi.active:
                            continue
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
                        if parts:
                            hotkey = '+'.join(parts)
                            break
                    if hotkey:
                        break
                if hotkey:
                    break
        except Exception:
            pass

        cls._cached_hotkeys[idname] = hotkey
        return hotkey

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
        # New draw cycle: invalidate caches
        cls = type(self)
        cls._blacklist_cache_valid = False
        cls._cached_hotkeys = {}
        return [], []
