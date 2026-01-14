"""Fuzzy matching utilities."""

def fuzzy_match(query: str, text: str) -> tuple[bool, int]:
    """
    Fuzzy match query against text.
    Returns (matched, score) where lower score is better.
    Allows words in the query to appear in any order in the text.
    """
    if not query:
        return True, 0

    # Normalize: lowercase and treat underscores as spaces
    query = query.lower().replace('_', ' ')
    text = text.lower().replace('_', ' ')

    # 1. Quick full substring check (best match)
    if query in text:
        return True, text.index(query) * 10

    # 2. Word-based matching (allows any order)
    words = query.split()
    total_score = 0
    
    for word in words:
        # Check if this word exists in the text as a substring
        if word in text:
            # Score based on position
            total_score += text.index(word) * 10
        else:
            # Fallback to fuzzy character-by-character matching for this word
            word_idx = 0
            text_idx = 0
            word_score = 0
            while word_idx < len(word) and text_idx < len(text):
                if word[word_idx] == text[text_idx]:
                    word_score += text_idx
                    word_idx += 1
                text_idx += 1
            
            if word_idx == len(word):
                # Word matched fuzzily
                total_score += (word_score * 5) + 500  # Penalty for non-substring match
            else:
                # This word didn't match at all
                return False, float('inf')

    # Bonus: Penalize if words are in a different order than typed
    # (Simplified: just use the total accumulated score)
    return True, total_score
