import os
import re
import json
import hashlib
from collections import defaultdict

import pymupdf


class AdvancedSpellCheckService:
    def __init__(self, editor):
        self.editor = editor
        self._language = "en"
        self._enchant_available = False
        self._checker = None
        self._custom_dictionary = set()
        self._ignore_list = set()
        self._auto_correct = False
        self._auto_correct_map = {}
        self._supported_languages = [
            "en", "es", "fr", "de", "it", "pt", "nl", "ru", "zh", "ja",
            "ko", "pl", "cs", "sv", "da", "no", "fi", "hu", "ro", "tr",
            "el", "bg", "hr", "sk", "sl", "uk", "ar", "he", "th", "vi",
        ]
        self._context_suggestions = {
            "teh": "the",
            "taht": "that",
            "recieve": "receive",
            "occured": "occurred",
            "seperate": "separate",
            "definately": "definitely",
            "accomodate": "accommodate",
            "occurence": "occurrence",
            "neccessary": "necessary",
            "acheive": "achieve",
            "adn": "and",
            "nto": "not",
            "nad": "and",
            "fo": "of",
            "wiht": "with",
            "thier": "their",
            "beacuse": "because",
            "wierd": "weird",
            "untill": "until",
            "arguement": "argument",
            "embarass": "embarrass",
        }
        self._init_checker()

    def _init_checker(self):
        try:
            import enchant
            self._checker = enchant.Dict(self._language)
            self._enchant_available = True
        except (ImportError, Exception):
            self._enchant_available = False

    def set_language(self, lang):
        if lang in self._supported_languages:
            self._language = lang
            try:
                import enchant
                self._checker = enchant.Dict(lang)
                self._enchant_available = True
            except (ImportError, Exception):
                self._enchant_available = False
            return True
        return False

    def check_word(self, word):
        if not word or len(word) < 2:
            return {"word": word, "correct": True, "suggestions": []}
        if word in self._custom_dictionary or word in self._ignore_list:
            return {"word": word, "correct": True, "suggestions": []}
        if self._enchant_available and self._checker:
            try:
                correct = self._checker.check(word)
                suggestions = []
                if not correct:
                    suggestions = self._checker.suggest(word)[:10]
                return {"word": word, "correct": correct, "suggestions": suggestions}
            except Exception:
                pass
        lower_word = word.lower()
        if lower_word in self._context_suggestions:
            return {"word": word, "correct": False, "suggestions": [self._context_suggestions[lower_word]]}
        return self._basic_check(word)

    def _basic_check(self, word):
        common_words = {
            "the", "a", "an", "and", "or", "but", "in", "on", "at", "to",
            "for", "of", "with", "by", "from", "is", "are", "was", "were",
            "be", "been", "being", "have", "has", "had", "do", "does", "did",
            "will", "would", "could", "should", "may", "might", "can", "shall",
            "this", "that", "these", "those", "it", "its", "you", "your",
            "not", "no", "if", "then", "else", "when", "where", "how",
            "what", "which", "who", "whom", "all", "each", "every", "both",
            "some", "such", "than", "too", "very", "just", "about", "also",
            "here", "there", "now", "then", "always", "never", "often",
        }
        if word.lower() in common_words:
            return {"word": word, "correct": True, "suggestions": []}
        return {"word": word, "correct": False, "suggestions": self._context_suggestions.get(word.lower(), [])}

    def check_text(self, text):
        words = re.findall(r"\b[a-zA-Z]+\b", text)
        results = []
        for word in words:
            result = self.check_word(word)
            if not result["correct"]:
                results.append(result)
        return results

    def check_page(self, page_num):
        try:
            doc = self.editor.pdf_utils.doc
            if doc is None or page_num < 0 or page_num >= len(doc):
                return []
            text = doc[page_num].get_text("text")
            return self.check_text(text)
        except Exception:
            return []

    def check_document(self):
        try:
            doc = self.editor.pdf_utils.doc
            if doc is None:
                return {}
            all_errors = []
            for pg in range(len(doc)):
                page_errors = self.check_page(pg)
                for error in page_errors:
                    error["page"] = pg + 1
                all_errors.extend(page_errors)
            return {
                "total_errors": len(all_errors),
                "errors": all_errors,
                "by_page": self._group_by_page(all_errors),
                "language": self._language,
            }
        except Exception:
            return {"total_errors": 0, "errors": []}

    def _group_by_page(self, errors):
        groups = {}
        for err in errors:
            pg = err.get("page", 0)
            if pg not in groups:
                groups[pg] = []
            groups[pg].append(err)
        return groups

    def add_to_dictionary(self, word):
        if word:
            self._custom_dictionary.add(word.lower())
            return True
        return False

    def remove_from_dictionary(self, word):
        self._custom_dictionary.discard(word.lower())
        return True

    def get_dictionary(self):
        return sorted(self._custom_dictionary)

    def ignore_word(self, word):
        self._ignore_list.add(word.lower())

    def add_auto_correct(self, wrong, correct):
        if wrong and correct:
            self._auto_correct_map[wrong.lower()] = correct
            return True
        return False

    def enable_auto_correct(self, enabled=True):
        self._auto_correct = enabled

    def apply_auto_correct(self, text):
        if not self._auto_correct or not text:
            return text
        result = text
        for wrong, correct in self._auto_correct_map.items():
            pattern = re.compile(re.escape(wrong), re.IGNORECASE)
            result = pattern.sub(correct, result)
        return result

    def get_suggestions(self, word, max_suggestions=10):
        result = self.check_word(word)
        return result["suggestions"][:max_suggestions]

    def import_dictionary(self, path):
        try:
            with open(path, 'r', encoding='utf-8') as f:
                for line in f:
                    word = line.strip()
                    if word and not word.startswith('#'):
                        self._custom_dictionary.add(word.lower())
            return {"success": True, "words_imported": len(self._custom_dictionary)}
        except Exception as e:
            return {"success": False, "error": str(e)}

    def export_dictionary(self, path):
        try:
            with open(path, 'w', encoding='utf-8') as f:
                for word in sorted(self._custom_dictionary):
                    f.write(word + '\n')
            return {"success": True, "words_exported": len(self._custom_dictionary)}
        except Exception as e:
            return {"success": False, "error": str(e)}

    def get_supported_languages(self):
        available = []
        for lang in self._supported_languages:
            try:
                import enchant
                if enchant.dict_exists(lang):
                    available.append(lang)
            except Exception:
                available.append(lang)
        return available

    def get_statistics(self, text):
        words = re.findall(r"\b[a-zA-Z]+\b", text)
        total = len(words)
        errors = [w for w in words if not self.check_word(w)["correct"]]
        unique_words = set(w.lower() for w in words)
        return {
            "total_words": total,
            "unique_words": len(unique_words),
            "spelling_errors": len(errors),
            "accuracy": round((1 - len(errors) / max(total, 1)) * 100, 1),
        }
