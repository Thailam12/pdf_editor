import os
import json


class SpellCheckService:
    def __init__(self, editor):
        self.editor = editor
        self._language = "en"
        self._custom_dictionary = set()
        self._enchant_available = False
        self._checker = None
        self._builtin_dict_path = os.path.join(
            os.path.dirname(__file__), "..", "data", "dictionary.txt"
        )
        self._builtin_words = set()
        self._init_checker()

    def _init_checker(self):
        """Initialize the spell checker."""
        try:
            import enchant
            self._checker = enchant.Dict(self._language)
            self._enchant_available = True
        except ImportError:
            self._enchant_available = False
            self._load_builtin_dict()

    def _load_builtin_dict(self):
        """Load a basic built-in dictionary for fallback spell checking."""
        basic_words = {
            "the", "a", "an", "and", "or", "but", "in", "on", "at", "to",
            "for", "of", "with", "by", "from", "is", "are", "was", "were",
            "be", "been", "being", "have", "has", "had", "do", "does", "did",
            "will", "would", "could", "should", "may", "might", "can", "shall",
            "this", "that", "these", "those", "it", "its", "you", "your",
            "we", "our", "they", "their", "he", "she", "his", "her",
            "not", "no", "if", "then", "else", "when", "where", "how",
            "what", "which", "who", "whom", "whose", "why",
            "all", "each", "every", "both", "few", "more", "most", "other",
            "some", "such", "than", "too", "very", "just", "about",
            "above", "after", "again", "also", "any", "because", "before",
            "between", "come", "day", "does", "down", "during", "even",
            "find", "first", "get", "give", "go", "here", "home", "into",
            "know", "last", "left", "let", "life", "like", "line", "long",
            "look", "made", "make", "many", "may", "men", "new", "now",
            "old", "only", "our", "out", "over", "own", "part", "place",
            "point", "right", "said", "same", "say", "see", "still",
            "take", "tell", "time", "two", "under", "upon", "use", "very",
            "want", "way", "well", "work", "year", "back", "being", "call",
            "good", "great", "hand", "high", "keep", "kind", "large",
            "little", "near", "need", "next", "open", "read", "small",
            "since", "start", "tell", "turn", "upon", "us", "water",
        }
        self._builtin_words = basic_words
        if os.path.exists(self._builtin_dict_path):
            try:
                with open(self._builtin_dict_path, "r", encoding="utf-8") as f:
                    for line in f:
                        self._builtin_words.add(line.strip().lower())
            except Exception:
                pass

    def check_word(self, word):
        """Check if a word is spelled correctly. Returns True if correct."""
        try:
            if word.lower() in self._custom_dictionary:
                return True
            if self._enchant_available and self._checker:
                return self._checker.check(word)
            return word.lower() in self._builtin_words
        except Exception:
            return True

    def suggest_corrections(self, word):
        """Return a list of suggested corrections for a misspelled word."""
        try:
            if self._enchant_available and self._checker:
                return self._checker.suggest(word)
            suggestions = []
            for w in self._builtin_words:
                if len(w) == len(word) and sum(a != b for a, b in zip(w, word.lower())) <= 2:
                    suggestions.append(w)
            return suggestions[:10]
        except Exception:
            return []

    def check_text(self, text):
        """Check text and return list of dicts with word, suggestions, position."""
        results = []
        if not text:
            return results
        words = text.split()
        offset = 0
        for word in words:
            clean = word.strip(".,;:!?\"'()-")
            pos = text.find(word, offset)
            if clean and not self.check_word(clean):
                results.append({
                    "word": clean,
                    "suggestions": self.suggest_corrections(clean),
                    "position": pos if pos >= 0 else offset
                })
            if pos >= 0:
                offset = pos + len(word)
        return results

    def add_to_dictionary(self, word):
        """Add a custom word to the personal dictionary."""
        try:
            self._custom_dictionary.add(word.lower())
            if self._enchant_available and self._checker:
                try:
                    self._checker.add(word)
                except Exception:
                    pass
        except Exception as e:
            raise RuntimeError(f"Cannot add word to dictionary: {e}")

    def remove_from_dictionary(self, word):
        """Remove a word from the personal dictionary."""
        try:
            self._custom_dictionary.discard(word.lower())
            if self._enchant_available and self._checker:
                try:
                    self._checker.remove(word)
                except Exception:
                    pass
        except Exception as e:
            raise RuntimeError(f"Cannot remove word from dictionary: {e}")

    def set_language(self, lang_code):
        """Set the spell check language. Supports 'en' and 'vi'."""
        try:
            self._language = lang_code
            if self._enchant_available:
                try:
                    import enchant
                    self._checker = enchant.Dict(lang_code)
                except Exception:
                    self._enchant_available = False
                    self._load_builtin_dict()
            else:
                self._load_builtin_dict()
        except Exception as e:
            raise RuntimeError(f"Cannot set language: {e}")
