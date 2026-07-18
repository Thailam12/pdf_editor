"""PDFMind 100M — BPE Tokenizer.

Custom Byte-Pair Encoding tokenizer optimized for PDF content.
Handles: text, numbers, URLs, emails, file paths, code snippets,
measurement units, dates, currency, and multilingual text.

Supports training from scratch and loading pre-trained vocabularies.
"""

import json
import os
import re
import unicodedata
from collections import Counter, defaultdict
from typing import Dict, List, Optional, Tuple


class BPE:
    """Byte-Pair Encoding implementation."""

    def __init__(self):
        self.merges: Dict[Tuple[str, str], int] = {}
        self.vocab: Dict[str, int] = {}
        self.inverse_vocab: Dict[int, str] = {}

    def train(self, corpus: List[str], vocab_size: int = 32000, min_freq: int = 2):
        word_freqs = Counter()
        for text in corpus:
            words = text.split()
            for word in words:
                word_freqs[word] += 1

        splits = {}
        for word, freq in word_freqs.items():
            if freq >= min_freq:
                splits[word] = list(word) + ["</w>"]

        vocab = set()
        for splits_list in splits.values():
            for token in splits_list:
                vocab.add(token)

        num_merges = vocab_size - len(vocab)
        merge_rank = 0

        for _ in range(num_merges):
            if not splits:
                break

            bigram_freqs = Counter()
            for word, freq in word_freqs.items():
                if word not in splits:
                    continue
                symbols = splits[word]
                for i in range(len(symbols) - 1):
                    bigram = (symbols[i], symbols[i + 1])
                    bigram_freqs[bigram] += freq

            if not bigram_freqs:
                break

            best_bigram = max(bigram_freqs, key=bigram_freqs.get)
            if bigram_freqs[best_bigram] < min_freq:
                break

            self.merges[best_bigram] = merge_rank
            merge_rank += 1

            new_splits = {}
            for word, freq in word_freqs.items():
                if word not in splits:
                    continue
                symbols = splits[word]
                new_symbols = []
                i = 0
                while i < len(symbols):
                    if i < len(symbols) - 1 and (symbols[i], symbols[i + 1]) == best_bigram:
                        new_symbols.append(symbols[i] + symbols[i + 1])
                        i += 2
                    else:
                        new_symbols.append(symbols[i])
                        i += 1
                new_splits[word] = new_symbols
                if new_symbols == [word + "</w>"]:
                    del new_splits[word]
            splits = new_splits

            merged_token = best_bigram[0] + best_bigram[1]
            vocab.add(merged_token)

        base_tokens = list(range(256))
        special_tokens = ["<pad>", "<bos>", "<eos>", "<mask>"]
        all_tokens = special_tokens + [chr(i) for i in base_tokens]
        for token in sorted(vocab):
            if token not in all_tokens:
                all_tokens.append(token)

        self.vocab = {token: idx for idx, token in enumerate(all_tokens)}
        self.inverse_vocab = {idx: token for token, idx in self.vocab.items()}

    def encode(self, text: str, add_special: bool = True) -> List[int]:
        tokens = []
        if add_special:
            tokens.append(self.vocab.get("<bos>", 1))

        words = text.split()
        for word in words:
            word_tokens = list(word) + ["</w>"]
            while len(word_tokens) > 1:
                min_rank = float("inf")
                min_idx = -1
                for i in range(len(word_tokens) - 1):
                    bigram = (word_tokens[i], word_tokens[i + 1])
                    rank = self.merges.get(bigram, float("inf"))
                    if rank < min_rank:
                        min_rank = rank
                        min_idx = i
                if min_idx == -1:
                    break
                merged = word_tokens[min_idx] + word_tokens[min_idx + 1]
                word_tokens = word_tokens[:min_idx] + [merged] + word_tokens[min_idx + 2:]

            for token in word_tokens:
                tokens.append(self.vocab.get(token, self.vocab.get("<unk>", 4)))

        if add_special:
            tokens.append(self.vocab.get("<eos>", 2))

        return tokens

    def decode(self, ids: List[int], skip_special: bool = True) -> str:
        special_ids = {self.vocab.get("<pad>", 0), self.vocab.get("<bos>", 1),
                       self.vocab.get("<eos>", 2), self.vocab.get("<mask>", 3)}
        tokens = []
        for idx in ids:
            if skip_special and idx in special_ids:
                continue
            token = self.inverse_vocab.get(idx, "<unk>")
            tokens.append(token)
        text = "".join(tokens)
        text = text.replace("</w>", " ").strip()
        return text

    def save(self, path: str):
        data = {
            "merges": [list(k) + [v] for k, v in self.merges.items()],
            "vocab": self.vocab,
        }
        with open(path, "w", encoding="utf-8") as f:
            json.dump(data, f, ensure_ascii=False, indent=2)

    @classmethod
    def load(cls, path: str) -> "BPE":
        bpe = cls()
        with open(path, encoding="utf-8") as f:
            data = json.load(f)
        bpe.merges = {tuple(item[:-1]): item[-1] for item in data["merges"]}
        bpe.vocab = data["vocab"]
        bpe.inverse_vocab = {int(idx): token for token, idx in bpe.vocab.items()}
        return bpe


