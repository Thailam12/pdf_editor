"""AI-powered semantic search engine for PDF documents.

Uses PDFMind model embeddings for semantic similarity search, question-answering,
and concept-based text retrieval with fallback to keyword text search.
"""

from __future__ import annotations

import logging
import math
import re
import time
from collections import Counter
from dataclasses import dataclass, field
from typing import Any, Dict, List, Optional, Sequence, Tuple

import fitz  # PyMuPDF

logger = logging.getLogger(__name__)

_MODEL_AVAILABLE = False
_model = None

try:
    import numpy as np
    _NUMPY_AVAILABLE = True
except ImportError:
    _NUMPY_AVAILABLE = False
    logger.info("numpy not available; semantic search will use keyword fallback")


def _try_load_model() -> bool:
    global _MODEL_AVAILABLE, _model
    if _MODEL_AVAILABLE:
        return True
    try:
        from sentence_transformers import SentenceTransformer
        _model = SentenceTransformer("all-MiniLM-L6-v2")
        _MODEL_AVAILABLE = True
        return True
    except Exception as e:
        logger.info("SentenceTransformer not available: %s", e)
        _MODEL_AVAILABLE = False
        return False


@dataclass
class SemanticResult:
    """A single semantic search result with similarity score."""
    text: str
    page_number: int
    bbox: Tuple[float, float, float, float]
    score: float
    start_char: int = 0
    end_char: int = 0
    chunk_index: int = 0
    metadata: Dict[str, Any] = field(default_factory=dict)

    @property
    def confidence(self) -> float:
        return max(0.0, min(1.0, self.score))

    def to_highlight_rect(self) -> Dict[str, Any]:
        return {
            "x0": self.bbox[0],
            "y0": self.bbox[1],
            "x1": self.bbox[2],
            "y1": self.bbox[3],
            "page": self.page_number,
        }


@dataclass
class TextChunk:
    """A chunk of text with its embedding vector and position data."""
    text: str
    page_number: int
    bbox: Tuple[float, float, float, float]
    start_char: int
    end_char: int
    embedding: Optional[Any] = None
    chunk_index: int = 0
    word_count: int = 0

    def __post_init__(self) -> None:
        if self.word_count == 0:
            self.word_count = len(self.text.split())


@dataclass
class KeywordResult:
    """Result from keyword-based fallback search."""
    text: str
    page_number: int
    bbox: Tuple[float, float, float, float]
    score: float
    matched_keywords: List[str] = field(default_factory=list)


@dataclass
class DocumentEmbedding:
    """Pre-computed embeddings for an entire document."""
    doc_id: str
    chunks: List[TextChunk]
    total_chunks: int = 0
    timestamp: float = 0.0

    @property
    def page_count(self) -> int:
        return len(set(c.page_number for c in self.chunks))


