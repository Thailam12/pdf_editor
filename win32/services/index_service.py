import os
import json
import math
import pymupdf


class IndexService:
    def __init__(self, editor):
        self.editor = editor
        self._index = {}
        self._doc_path = None
        self._page_texts = {}

    def build_index(self, path):
        """Build a full-text inverted index for the given PDF."""
        try:
            self._doc_path = path
            doc = pymupdf.open(path)
            self._index = {}
            self._page_texts = {}
            for page_num in range(len(doc)):
                page = doc[page_num]
                text = page.get_text("text")
                self._page_texts[page_num] = text
                words = self._tokenize(text)
                for word, positions in words.items():
                    if word not in self._index:
                        self._index[word] = []
                    self._index[word].append({
                        "page": page_num,
                        "positions": positions,
                        "count": len(positions)
                    })
            doc.close()
            return {
                "total_words": len(self._index),
                "total_pages": len(self._page_texts),
                "vocabulary": list(self._index.keys())[:100]
            }
        except Exception as e:
            raise RuntimeError(f"Cannot build index: {e}")

    def search_index(self, query):
        """Search the index and return results with page, position, context."""
        try:
            results = []
            query_words = self._tokenize(query)
            if not query_words:
                return results
            scores = {}
            for word in query_words:
                if word in self._index:
                    df = len(self._index[word])
                    total_pages = max(len(self._page_texts), 1)
                    idf = math.log(total_pages / (1 + df))
                    for entry in self._index[word]:
                        page_num = entry["page"]
                        tf = entry["count"]
                        if page_num not in scores:
                            scores[page_num] = 0.0
                        scores[page_num] += tf * idf
            for page_num, score in sorted(scores.items(), key=lambda x: -x[1]):
                context = self._page_texts.get(page_num, "")
                sentences = context.split(".")
                relevant = [
                    s.strip() for s in sentences
                    if any(w.lower() in s.lower() for w in query_words)
                ]
                results.append({
                    "page": page_num,
                    "score": round(score, 4),
                    "context": ". ".join(relevant[:3])[:500]
                })
            return results
        except Exception as e:
            raise RuntimeError(f"Cannot search index: {e}")

    def add_to_index(self, page_num, text):
        """Add text to the index for a given page."""
        try:
            words = self._tokenize(text)
            for word, positions in words.items():
                if word not in self._index:
                    self._index[word] = []
                existing = [e for e in self._index[word] if e["page"] == page_num]
                if existing:
                    existing[0]["positions"].extend(positions)
                    existing[0]["count"] = len(existing[0]["positions"])
                else:
                    self._index[word].append({
                        "page": page_num,
                        "positions": positions,
                        "count": len(positions)
                    })
            if page_num in self._page_texts:
                self._page_texts[page_num] += " " + text
            else:
                self._page_texts[page_num] = text
        except Exception as e:
            raise RuntimeError(f"Cannot add to index: {e}")

    def remove_from_index(self, page_num):
        """Remove all index entries for a given page."""
        try:
            self._page_texts.pop(page_num, None)
            for word in list(self._index.keys()):
                self._index[word] = [
                    e for e in self._index[word] if e["page"] != page_num
                ]
                if not self._index[word]:
                    del self._index[word]
        except Exception as e:
            raise RuntimeError(f"Cannot remove from index: {e}")

    def save_index(self, filepath):
        """Save the index to a JSON file."""
        try:
            data = {
                "doc_path": self._doc_path,
                "index": self._index,
                "page_texts": {str(k): v for k, v in self._page_texts.items()}
            }
            with open(filepath, "w", encoding="utf-8") as f:
                json.dump(data, f, ensure_ascii=False, indent=2)
        except Exception as e:
            raise RuntimeError(f"Cannot save index: {e}")

    def load_index(self, filepath):
        """Load an index from a JSON file."""
        try:
            with open(filepath, "r", encoding="utf-8") as f:
                data = json.load(f)
            self._doc_path = data.get("doc_path")
            self._index = data.get("index", {})
            self._page_texts = {
                int(k): v for k, v in data.get("page_texts", {}).items()
            }
        except Exception as e:
            raise RuntimeError(f"Cannot load index: {e}")

    def _tokenize(self, text):
        """Tokenize text into words with positions. Returns dict[word] -> [positions]."""
        words = {}
        if not text:
            return words
        tokens = text.split()
        for i, token in enumerate(tokens):
            clean = token.strip(".,;:!?\"'()-").lower()
            if clean and len(clean) > 1:
                if clean not in words:
                    words[clean] = []
                words[clean].append(i)
        return words
