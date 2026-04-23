- [ ] Create a CONTEXT_TOGGLE mapping with `context_path = "show_stats"` (no dot). Fire it by keyboard chord. **Expected:** a WARNING in the Info panel mentioning the bad path; no crash. (`ui/default_mappings.json` uses the correct `space_data.overlay.show_stats` — this is a deliberate malformed test.)


- [ ] With `scripts_folder` set, create a PYTHON_FILE mapping pointing to a script **outside** the folder (e.g. `C:/Temp/evil.py`). Trigger it. **Expected:** ERROR in Info panel mentioning the rejected path and the allowed scripts folder; script does NOT run.

- [ ] Create a PYTHON_FILE mapping to a path that does not exist. Trigger it. **Expected:** ERROR visible in Info panel (not just stdout); overlay closes. Watch for `_safe_report` path (`operators/leader.py:879`).

- [ ] Create a SUB_OPERATOR entry inside a CONTEXT_MENU with a deliberately malformed op string. Trigger the context menu. **Expected:** WARNING on the malformed item; other items in the menu still work.

- [ ] Re-trigger a Recents entry whose underlying mapping was edited to be malformed AFTER the entry was recorded. **Expected:** the cached HistoryEntry still executes the ORIGINAL (pre-edit) operators — Recents replay uses the cached `operators` list, not a live lookup against the current mapping. This is by design: `core/history.py` is in-memory only, no persistence; entries snapshot the call at fire time. (Previous version of this item assumed config-level recents persistence that doesn't exist.)

- [ ] Locate `chordsong.autosave.json` next to your `config_path`. Delete it if present.
- [ ] Edit any mapping (e.g. change a label) to trigger autosave. Wait the debounce (~1s).
- [ ] **Expected:** `chordsong.autosave.json` exists and is valid JSON (open in a text editor — final char is `}` followed by newline, full structure present).
- [ ] **Expected:** no `chordsong.autosave.json.tmp` file left behind in the same directory after a successful write.
- [ ] Make another mapping edit, immediately Ctrl+C the Blender process mid-write (best effort — repeat a few times with fast edits). Relaunch Blender. **Expected:** `chordsong.autosave.json` is either the previous good version or the new good version — never a zero-byte or truncated file. A leftover `.tmp` is acceptable after a crash but the main file must still parse.

---

## 9. Panel hide / restore (commit `5a3e7f4`, handoff at `utils/panels.py:176`)

- [ ] In a 3D View, make sure T panel (toolbar), N panel (sidebar), HUD, and Asset Shelf are all visible.
- [ ] Press Space. **Expected:** T, N, HUD, Asset Shelf all hide immediately.
- [ ] Press ESC. **Expected:** all four regions restore to their previous visible state.
- [ ] Repeat, but instead of ESC, complete a chord that opens Recents. **Expected:** panels remain hidden during the leader->recents transition (no mid-flash).
- [ ] Close the Recents modal (ESC). **Expected:** panels restore now.
- [ ] Repeat with a chord that opens the scripts overlay. **Expected:** panels stay hidden through leader->scripts-overlay; they restore only when the scripts overlay closes.
- [ ] Start with one of the four regions already hidden (e.g. N panel closed). Invoke overlay, close it. **Expected:** that region stays hidden (original state preserved, not force-shown).

---

## 10. Blinker hot-reload safety (commit `e0cbff3`)

*Skip this section if blinker is not installed. Otherwise:*

- [ ] Enable blinker auto-reload for the addon. Press Space to bring up the leader overlay.
- [ ] With the overlay visible, touch any `.py` file in the addon (e.g. add a trailing newline to `operators/leader.py`). **Expected:** blinker reloads; no `ReferenceError: StructRNA of type CHORDSONG_OT_Leader has been removed` in the console. Overlay may disappear — that's fine, the test is no crash.
- [ ] Repeat with the scripts overlay visible. **Expected:** no `ReferenceError` from `CHORDSONG_OT_ScriptsOverlay` draw callback.
- [ ] Toggle `allow_custom_user_scripts` in prefs while blinker reload is pending / mid-reload. **Expected:** no `ValueError: the return value must be None` from the property update callback (the lambda-tuple fix).

---

## 11. Close flow & miscellaneous (commits `6a06074`, `0c3eac1`)

- [ ] Open leader, flip a toggle via click, middle-click anywhere. **Expected:** middle-click does NOT revert the toggled value (regression guard — the earlier overlay-clicks branch had a middle-click-revert behavior that should not resurface).
- [ ] Open leader, press ESC. **Expected:** overlay closes, panels restore, no stale timers (check with the "Reset Chord Song State" operator if present — should report 0 timers removed immediately after ESC).
- [ ] Open the addon's UI tab. **Expected:** the box previously labeled "Debug Tools" now reads "Previews & Tools" (commit `0c3eac1`, `ui/layout/ui_tab.py:205`).

---

## 12. Keymap accessors (refactor `f3d16fc`, re-exports in `ui/keymap.py`)

- [ ] In prefs, change the leader key from Space to Grave Accent. Press the new key. **Expected:** overlay opens on Grave Accent.
- [ ] Restart Blender. **Expected:** leader still on Grave Accent (user keyconfig persisted).
- [ ] Disable addon, re-enable. **Expected:** leader still on Grave Accent (both user and addon keyconfigs updated by `set_leader_key_in_keymap`).
- [ ] Check footer display of leader token (e.g. a "next leader press repeats last chord" hint if present). **Expected:** shows the current leader glyph, not "<Leader>".

---

## 13. Refactor regression sweep (commits `5a3e7f4`, `625dcfe`, `74511ec`, `f289301`, `d20743e`, `353b89e`, `f3d16fc`)

These are pure refactors — no behavior change intended. Sanity-check by running ONE end-to-end path that exercises the moved code:

- [ ] Open leader, type a 3-key chord, watch overlay update per keystroke. **Expected:** overlay re-renders on each key (exercises extracted `utils/redraw.py:tag_redraw_all_areas`).
- [ ] Open leader in a region, move mouse to a different area, click. **Expected:** the invoke-region check in `operators/common.py:event_in_invoke_region` routes the click correctly (exercises deduped `ContextWrapper`/`ContextWithRegion`).
- [ ] Trigger the fading-overlay path (a post-execute fade if present). **Expected:** fade renders and cleans up (exercises extracted `operators/fading_overlay.py`).
- [ ] After ESC, re-open leader. **Expected:** prior class-level sentinels (now `None`, commit `f289301`) reset cleanly — no stale state leaking from previous invocation.

---

**Before merging:**
- [ ] All items above checked.
- [ ] Info panel reviewed for unexpected errors/warnings during the run.
- [ ] `python tests/runall.py` exit 0 one more time from a clean clone.
