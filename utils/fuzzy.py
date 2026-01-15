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
            # Stricter: require characters to appear in order and relatively close together
            word_idx = 0
            text_idx = 0
            word_score = 0
            last_match_idx = -1
            max_gap = max(2, len(word) // 2)  # Stricter: smaller gaps allowed
            
            # Require first character to match (makes matching much stricter)
            first_char_found = False
            while text_idx < len(text) and not first_char_found:
                if word[0] == text[text_idx]:
                    first_char_found = True
                    word_idx = 1
                    word_score += text_idx
                    last_match_idx = text_idx
                    text_idx += 1
                    break
                text_idx += 1
            
            if not first_char_found:
                # First character must match
                return False, float('inf')
            
            # Continue matching remaining characters
            while word_idx < len(word) and text_idx < len(text):
                if word[word_idx] == text[text_idx]:
                    # Check if gap is too large
                    gap = text_idx - last_match_idx
                    if gap > max_gap:
                        # Gap too large, this is not a good match
                        break
                    word_score += text_idx
                    last_match_idx = text_idx
                    word_idx += 1
                text_idx += 1
            
            if word_idx == len(word):
                # Word matched fuzzily, but with stricter requirements
                # Heavily penalize non-substring matches
                gap_penalty = sum(range(1, word_idx)) * 50  # Penalty increases with word length
                total_score += (word_score * 10) + 2000 + gap_penalty  # Much higher penalty
            else:
                # This word didn't match at all
                return False, float('inf')

    # Bonus: Penalize if words are in a different order than typed
    # (Simplified: just use the total accumulated score)
    return True, total_score
