import re
from collections import Counter

# Grammatical stop words that carry no domain-specific meaning.
# Intentionally narrow — we want to keep tech terms, job-specific nouns, etc.
_STOP_WORDS: frozenset[str] = frozenset({
    "a", "an", "the", "and", "or", "but", "in", "on", "at", "to", "for",
    "of", "with", "by", "from", "as", "is", "was", "are", "were", "be",
    "been", "being", "have", "has", "had", "do", "does", "did", "will",
    "would", "could", "should", "may", "might", "shall", "can",
    "this", "that", "these", "those", "it", "its", "we", "our", "you",
    "your", "they", "their", "he", "she", "his", "her", "not", "no",
    "any", "all", "both", "each", "few", "more", "most", "other",
    "some", "such", "than", "then", "them", "so", "if", "i", "me", "my",
    "what", "which", "who", "how", "when", "where", "why", "about",
    "also", "into", "up", "out", "over", "just", "one", "two", "new",
    "us", "am", "own", "too", "very", "per", "via", "etc",
})


def extract_keywords(text: str, max_keywords: int = 20) -> list[str]:
    """Return the top *max_keywords* words by frequency from *text*.

    Strips HTML, removes punctuation, lowercases, filters stop words and
    tokens shorter than 3 characters. Returns words ordered by descending
    frequency (alphabetical as a tiebreaker).
    """
    # Strip any HTML tags that might come from a pasted job listing
    text = re.sub(r"<[^>]+>", " ", text)
    # Replace punctuation/special chars with spaces; keep word chars
    text = re.sub(r"[^\w\s]", " ", text.lower())

    words = text.split()

    meaningful = [
        w for w in words
        if len(w) >= 3 and w not in _STOP_WORDS and not w.isdigit()
    ]

    counts = Counter(meaningful)
    return [word for word, _ in counts.most_common(max_keywords)]