class TextChunker:
    """Splits document text into overlapping chunks for embedding."""

    def __init__(
        self,
        chunk_size: int = 256,
        chunk_overlap: int = 64,
        min_chunk_size: int = 32,
    ):
        self._chunk_size = chunk_size
        self._chunk_overlap = chunk_overlap
        self._min_chunk_size = min_chunk_size

    def chunk_page(
        self, text: str, page_number: int, words_data: Optional[List] = None
    ) -> List[TextChunk]:
        if not text.strip():
            return []

        sentences = self._split_sentences(text)
        chunks: List[TextChunk] = []
        current_text = ""
        current_start = 0
        chunk_idx = 0

        for sentence in sentences:
            sentence_start = text.find(sentence, current_start)
            if sentence_start == -1:
                sentence_start = current_start

            candidate = (current_text + " " + sentence).strip() if current_text else sentence

            if len(candidate.split()) > self._chunk_size and current_text:
                bbox = self._estimate_chunk_bbox(
                    text, current_start, current_start + len(current_text)
                )
                chunks.append(TextChunk(
                    text=current_text.strip(),
                    page_number=page_number,
                    bbox=bbox,
                    start_char=current_start,
                    end_char=current_start + len(current_text),
                    chunk_index=chunk_idx,
                ))
                chunk_idx += 1

                overlap_text = " ".join(current_text.split()[-self._chunk_overlap:])
                overlap_start = current_text.rfind(overlap_text)
                if overlap_start >= 0:
                    current_start = current_start + overlap_start
                else:
                    current_start = sentence_start
                current_text = overlap_text + " " + sentence if overlap_text else sentence
            else:
                if not current_text:
                    current_start = sentence_start
                current_text = candidate

        if current_text.strip() and len(current_text.split()) >= self._min_chunk_size // 2:
            bbox = self._estimate_chunk_bbox(
                text, current_start, current_start + len(current_text)
            )
            chunks.append(TextChunk(
                text=current_text.strip(),
                page_number=page_number,
                bbox=bbox,
                start_char=current_start,
                end_char=current_start + len(current_text),
                chunk_index=chunk_idx,
            ))

        return chunks

    def chunk_document(
        self, doc: fitz.Document
    ) -> List[TextChunk]:
        all_chunks: List[TextChunk] = []
        global_offset = 0

        for page_num in range(len(doc)):
            page = doc[page_num]
            text = page.get_text("text", flags=fitz.TEXT_PRESERVE_WHITESPACE)
            page_chunks = self.chunk_page(text, page_num)

            for chunk in page_chunks:
                chunk.start_char += global_offset
                chunk.end_char += global_offset
                all_chunks.append(chunk)

            global_offset += len(text)

        for i, chunk in enumerate(all_chunks):
            chunk.chunk_index = i

        return all_chunks

    def _split_sentences(self, text: str) -> List[str]:
        parts = re.split(r'(?<=[.!?])\s+|\n+', text)
        result: List[str] = []
        for part in parts:
            part = part.strip()
            if not part:
                continue
            words = part.split()
            if len(words) > self._chunk_size:
                for i in range(0, len(words), self._chunk_size - self._chunk_overlap):
                    sub = " ".join(words[i: i + self._chunk_size])
                    if sub.strip():
                        result.append(sub.strip())
            else:
                result.append(part)
        return result

    def _estimate_chunk_bbox(
        self, full_text: str, start: int, end: int
    ) -> Tuple[float, float, float, float]:
        text_len = max(len(full_text), 1)
        y_progress = start / text_len
        page_height = 800.0
        chunk_height = 20.0
        y_start = y_progress * page_height
        return (0.0, y_start, 600.0, y_start + chunk_height)


class KeywordSearch:
    """TF-IDF-inspired keyword search as fallback when embeddings are unavailable."""

    def __init__(self, stopwords: Optional[set] = None):
        self._stopwords = stopwords or self._default_stopwords()
        self._idf_cache: Dict[str, float] = {}

    def build_idf(self, chunks: List[TextChunk]) -> None:
        doc_count = len(chunks)
        term_doc_freq: Counter[str] = Counter()

        for chunk in chunks:
            terms = self._tokenize(chunk.text)
            unique_terms = set(terms)
            for term in unique_terms:
                term_doc_freq[term] += 1

        import math as _math
        for term, freq in term_doc_freq.items():
            self._idf_cache[term] = _math.log((doc_count + 1) / (freq + 1)) + 1

    def search(
        self,
        query: str,
        chunks: List[TextChunk],
        top_k: int = 20,
    ) -> List[KeywordResult]:
        query_terms = self._tokenize(query)
        if not query_terms:
            return []

        query_vec = self._compute_tfidf_vector(query_terms, len(chunks))
        results: List[KeywordResult] = []

        for i, chunk in enumerate(chunks):
            chunk_terms = self._tokenize(chunk.text)
            chunk_vec = self._compute_tfidf_vector(chunk_terms, len(chunks))
            score = self._cosine_similarity(query_vec, chunk_vec)

            if score > 0.01:
                matched = [t for t in query_terms if t in chunk_terms]
                results.append(KeywordResult(
                    text=chunk.text,
                    page_number=chunk.page_number,
                    bbox=chunk.bbox,
                    score=score,
                    matched_keywords=matched,
                ))

        results.sort(key=lambda r: r.score, reverse=True)
        return results[:top_k]

    def _tokenize(self, text: str) -> List[str]:
        words = re.findall(r'\b[a-zA-Z0-9]+\b', text.lower())
        return [w for w in words if w not in self._stopwords and len(w) > 1]

    def _compute_tfidf_vector(
        self, terms: List[str], doc_count: int
    ) -> Dict[str, float]:
        tf = Counter(terms)
        total = max(len(terms), 1)
        vec: Dict[str, float] = {}
        for term, count in tf.items():
            idf = self._idf_cache.get(term, math.log(doc_count + 1))
            vec[term] = (count / total) * idf
        return vec

    @staticmethod
    def _cosine_similarity(a: Dict[str, float], b: Dict[str, float]) -> float:
        common_keys = set(a.keys()) & set(b.keys())
        if not common_keys:
            return 0.0

        dot = sum(a[k] * b[k] for k in common_keys)
        norm_a = math.sqrt(sum(v * v for v in a.values()))
        norm_b = math.sqrt(sum(v * v for v in b.values()))

        if norm_a == 0 or norm_b == 0:
            return 0.0
        return dot / (norm_a * norm_b)

    @staticmethod
    def _default_stopwords() -> set:
        return {
            "the", "a", "an", "is", "are", "was", "were", "be", "been",
            "being", "have", "has", "had", "do", "does", "did", "will",
            "would", "could", "should", "may", "might", "shall", "can",
            "to", "of", "in", "for", "on", "with", "at", "by", "from",
            "as", "into", "through", "during", "before", "after", "above",
            "below", "between", "out", "off", "over", "under", "again",
            "further", "then", "once", "here", "there", "when", "where",
            "why", "how", "all", "each", "every", "both", "few", "more",
            "most", "other", "some", "such", "no", "nor", "not", "only",
            "own", "same", "so", "than", "too", "very", "just", "also",
        }


