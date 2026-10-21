- [ ] Create a CONTEXT_TOGGLE mapping with `context_path = "show_stats"` (no dot). Fire it by keyboard chord. **Expected:** a WARNING in the Info panel mentioning the bad path; no crash. (`ui/default_mappings.json` uses the correct `space_data.overlay.show_stats` — this is a deliberate malformed test.)


- [ ] With `scripts_folder` set, create a PYTHON_FILE mapping pointing to a script **outside** the folder (e.g. `C:/Temp/evil.py`). Trigger it. **Expected:** ERROR in Info panel mentioning the rejected path and the allowed scripts folder; script does NOT run.

- [ ] Create a PYTHON_FILE mapping to a path that does not exist. Trigger it. **Expected:** ERROR visible in Info panel (not just stdout); overlay closes. Watch for `_safe_report` path (`operators/leader.py:879`).

- [ ] Create a SUB_OPERATOR entry inside a CONTEXT_MENU with a deliberately malformed op string. Trigger the context menu. **Expected:** WARNING on the malformed item; other items in the menu still work.

- [ ] Leader key round-trip: set leader to `TAB` in prefs, **Save Config**, set leader back to `Space`, **Load Config**. **Expected:** leader is `TAB` again; Info panel shows "Leader key set to TAB". Then restart Blender (or disable/enable the addon). **Expected:** startup auto-load does NOT change the leader key. **Export Config** the same setup and inspect the JSON. **Expected:** no `leader_key` entry.


## Multi-editor contexts (1.3)

Blender GUI, Chord Song preferences open, ideally 100+ chords loaded.

**Mappings tab — context selector**

- [ ] Prefs window narrower than ~1500 px, then wider. **Expected:** editor rows switch from one column to two; no horizontal jerk on redraw.
- [ ] Inspect the rows. **Expected:** every editor button ends at the same x, mode chips line up in columns, key fields start at the same x; chips are icon + count, "0" where empty, never a hole; hovering a chip names its mode.
- [ ] Click the 3D View button, then the Sculpt chip. **Expected:** the button selects Object (button and Object chip lit); Sculpt then lit instead; the count on a chip matches the rows listed.
- [ ] Inspect the Edit Modes row under 3D View. **Expected:** eight chips, Mesh first; clicking its button selects Mesh; 3D View's count excludes the Edit Modes count.
- [ ] Click the button of a single-context editor (NLA). **Expected:** selected, lit, no chips.
- [ ] Select the Global tab. **Expected:** Global box highlighted, same as a selected chip.
- [ ] Create a conflict inside one editor. **Expected:** that editor's button and the offending chip are red; other chips are not.
- [ ] Movie Clip editor: Tracking mode with Clip, Graph and Dope Sheet views, then Mask mode. **Expected:** the leader overlay lists that view's chords only; a Tracking chord does not fire in Mask mode.

**Leader key**

- [ ] Inspect any editor row, 3D View included. **Expected:** the key cell at the end (key icon, field, Override icon), greyed while it follows the default.
- [ ] 3D View → Override → set Tab. **Expected:** Leader Key (default) still shows Space; Tab opens the leader in the 3D View, Space does not; Space still works in the other editors. Reset → back to Space.
- [ ] Restart Blender after changing the default key. **Expected:** the default field and every following editor still show the new key.
- [ ] Change the default leader (Space → Tab). **Expected:** every non-overridden editor shows Tab, greyed; one Info-panel message, not one per editor.
- [ ] Sequencer → Override → set Ctrl+Space. Change the default back to Space. **Expected:** Sequencer keeps Ctrl+Space, un-greyed. Reset → back to Space, greyed, no stray Ctrl.
- [ ] Press Ctrl+Space in the Sequencer, Space in the 3D View. **Expected:** leader overlay opens in each.

**Mapping list**

- [ ] Search a term with no hits. **Expected:** "No chord here matches …", not "No mappings in this context yet".
- [ ] Select an editor with no chords of its own (Movie Clip). **Expected:** hint reads "N chord(s) from Global are active here".
- [ ] On the Global tab, make a Global chord clash with a 3D View chord. **Expected:** the 3D View row appears greyed with "3D View chord — open its tab"; clicking it lands on the 3D View tab with the row visible.
- [ ] Expand a row. **Expected:** Context dropdown wider than Type dropdown. Change Context to Video Sequencer. **Expected:** the tab follows to Video Sequencer; the row stays on screen.
- [ ] Conflict inside a group. **Expected:** group header red.
- [ ] Check for Conflicts → Go to Chord on a duplicate (and the magnifier on a prefix row). **Expected:** Mappings tab, context tab of the chord selected, search reads `c:<chord>`, both conflicting rows unfolded. From the Global tab on a Global-vs-3D View clash. **Expected:** lands on the 3D View tab, Global row listed read-only.

**Contexts dialog (globe icon)**

- [ ] Globe on a Sequencer chord. **Expected:** 3-column grid, Video Sequencer ticked, Sequencer Preview greyed with a note. Tick NLA → OK. **Expected:** copy appears in the NLA tab; warning if NLA already binds that chord.
- [ ] Globe → untick everything → OK. **Expected:** warning, nothing removed.
- [ ] Globe → Make Global on a chord that has copies in several editors. **Expected:** copies merge into one Global row.

**Add Chord (right-click) and Stats convert**

- [ ] Right-click a button in the Sequencer → Add Chord Mapping. **Expected:** Video Sequencer pre-ticked. Same from the Properties editor. **Expected:** only 3D View ticked, no second copy.
- [ ] Leave the chord empty → OK. **Expected:** warning; typed fields kept, not silently discarded.
- [ ] Right-click an operator button → Add Chord Mapping. **Expected:** Call row (Invoke | Exec) under Parameters, Invoke preselected; absent for toggle/property mappings. Pick Exec → OK. **Expected:** new mapping shows Exec in the Mappings tab; reopening the dialog resets to Invoke.
- [ ] Statistics tab → Convert to Chord. **Expected:** 3-column context grid including Global.

**Runtime**

- [ ] Fire a chord in the Sequencer. **Expected:** confirmation overlay in the Sequencer, not in the 3D View.
- [ ] Open Recents in the Graph Editor; then with Dope Sheet and Timeline side by side. **Expected:** overlay only in the invoking area.
- [ ] Open the leader overlay in the Compositor and the Image Editor with panel hiding on. **Expected:** T/N panels hide and restore with Blender's own animation. (Sequencer snaps — native, expected.)
- [ ] Bind Close Overlay to a single key in the Shader Editor only; open the leader overlay in the 3D View and press it. **Expected:** overlay stays open.

**Performance**

- [ ] Mappings tab with 100+ chords, drag the preferences window. **Expected:** smooth.
- [ ] Statistics tab with 12+ rows, drag. **Expected:** smooth; hotkey column populated.

- [ ] All items above checked.
- [ ] Info panel reviewed for unexpected errors/warnings during the run.
- [ ] `python tests/runall.py` exit 0 one more time from a clean clone.
