# Chords Sorting

Chord Song supports both **manual ordering** and **alphabetical sorting** of your chord mappings. The order you set in the preferences is reflected in both the UI and the main overlay.

<!-- markdownlint-disable MD033 -->
<video autoplay loop muted playsinline>
  <source src="/chordsong/scr/chords_sorting.mp4" type="video/mp4">
</video>
<!-- markdownlint-enable MD033 -->

## Manual Ordering

### Move Up/Down Buttons

Each chord mapping has **up** (⬆️) and **down** (⬇️) buttons to manually adjust its position within its group.

**Usage:**

1. Locate the chord you want to move
2. Click the **⬆️** button to move it up one position
3. Click the **⬇️** button to move it down one position

**Notes:**

- Changes are saved immediately
- Chords can only be moved within their own group
- The new order appears in both the UI and overlay
- Top/bottom chords cannot move further in that direction

### Sort Group Button

Each group header has a **Sort** button (AZ icon) that alphabetically sorts all chords within that group.

**Example:**

``` python
Before sorting:     After sorting:
─────────────       ─────────────
g g  → ...          a 1  → ...
a 1  → ...          a 2  → ...
k c  → ...          g g  → ...
a 2  → ...          k c  → ...
```

## Order Preservation

Your custom chord order is preserved:

- **Explicitly saved** - Each chord has an `order_index` field in the config file
- **Robust & resilient** - Order is a first-class property, not just array position
- **Reflected everywhere** - Visible in both the UI and overlay
- **Validated on load** - Config loading respects saved order, then normalizes indices
- **Search-safe** - Custom order maintained even when filtering
- **Auto-normalized** - Indices are kept sequential (0, 1, 2...) with no gaps or duplicates

## Workflow Tips

If you have many chords and want to organize them:

- Place frequently-used chords at the top
- Move frequently-used chords to the top of their group
- Keep related chords together
- Order them by workflow sequence
- Organize to match your mental model

## Technical Details

### Order Index Normalization

All `order_index` values are automatically normalized to match array positions (0, 1, 2, 3...) to ensure:

- **No gaps** - Sequential numbering with no missing indices
- **No duplicates** - Each chord has a unique index
- **Single-click moves** - Moving up/down works with one click
- **Predictable order** - Index always matches position

**Normalization runs during:**

- Config loading
- Config appending
- Chord pasting
- Move operations
- Sort operations

**Example:**

```json
Before normalization:       After normalization:
──────────────────          ───────────────────
{"order_index": 5, ...}  →  {"order_index": 0, ...}
{"order_index": 0, ...}  →  {"order_index": 1, ...}
{"order_index": 34, ...} →  {"order_index": 2, ...}
{"order_index": 50, ...} →  {"order_index": 3, ...}
```
