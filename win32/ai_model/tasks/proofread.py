"""PDFMind 100M — Proofreading Task.

Proofreads PDF content for:
- Grammar errors
- Spelling mistakes
- Punctuation issues
- Style inconsistencies
- Readability improvements
"""

from typing import Dict, List, Optional


class Proofreader:
    def __init__(self, model=None, tokenizer=None, device: str = "cpu"):
        self.model = model
        self.tokenizer = tokenizer
        self.device = device

    def proofread(
        self,
        text: str,
        checks: Optional[List[str]] = None,
        max_length: int = 512,
    ) -> Dict:
        if checks is None:
            checks = ["grammar", "spelling", "punctuation", "style"]

        prompt = (
            f"Proofread this text. Check for: {', '.join(checks)}.\n"
            f"Provide the corrected text and list each correction.\n\n"
            f"Text:\n{text[:3000]}\n\n"
            f"Corrections (TYPE: ORIGINAL -> CORRECTED):\n"
        )

        response = self._generate(prompt, max_length, temperature=0.1)
        corrections = self._parse_corrections(response)

        corrected_text = text
        for corr in sorted(corrections, key=lambda c: -text.find(c.get("original", ""))):
            orig = corr.get("original", "")
            fixed = corr.get("corrected", "")
            if orig in corrected_text:
                corrected_text = corrected_text.replace(orig, fixed, 1)

        return {
            "original": text,
            "corrected": corrected_text,
            "corrections": corrections,
            "num_corrections": len(corrections),
            "score": self._compute_score(corrections, text),
        }

    def proofread_pages(self, pages: List[str]) -> List[Dict]:
        return [self.proofread(page) for page in pages]

    def readability_score(self, text: str) -> Dict:
        sentences = [s.strip() for s in text.replace("\n", " ").split(".") if s.strip()]
        words = text.split()
        syllable_count = sum(self._count_syllables(w) for w in words)

        num_sentences = max(len(sentences), 1)
        num_words = max(len(words), 1)
        num_syllables = max(syllable_count, 1)

        asl = num_words / num_sentences
        asw = num_syllables / num_words
        flesch_kincaid = 206.835 - 1.015 * asl - 84.6 * (num_syllables / num_words)

        if flesch_kincaid >= 80:
            level = "Easy"
        elif flesch_kincaid >= 60:
            level = "Standard"
        elif flesch_kincaid >= 40:
            level = "Difficult"
        else:
            level = "Very Difficult"

        return {
            "flesch_kincaid": round(flesch_kincaid, 1),
            "reading_level": level,
            "word_count": num_words,
            "sentence_count": num_sentences,
            "avg_words_per_sentence": round(asl, 1),
            "avg_syllables_per_word": round(asw, 2),
        }

    def style_check(self, text: str) -> Dict:
        import re
        issues = []

        sentences = text.split(".")
        for i, sent in enumerate(sentences):
            sent = sent.strip()
            if not sent:
                continue
            if len(sent) > 200:
                issues.append({"type": "style", "issue": "Very long sentence", "sentence": i + 1, "length": len(sent)})
            if i > 0 and sent and sent[0].islower():
                issues.append({"type": "style", "issue": "Sentence does not start with capital", "sentence": i + 1})
            passive = re.findall(r"\b(is|are|was|were|been|being)\s+\w+ed\b", sent)
            if passive:
                issues.append({"type": "style", "issue": f"Passive voice detected: {passive[0]}", "sentence": i + 1})
            filler = re.findall(r"\b(very|really|quite|just|actually|basically)\b", sent.lower())
            if filler:
                issues.append({"type": "style", "issue": f"Filler word: {filler[0]}", "sentence": i + 1})

        return {
            "issues": issues,
            "num_issues": len(issues),
            "grade": "A" if len(issues) == 0 else "B" if len(issues) < 3 else "C" if len(issues) < 6 else "D",
        }

    def _parse_corrections(self, response: str) -> List[Dict]:
        import re
        corrections = []
        for line in response.split("\n"):
            match = re.match(r"(\w+):\s*(.+?)\s*->\s*(.+)", line.strip())
            if match:
                corrections.append({
                    "type": match.group(1),
                    "original": match.group(2).strip(),
                    "corrected": match.group(3).strip(),
                })
        return corrections

    def _compute_score(self, corrections: list, text: str) -> float:
        if not text:
            return 1.0
        error_rate = len(corrections) / max(len(text.split()), 1)
        return max(0.0, min(1.0, 1.0 - error_rate * 10))

    def _count_syllables(self, word: str) -> int:
        word = word.lower().strip()
        if not word:
            return 0
        vowels = "aeiouy"
        count = 0
        prev_vowel = False
        for char in word:
            is_vowel = char in vowels
            if is_vowel and not prev_vowel:
                count += 1
            prev_vowel = is_vowel
        if word.endswith("e") and count > 1:
            count -= 1
        return max(count, 1)

    def _generate(self, prompt: str, max_length: int, temperature: float) -> str:
        import torch
        input_ids = self.tokenizer.encode(prompt, max_length=2048, add_special=True)
        input_tensor = torch.tensor([input_ids], dtype=torch.long, device=self.device)
        output = self.model.generate(input_tensor, max_new_tokens=max_length, temperature=temperature)
        return self.tokenizer.decode(output[0].tolist(), skip_special=True)