class SemanticSearchEngine:
    """AI-powered semantic search engine for PDF documents.

    Uses sentence-transformer embeddings when available for concept-based
    search, with automatic fallback to TF-IDF keyword matching when
    the model is not installed.
    """

    def __init__(
        self,
        chunk_size: int = 256,
        chunk_overlap: int = 64,
        use_model: bool = True,
    ):
        self._chunker = TextChunker(
            chunk_size=chunk_size, chunk_overlap=chunk_overlap
        )
        self._keyword_search = KeywordSearch()
        self._doc_embeddings: Dict[str, DocumentEmbedding] = {}
        self._model_loaded = False
        self._use_model = use_model

        if use_model:
            self._model_loaded = _try_load_model()

    def index_document(self, doc: fitz.Document, doc_id: Optional[str] = None) -> DocumentEmbedding:
        doc_id = doc_id or self._doc_id(doc)

        if doc_id in self._doc_embeddings:
            return self._doc_embeddings[doc_id]

        chunks = self._chunker.chunk_document(doc)

        if self._model_loaded and _NUMPY_AVAILABLE and _model is not None:
            self._embed_chunks(chunks)

        self._keyword_search.build_idf(chunks)

        embedding = DocumentEmbedding(
            doc_id=doc_id,
            chunks=chunks,
            total_chunks=len(chunks),
            timestamp=time.time(),
        )
        self._doc_embeddings[doc_id] = embedding
        return embedding

    def search(
        self,
        doc: fitz.Document,
        query: str,
        top_k: int = 20,
        threshold: float = 0.3,
        page_numbers: Optional[List[int]] = None,
    ) -> List[SemanticResult]:
        doc_id = self._doc_id(doc)
        embedding = self.index_document(doc, doc_id)
        chunks = embedding.chunks

        if page_numbers:
            chunks = [c for c in chunks if c.page_number in page_numbers]

        if self._model_loaded and _NUMPY_AVAILABLE and _model is not None:
            results = self._semantic_search(query, chunks, top_k, threshold)
            if results:
                return results

        return self._keyword_fallback(query, chunks, top_k)

    def find_related_passages(
        self,
        doc: fitz.Document,
        reference_text: str,
        top_k: int = 10,
    ) -> List[SemanticResult]:
        return self.search(doc, reference_text, top_k=top_k, threshold=0.1)

    def question_answer(
        self,
        doc: fitz.Document,
        question: str,
        top_k: int = 5,
    ) -> List[SemanticResult]:
        results = self.search(doc, question, top_k=top_k, threshold=0.2)

        for r in results:
            sentences = re.split(r'[.!?]+', r.text)
            best_sentence = ""
            best_score = 0.0
            for sentence in sentences:
                sentence = sentence.strip()
                if not sentence:
                    continue
                score = self._text_relevance(question, sentence)
                if score > best_score:
                    best_score = score
                    best_sentence = sentence
            if best_sentence:
                r.text = best_sentence
                r.score = (r.score + best_score) / 2

        results.sort(key=lambda x: x.score, reverse=True)
        return results[:top_k]

    def extract_keywords(
        self,
        doc: fitz.Document,
        top_n: int = 20,
    ) -> List[Tuple[str, float]]:
        doc_id = self._doc_id(doc)
        embedding = self.index_document(doc, doc_id)

        word_freq: Counter[str] = Counter()
        total_words = 0

        for chunk in embedding.chunks:
            words = self._keyword_search._tokenize(chunk.text)
            word_freq.update(words)
            total_words += len(words)

        if total_words == 0:
            return []

        import math as _math
        scored = [
            (word, (freq / total_words) * _math.log(total_words / (freq + 1) + 1))
            for word, freq in word_freq.most_common(200)
        ]
        scored.sort(key=lambda x: x[1], reverse=True)
        return scored[:top_n]

    def get_search_stats(self, doc: fitz.Document) -> Dict[str, Any]:
        doc_id = self._doc_id(doc)
        embedding = self.index_document(doc, doc_id)
        return {
            "doc_id": doc_id,
            "total_chunks": embedding.total_chunks,
            "page_count": embedding.page_count,
            "model_available": self._model_loaded,
            "chunks_per_page": {
                p: sum(1 for c in embedding.chunks if c.page_number == p)
                for p in range(embedding.page_count)
            },
        }

    def invalidate(self, doc_id: Optional[str] = None) -> None:
        if doc_id:
            self._doc_embeddings.pop(doc_id, None)
        else:
            self._doc_embeddings.clear()

    def _semantic_search(
        self,
        query: str,
        chunks: List[TextChunk],
        top_k: int,
        threshold: float,
    ) -> List[SemanticResult]:
        if not _NUMPY_AVAILABLE or _model is None:
            return []

        try:
            query_embedding = _model.encode(query, convert_to_numpy=True)
        except Exception as e:
            logger.warning("Query encoding failed: %s", e)
            return []

        chunk_embeddings = [c.embedding for c in chunks if c.embedding is not None]
        if not chunk_embeddings:
            return []

        import numpy as np
        emb_matrix = np.array(chunk_embeddings)
        query_norm = query_embedding / (np.linalg.norm(query_embedding) + 1e-10)
        emb_norms = emb_matrix / (np.linalg.norm(emb_matrix, axis=1, keepdims=True) + 1e-10)
        similarities = emb_norms @ query_norm

        results: List[SemanticResult] = []
        chunk_idx = 0
        for i, chunk in enumerate(chunks):
            if chunk.embedding is None:
                continue
            score = float(similarities[chunk_idx])
            chunk_idx += 1

            if score >= threshold:
                results.append(SemanticResult(
                    text=chunk.text,
                    page_number=chunk.page_number,
                    bbox=chunk.bbox,
                    score=score,
                    start_char=chunk.start_char,
                    end_char=chunk.end_char,
                    chunk_index=chunk.chunk_index,
                ))

        results.sort(key=lambda r: r.score, reverse=True)
        return results[:top_k]

    def _keyword_fallback(
        self,
        query: str,
        chunks: List[TextChunk],
        top_k: int,
    ) -> List[SemanticResult]:
        kw_results = self._keyword_search.search(query, chunks, top_k=top_k)
        results: List[SemanticResult] = []

        for kr in kw_results:
            results.append(SemanticResult(
                text=kr.text,
                page_number=kr.page_number,
                bbox=kr.bbox,
                score=kr.score,
                metadata={"matched_keywords": kr.matched_keywords, "method": "keyword"},
            ))

        return results

    def _embed_chunks(self, chunks: List[TextChunk]) -> None:
        if _model is None or not _NUMPY_AVAILABLE:
            return

        texts = [c.text for c in chunks]
        batch_size = 64

        try:
            for i in range(0, len(texts), batch_size):
                batch = texts[i: i + batch_size]
                embeddings = _model.encode(batch, convert_to_numpy=True, show_progress_bar=False)
                for j, emb in enumerate(embeddings):
                    chunks[i + j].embedding = emb
        except Exception as e:
            logger.warning("Chunk embedding failed: %s", e)

    @staticmethod
    def _text_relevance(query: str, text: str) -> float:
        query_words = set(query.lower().split())
        text_words = set(text.lower().split())
        if not query_words:
            return 0.0
        overlap = query_words & text_words
        return len(overlap) / len(query_words)

    @staticmethod
    def _doc_id(doc: fitz.Document) -> str:
        try:
            return doc.name or str(id(doc))
        except Exception:
            return str(id(doc))
