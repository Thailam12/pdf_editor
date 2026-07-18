import re
from collections import Counter
from tkinter import messagebox


_TRANSLATION_DICT = {
    "hello": "xin chào", "goodbye": "tạm biệt", "thank you": "cảm ơn",
    "please": "làm ơn", "yes": "có", "no": "không", "good": "tốt",
    "bad": "xấu", "big": "lớn", "small": "nhỏ", "hot": "nóng",
    "cold": "lạnh", "water": "nước", "food": "thức ăn", "love": "yêu",
    "hate": "ghét", "work": "làm việc", "school": "trường học",
    "book": "sách", "pen": "bút", "man": "đàn ông", "woman": "phụ nữ",
    "child": "đứa trẻ", "day": "ngày", "night": "đêm", "time": "thời gian",
    "money": "tiền", "friend": "bạn bè", "family": "gia đình",
    "house": "nhà", "car": "xe hơi", "city": "thành phố",
    "country": "đất nước", "world": "thế giới", "people": "mọi người",
    "hello world": "xin chào thế giới",
    "xin chào": "hello", "tạm biệt": "goodbye", "cảm ơn": "thank you",
    "làm ơn": "please", "tốt": "good", "xấu": "bad", "lớn": "big",
    "nhỏ": "small", "nước": "water", "thức ăn": "food", "yêu": "love",
    "làm việc": "work", "trường học": "school", "sách": "book",
    "đàn ông": "man", "phụ nữ": "woman", "gia đình": "family",
    "nhà": "house", "thành phố": "city", "thế giới": "world",
    "thời gian": "time", "tiền": "money", "bạn bè": "friend",
    "mọi người": "people",
}


class AIService:
    def __init__(self, editor):
        self.editor = editor

    def extract_text(self, page_num):
        try:
            doc = self.editor.pdf_utils.doc
            if doc is None or page_num < 0 or page_num >= len(doc):
                return ""
            page = doc[page_num]
            return page.get_text("text").strip()
        except Exception as e:
            return ""

    def summarize_text(self, text):
        try:
            if not text.strip():
                return ""
            sentences = re.split(r'(?<=[.!?])\s+', text)
            sentences = [s.strip() for s in sentences if len(s.strip()) > 10]
            if len(sentences) <= 3:
                return text[:500]
            words = re.findall(r'\w+', text.lower())
            stop_words = {
                "the", "a", "an", "is", "are", "was", "were", "be", "been",
                "being", "have", "has", "had", "do", "does", "did", "will",
                "would", "could", "should", "may", "might", "shall", "can",
                "to", "of", "in", "for", "on", "with", "at", "by", "from",
                "as", "and", "or", "but", "not", "so", "if", "that", "this",
                "these", "those", "it", "its", "they", "them", "their",
                "he", "she", "his", "her", "him", "we", "us", "our",
                "you", "your", "i", "me", "my", "mine",
            }
            filtered = [w for w in words if w not in stop_words and len(w) > 2]
            if not filtered:
                return text[:500]
            word_freq = Counter(filtered)
            max_freq = max(word_freq.values())
            sentence_scores = {}
            for sentence in sentences:
                sent_words = re.findall(r'\w+', sentence.lower())
                score = sum(word_freq.get(w, 0) / max_freq for w in sent_words)
                sentence_scores[sentence] = score / (len(sent_words) + 1)
            ranked = sorted(sentence_scores.items(), key=lambda x: x[1], reverse=True)
            num_summary_sentences = max(1, len(sentences) // 3)
            summary_sentences = [s for s, _ in ranked[:num_summary_sentences]]
            summary = " ".join(summary_sentences)
            return summary if summary else text[:500]
        except Exception as e:
            return text[:500]

    def translate_text(self, text, target_lang="vi"):
        try:
            if not text.strip():
                return ""
            result_parts = []
            for word in text.split():
                lower = word.lower().strip(".,!?;:\"'()[]{}")
                translated = _TRANSLATION_DICT.get(lower)
                if translated:
                    result_parts.append(translated)
                else:
                    result_parts.append(word)
            return " ".join(result_parts)
        except Exception as e:
            return text

    def analyze_document(self):
        try:
            doc = self.editor.pdf_utils.doc
            if doc is None:
                return {
                    "page_count": 0, "word_count": 0,
                    "char_count": 0, "estimated_read_time": "0 phút",
                }
            total_words = 0
            total_chars = 0
            for page_num in range(len(doc)):
                text = doc[page_num].get_text("text")
                total_words += len(text.split())
                total_chars += len(text)
            read_minutes = max(1, round(total_words / 200))
            read_time = f"{read_minutes} phút" if read_minutes < 60 else f"{read_minutes // 60} giờ {read_minutes % 60} phút"
            return {
                "page_count": len(doc),
                "word_count": total_words,
                "char_count": total_chars,
                "estimated_read_time": read_time,
            }
        except Exception as e:
            return {
                "page_count": 0, "word_count": 0,
                "char_count": 0, "estimated_read_time": "0 phút",
            }
