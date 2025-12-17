"""History tracking for chord invocations.

Stores up to 88 recent commands (matching hotkey capacity: 1-9, a-z, A-Z, symbols)
"""

from collections import deque
from dataclasses import dataclass
from typing import Optional


@dataclass
class HistoryEntry:
    """Represents a single chord invocation in history."""
    chord_tokens: list  # List of tokens in the chord (e.g., ['g', 'g'])
    label: str  # The label/description of the command
    icon: str  # Optional icon
    mapping_type: str  # "OPERATOR", "PYTHON_FILE", or "CONTEXT_TOGGLE"
    # Operator-specific fields
    operator: Optional[str] = None
    kwargs: Optional[dict] = None
    call_context: Optional[str] = None
    # Python file-specific field
    python_file: Optional[str] = None
    # Context toggle-specific field
    context_path: Optional[str] = None


class ChordHistory:
    """Manages a limited history of chord invocations."""
    
    def __init__(self, max_size: int = 88):
        """Initialize history with maximum size."""
        self._history = deque(maxlen=max_size)
        self._max_size = max_size
    
    def add(self, entry: HistoryEntry):
        """Add a new entry to history (most recent at the front)."""
        # Check if this exact chord is already at the front
        # If so, don't add it again (avoid duplicate consecutive entries)
        if self._history and self._are_entries_equal(self._history[0], entry):
            return
        
        # Add to front of deque
        self._history.appendleft(entry)
    
    def _are_entries_equal(self, entry1: HistoryEntry, entry2: HistoryEntry) -> bool:
        """Check if two entries represent the same command."""
        if entry1.mapping_type != entry2.mapping_type:
            return False
        
        if entry1.mapping_type == "OPERATOR":
            return (entry1.operator == entry2.operator and 
                    entry1.kwargs == entry2.kwargs)
        elif entry1.mapping_type == "PYTHON_FILE":
            return entry1.python_file == entry2.python_file
        elif entry1.mapping_type == "CONTEXT_TOGGLE":
            return entry1.context_path == entry2.context_path
        
        return False
    
    def get_all(self) -> list:
        """Get all history entries (most recent first)."""
        return list(self._history)
    
    def get(self, index: int) -> Optional[HistoryEntry]:
        """Get entry at specific index (0-based, 0 is most recent)."""
        if 0 <= index < len(self._history):
            return self._history[index]
        return None
    
    def clear(self):
        """Clear all history."""
        self._history.clear()
    
    def __len__(self):
        """Return number of entries in history."""
        return len(self._history)


# Global history instance (88 = 9 + 26 + 26 + 10 + 3 + 14 punctuation)
_global_history = ChordHistory(max_size=88)


def get_history() -> ChordHistory:
    """Get the global history instance."""
    return _global_history


def add_to_history(
    chord_tokens: list,
    label: str,
    icon: str,
    mapping_type: str,
    operator: Optional[str] = None,
    kwargs: Optional[dict] = None,
    call_context: Optional[str] = None,
    python_file: Optional[str] = None,
    context_path: Optional[str] = None,
):
    """Convenience function to add an entry to global history."""
    entry = HistoryEntry(
        chord_tokens=chord_tokens,
        label=label,
        icon=icon,
        mapping_type=mapping_type,
        operator=operator,
        kwargs=kwargs,
        call_context=call_context,
        python_file=python_file,
        context_path=context_path,
    )
    _global_history.add(entry)
