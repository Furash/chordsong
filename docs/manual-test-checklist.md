# Manual Test Checklist — `refactor/improving` -> `master`

Covers the 22 commits between `master` and `refactor/improving`. Run each step in a fresh Blender session (5.0+). Each item is meant to take under a minute. Use Window > Toggle System Console (Windows) or launch Blender from a terminal to watch stdout alongside the Info panel.

**Setup once before starting:**
- [ ] Install the addon from the `refactor/improving` checkout and enable it in Preferences > Add-ons.
- [ ] Open the Info editor (or Window > Scripting so you can see reports).
- [ ] Note your current `config_path` from addon prefs — you'll need it for autosave checks.

---

## 1. Automated tests green (commit `41d0c29`)

- [ ] From a terminal, run `python D:/git/chordsong/tests/runall.py`. **Expected:** exit 0, final line reports `49 passed, 0 failed` (checklist spec said 34; the branch has since added more — treat anything >= 34 with 0 failed as pass).

---

## 2. Toggle click flow (commits `180a51d`, `c8c435b`, `b590805`, `6a06074`, `d37c248`)

- [ ] Press Space to open the leader overlay. **Expected:** footer shows `M1 Toggle` hint (new in `d37c248`) alongside `ESC Close`.
- [ ] Left-click a toggle row backed by a Blender-native prop (e.g. `space_data.overlay.show_stats` via `space o s` row). **Expected:** value flips, overlay stays open, footer still visible.
- [ ] Click the same toggle again. **Expected:** flips back; no "first click does nothing" behavior (regression guard for `180a51d` / `c8c435b`).
- [ ] Click the toggle 5 times as fast as possible. **Expected:** final state = original XOR (odd count). No rubber-banding, no reverts. Watch Info panel for errors.
- [ ] Add a mapping backed by a custom addon property (pick any enabled addon's BoolProperty — e.g. `preferences.addons['cycles'].preferences.use_oidn` or similar). Click it once in the overlay. **Expected:** flips on first click and persists (regression guard for `b590805` / `c8c435b` — the custom-prop rollback bug).
- [ ] Hold the configured `toggle_multi_modifier` (default CTRL) and left-click a toggle row. **Expected:** same behavior as plain click (commit `6a06074` deliberately removed modifier branching on the click path; overlay still stays open either way).
- [ ] Create a CONTEXT_TOGGLE mapping with `context_path = "show_stats"` (no dot). Fire it by keyboard chord. **Expected:** a WARNING in the Info panel mentioning the bad path; no crash. (`ui/default_mappings.json` uses the correct `space_data.overlay.show_stats` — this is a deliberate malformed test.)
- [ ] Click a toggle, then **click outside** the invoke region (a different area, e.g. the Outliner). **Expected:** click does NOT fire the toggle; the overlay closes (or ignores per spec) — no stray toggle flip in the other area.

---

## 3. Keyboard chord toggles (unchanged path, regression check)

- [ ] Trigger a toggle via keyboard chord, e.g. `Space o s` (overlay stats). **Expected:** toggles exactly once, overlay closes.
- [ ] Hold the `toggle_multi_modifier` (CTRL by default) while completing the chord. **Expected:** executes the "multi" variant per the mapping (e.g. toggles all paths) — leader.py:906 path unchanged by this branch.

---

## 4. Scripts overlay (commits `d8dcbcb`, `d37c248`, `6ab51d1`, `5b2fad6`)

- [ ] In addon prefs enable `allow_custom_user_scripts` and set `scripts_folder` to a new empty folder. Drop two `.py` files into it (one prints "A", one prints "B").
- [ ] Open the scripts overlay (via its chord or test UI). **Expected footer text:** `M1 Run script` and `^M1 Run + keep overlay open` (commit `d37c248` — earlier `d8dcbcb` said "Run" / "Stay open", superseded).
- [ ] Left-click script A. **Expected:** A runs (see its print in console), overlay closes.
- [ ] Reopen, CTRL+left-click script A. **Expected:** A runs, overlay stays open.
- [ ] While overlay still open from previous step, CTRL+click script B. **Expected:** B also runs, overlay still open.
- [ ] Press ESC. **Expected:** overlay closes cleanly.

---

## 5. Script path confinement (commit `6ab51d1`, tests in `test_is_script_path_allowed.py`)

- [ ] With `scripts_folder` set, create a PYTHON_FILE mapping pointing to a script **outside** the folder (e.g. `C:/Temp/evil.py`). Trigger it. **Expected:** ERROR in Info panel mentioning the rejected path and the allowed scripts folder; script does NOT run.
- [ ] Move that same script INTO `scripts_folder`, update the mapping, re-trigger. **Expected:** script runs without error.
- [ ] Clear `scripts_folder` in prefs (empty string). Point a mapping at a script anywhere on disk, trigger it. **Expected:** runs (confinement off when folder is unset — legacy behavior preserved).
- [ ] Set `scripts_folder`, then craft a mapping whose path uses `..` to escape (e.g. `<scripts_folder>/../evil.py`). Trigger. **Expected:** ERROR — `realpath`-based check blocks traversal.

---

## 6. Failure surfaces (commit `5b2fad6`)

- [ ] Create a PYTHON_FILE mapping to a path that does not exist. Trigger it. **Expected:** ERROR visible in Info panel (not just stdout); overlay closes. Watch for `_safe_report` path (`operators/leader.py:879`).
- [ ] Create a SUB_OPERATOR entry inside a CONTEXT_MENU with a deliberately malformed op string. Trigger the context menu. **Expected:** WARNING on the malformed item; other items in the menu still work.
- [ ] Trigger a recents re-entry with recents intentionally corrupt (close Blender, edit the config to have a bad recents entry, re-open). **Expected:** ERROR `Failed to open recents:` with the exception text.

---

## 7. `allow_custom_user_scripts` persistence & quarantine (commits `6ab51d1`, `809d4b1`, `e0cbff3`)

- [ ] In prefs, enable `allow_custom_user_scripts`. Disable the addon, re-enable it. **Expected:** flag is still ON (sidecar `allow_custom_user_scripts.flag` next to `config_path.txt` persisted it).
- [ ] With flag ON, quit Blender, relaunch. **Expected:** flag still ON.
- [ ] With flag ON, toggle it OFF in prefs. Disable/re-enable addon. **Expected:** flag still OFF. Verify `allow_custom_user_scripts.flag` exists and reflects the latest state.
- [ ] Export your current config to JSON. Manually edit the exported file to set `"allow_custom_user_scripts": true`. Turn the flag OFF in prefs. Load that config via Load Config. **Expected:** flag stays OFF (quarantine); a WARNING appears in Info panel that the flag was stripped from the imported config.
- [ ] Repeat the previous step via Load Default / Load Autosave paths. **Expected:** same quarantine behavior — the flag is never silently enabled from JSON.
- [ ] Toggle the flag in prefs rapidly (fast clicks). **Expected:** no `ValueError: return value must be None` in console (regression guard for `e0cbff3` — the lambda-returning-tuple bug).

---

## 8. Atomic autosave (commit `29ebcfa`)

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
