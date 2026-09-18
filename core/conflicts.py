"""Real-time chord conflict index for the preferences UI.

bpy-free (same layering rule as engine/contexts) so it is unit-testable.

Why this exists: the Mappings tab highlights conflicted chords, conflicted
groups and conflicted context tabs. Each of those used to ask "is this
mapping in conflict?" one mapping at a time, and each answer re-split every
chord string in the list — three O(n^2) passes of string work on every
redraw. The preferences region redraws every frame while the window is
dragged or resized, so at ~100 mappings that alone cost ~80 ms a frame.

Here the whole picture is built once per unique mapping list:

  * chords are tokenised once (O(n)),
  * exact duplicates are found by grouping equal token tuples,
  * prefix shadowing is found by looking each chord's own prefixes up in
    that same table — a chord can only be shadowed by one of its prefixes,
    so there is no need to compare every pair.

The result is a map of mapping index -> the set of indices it clashes with,
which answers every question the UI asks in constant time. It is memoised on
a cheap signature of the list, so repeat draws of unchanged data cost only
that signature.
"""

from .contexts import DEFAULT_CONTEXT, contexts_overlap
from .engine import get_str_attr, split_chord

# Longest chord we index prefixes for. Chords are a handful of tokens; the
# bound only stops a pathological entry from doing real work.
_MAX_CHORD_TOKENS = 16

_cache_signature = None
_cache_result = None


def mappings_signature(mappings):
    """Everything the conflict picture depends on: each mapping's chord,
    context and enabled flag, in order. Cheap to build (O(n) attribute
    reads) and exact — any edit that could change a conflict changes it."""
    return tuple(
        (get_str_attr(m, "chord"),
         getattr(m, "context", DEFAULT_CONTEXT) or DEFAULT_CONTEXT,
         bool(getattr(m, "enabled", True)))
        for m in mappings
    )


def build_conflict_map(mappings):
    """index -> set of other indices that mapping conflicts with.

    Two enabled mappings conflict when their contexts can be active at the
    same time (see core.contexts.contexts_overlap) and either their chords
    are identical, or one is a prefix of the other — a prefix always fires
    first, so the longer chord can never be reached.

    Mappings that are disabled or have no chord never conflict and are
    absent from the result.
    """
    tokens = {}          # index -> token tuple
    context_of = {}      # index -> context token
    by_chord = {}        # token tuple -> [index]

    for idx, m in enumerate(mappings):
        if not getattr(m, "enabled", True):
            continue
        chord = get_str_attr(m, "chord")
        if not chord:
            continue
        toks = tuple(split_chord(chord))
        if not toks or len(toks) > _MAX_CHORD_TOKENS:
            continue
        tokens[idx] = toks
        context_of[idx] = getattr(m, "context", DEFAULT_CONTEXT) or DEFAULT_CONTEXT
        by_chord.setdefault(toks, []).append(idx)

    conflicts = {}

    def _link(a, b):
        conflicts.setdefault(a, set()).add(b)
        conflicts.setdefault(b, set()).add(a)

    # Exact duplicates: every pair inside one bucket. Buckets are tiny in
    # practice (a chord is rarely bound more than a handful of times).
    for indices in by_chord.values():
        if len(indices) < 2:
            continue
        for i, a in enumerate(indices):
            for b in indices[i + 1:]:
                if contexts_overlap(context_of[a], context_of[b]):
                    _link(a, b)

    # Prefix shadowing: look up this chord's own proper prefixes rather
    # than comparing against every other chord.
    for idx, toks in tokens.items():
        for cut in range(1, len(toks)):
            for other in by_chord.get(toks[:cut], ()):
                if other != idx and contexts_overlap(context_of[idx], context_of[other]):
                    _link(idx, other)

    return conflicts


def conflict_map(mappings):
    """`build_conflict_map`, memoised on the mapping list's signature."""
    global _cache_signature, _cache_result  # pylint: disable=global-statement
    signature = mappings_signature(mappings)
    if signature != _cache_signature:
        _cache_result = build_conflict_map(mappings)
        _cache_signature = signature
    return _cache_result


def invalidate():
    """Drop the memoised picture (addon reload, config load, tests)."""
    global _cache_signature, _cache_result  # pylint: disable=global-statement
    _cache_signature = None
    _cache_result = None


def conflicted_indices(mappings):
    """Indices of every mapping currently in conflict."""
    return set(conflict_map(mappings))


def is_conflicted(mappings, index):
    """True when mappings[index] duplicates or shadows another chord."""
    return index in conflict_map(mappings)


def conflicts_with_any(conflicts, index, others):
    """True when `index` clashes with one of the `others` indices, given an
    already-built conflict map.

    Takes the map rather than the mapping list on purpose: a draw pass asks
    this once per row, and re-deriving the map each time means re-hashing
    the whole list, which is the quadratic cost this module exists to avoid.
    """
    partners = conflicts.get(index) if conflicts else None
    if not partners:
        return False
    return not partners.isdisjoint(others)


def contexts_with_conflicts(mappings, conflicts=None):
    """Context tokens holding at least one conflicted mapping — the tabs
    and rollout headers that should be drawn red. Pass `conflicts` when the
    caller already built the map for this draw."""
    if conflicts is None:
        conflicts = conflict_map(mappings)
    out = set()
    for idx in conflicts:
        try:
            out.add(getattr(mappings[idx], "context", DEFAULT_CONTEXT) or DEFAULT_CONTEXT)
        except Exception:  # pylint: disable=broad-exception-caught
            continue
    return out
