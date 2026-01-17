"""Suggester module for generating chord suggestions."""
from ..common import prefs
import bpy  # type: ignore

def get_initials(text, max_chars=3):
    """Extract initials from text, max max_chars characters."""
    if not text:
        return ""
    # Remove common words and split
    words = text.lower().split()
    # Filter out very common words
    common = {"the", "a", "an", "to", "for", "of", "in", "on", "at", "by"}
    words = [w for w in words if w not in common]
    if not words:
        return ""

    # Get first letter of each word, up to max_chars
    initials = "".join(w[0] for w in words[:max_chars])
    return initials[:max_chars]

def spacify(text):
    """Add spaces between each character."""
    return " ".join(text) if text else ""

def has_prefix_conflict(candidate, existing_chords):
    """Check if a candidate chord has a prefix conflict with existing chords.
    
    A conflict exists if:
    - The candidate exactly matches an existing chord
    - The candidate is a prefix of an existing chord (blocks it)
    - An existing chord is a prefix of the candidate (blocks it)
    
    Args:
        candidate: The chord to check
        existing_chords: Set of existing chord strings
        
    Returns:
        True if there's a conflict, False otherwise
    """
    candidate_lower = candidate.strip().lower()
    
    for existing in existing_chords:
        existing_lower = existing.strip().lower()
        
        # Exact match
        if candidate_lower == existing_lower:
            return True
        
        # Check if candidate is a prefix of existing (e.g., "m p" blocks "m p c")
        if existing_lower.startswith(candidate_lower + " "):
            return True
        
        # Check if existing is a prefix of candidate (e.g., "m p c" blocked by "m p")
        if candidate_lower.startswith(existing_lower + " "):
            return True
    
    return False

def suggest_chord(group, label):
    """Generate a smart chord suggestion based on group and label.

    Args:
        group: The group name (e.g., "Object", "View")
        label: The label/operator name (e.g., "Select All")

    Returns:
        A non-conflicting chord string (e.g., "o a" for Object + Select All)
    """
    p = prefs(bpy.context)

    # Get existing chords for conflict checking
    existing_chords = set()
    for m in p.mappings:
        if m.enabled:
            existing_chords.add(m.chord.strip().lower())

    # Generate base chord from group + label
    group_initial = get_initials(group, 1)
    label_initials = get_initials(label, 2)

    if not group_initial or not label_initials:
        # Fallback to just label initials
        label_initials = get_initials(label, 3)
        if not label_initials:
            return ""
        candidates = [spacify(label_initials)]
    else:
        # Try various combinations
        candidates = [
            f"{group_initial} {spacify(label_initials)}",  # e.g., "o s a" for Object + Select All
            f"{group_initial} {label_initials[0]}",  # e.g., "o s"
            spacify(label_initials),  # Just label initials with spaces
        ]

    # Find first non-conflicting chord (including prefix conflicts)
    for candidate in candidates:
        if candidate and not has_prefix_conflict(candidate, existing_chords):
            return candidate

    # If all conflict, try adding a number suffix
    for candidate in candidates:
        if not candidate:
            continue
        for i in range(1, 10):
            numbered = f"{candidate} {i}"
            if not has_prefix_conflict(numbered, existing_chords):
                return numbered

    # Last resort: return empty and let user decide
    return ""