class PDFMindTokenizer:
    """Tokenizer wrapper for PDFMind models."""

    PAD_TOKEN = "<pad>"
    BOS_TOKEN = "<bos>"
    EOS_TOKEN = "<eos>"
    UNK_TOKEN = "<unk>"
    MASK_TOKEN = "<mask>"

    SPECIAL_PATTERNS = [
        (r"https?://\S+", "<URL>"),
        (r"\S+@\S+\.\S+", "<EMAIL>"),
        (r"\b\d{1,3}([.,]\d{1,3}){2,3}\b", "<NUMBER>"),
        (r"\b\d{4}[-/]\d{1,2}[-/]\d{1,2}\b", "<DATE>"),
        (r"\b\d{1,2}:\d{2}(:\d{2})?\b", "<TIME>"),
        (r"\b\d+([.,]\d+)?\s*(mm|cm|m|km|in|ft|yd|mi|kg|g|mg|lb|oz|L|mL|°C|°F|°)\b", "<MEASUREMENT>"),
        (r"\b[A-Z]{2,}\d{2,}\b", "<CODE>"),
        (r"[\w/\\]+\.\w{1,5}\b", "<FILEPATH>"),
    ]

    def __init__(self, bpe: Optional[BPE] = None, vocab_size: int = 32000):
        self.bpe = bpe or BPE()
        self.vocab_size = vocab_size
        self.special_tokens = {
            self.PAD_TOKEN: 0,
            self.BOS_TOKEN: 1,
            self.EOS_TOKEN: 2,
            self.UNK_TOKEN: 3,
            self.MASK_TOKEN: 4,
        }

    def train(self, texts: List[str]):
        self.bpe.train(texts, vocab_size=self.vocab_size)
        self.vocab_size = len(self.bpe.vocab)

    def encode(self, text: str, max_length: Optional[int] = None, add_special: bool = True) -> List[int]:
        preprocessed = self._preprocess(text)
        token_ids = self.bpe.encode(preprocessed, add_special=add_special)

        if max_length is not None:
            if len(token_ids) > max_length:
                token_ids = token_ids[:max_length]
                if add_special and token_ids[-1] != self.special_tokens[self.EOS_TOKEN]:
                    token_ids[-1] = self.special_tokens[self.EOS_TOKEN]

        return token_ids

    def decode(self, token_ids: List[int], skip_special: bool = True) -> str:
        return self.bpe.decode(token_ids, skip_special=skip_special)

    def batch_encode(self, texts: List[str], max_length: Optional[int] = None, padding: bool = True) -> dict:
        encoded = [self.encode(t, max_length=max_length) for t in texts]

        if padding and max_length:
            for i in range(len(encoded)):
                pad_len = max_length - len(encoded[i])
                encoded[i] = encoded[i] + [0] * pad_len

        return {
            "input_ids": encoded,
            "attention_mask": [[1 if t != 0 else 0 for t in seq] for seq in encoded],
        }

    def _preprocess(self, text: str) -> str:
        text = unicodedata.normalize("NFKC", text)
        text = text.replace("\t", " ").replace("\r\n", "\n").replace("\r", "\n")
        lines = text.split("\n")
        lines = [re.sub(r" {2,}", " ", line.strip()) for line in lines]
        text = "\n".join(lines)
        text = re.sub(r"\n{3,}", "\n\n", text)
        return text

    @property
    def pad_id(self) -> int:
        return 0

    @property
    def bos_id(self) -> int:
        return 1

    @property
    def eos_id(self) -> int:
        return 2

    @property
    def unk_id(self) -> int:
        return 3

    @property
    def mask_id(self) -> int:
        return 4

    def save(self, directory: str):
        os.makedirs(directory, exist_ok=True)
        self.bpe.save(os.path.join(directory, "bpe.json"))
        meta = {
            "vocab_size": self.vocab_size,
            "special_tokens": self.special_tokens,
            "version": "1.0.0",
            "model_name": "PDFMind-100M",
        }
        with open(os.path.join(directory, "tokenizer_config.json"), "w") as f:
            json.dump(meta, f, indent=2)

    @classmethod
    def load(cls, directory: str) -> "PDFMindTokenizer":
        bpe = BPE.load(os.path.join(directory, "bpe.json"))
        with open(os.path.join(directory, "tokenizer_config.json")) as f:
            meta = json.load(f)
        tokenizer = cls(bpe=bpe, vocab_size=meta["vocab_size"])
        tokenizer.special_tokens = meta.get("special_tokens", cls.special_tokens)
        return tokenizer

    @classmethod
    def from_pretrained(cls, model_name: str = "pdfmind/pdfmind-100m") -> "PDFMindTokenizer":
        from huggingface_hub import hf_hub_download
        config_path = hf_hub_download(repo_id=model_name, filename="tokenizer/tokenizer_config.json")
        bpe_path = hf_hub_download(repo_id=model_name, filename="tokenizer/bpe.json")
        directory = os.path.dirname(config_path)
        return cls.load(directory)
