- [ ] Create a CONTEXT_TOGGLE mapping with `context_path = "show_stats"` (no dot). Fire it by keyboard chord. **Expected:** a WARNING in the Info panel mentioning the bad path; no crash. (`ui/default_mappings.json` uses the correct `space_data.overlay.show_stats` — this is a deliberate malformed test.)


- [ ] With `scripts_folder` set, create a PYTHON_FILE mapping pointing to a script **outside** the folder (e.g. `C:/Temp/evil.py`). Trigger it. **Expected:** ERROR in Info panel mentioning the rejected path and the allowed scripts folder; script does NOT run.

- [ ] Create a PYTHON_FILE mapping to a path that does not exist. Trigger it. **Expected:** ERROR visible in Info panel (not just stdout); overlay closes. Watch for `_safe_report` path (`operators/leader.py:879`).

- [ ] Create a SUB_OPERATOR entry inside a CONTEXT_MENU with a deliberately malformed op string. Trigger the context menu. **Expected:** WARNING on the malformed item; other items in the menu still work.


- [ ] All items above checked.
- [ ] Info panel reviewed for unexpected errors/warnings during the run.
- [ ] `python tests/runall.py` exit 0 one more time from a clean clone.
