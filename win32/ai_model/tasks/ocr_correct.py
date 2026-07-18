"""PDFMind 100M — OCR Error Correction.

Corrects common OCR misrecognitions using language model context.
Handles: character swaps, similar glyphs (l/I/1), broken words,
number/letter confusion, spacing errors.
"""

from typing import Dict, List, Optional, Tuple


class OCRCorrector:
    COMMON_OCR_ERRORS = {
        "tiie": "the", "tlie": "the", "tbe": "the", "tne": "the",
        "witb": "with", "witli": "with", "widi": "with",
        "rn": "m", "cl": "d", "li": "h", "vv": "w",
        "0": "O", "1": "l", "5": "S", "8": "B",
        "comrnand": "command", "cornputer": "computer",
        "accornmodation": "accommodation", "recornrnend": "recommend",
        "speecli": "speed", "lncluded": "included", "lnformation": "information",
        "page l": "page 1", "chapter l": "chapter 1",
        "II" : "H", "ll" : "h",
    }

    def __init__(self, model=None, tokenizer=None, device: str = "cpu"):
        self.model = model
        self.tokenizer = tokenizer
        self.device = device

    def correct(
        self,
        text: str,
        use_model: bool = False,
        confidence_threshold: float = 0.5,
    ) -> Dict:
        corrections = []
        corrected_text = text

        if use_model and self.model is not None:
            result = self._model_correct(text)
            corrected_text = result["text"]
            corrections.extend(result["corrections"])
        else:
            corrected_text, rule_corrections = self._rule_correct(text)
            corrections.extend(rule_corrections)

        return {
            "original": text,
            "corrected": corrected_text,
            "corrections": corrections,
            "num_corrections": len(corrections),
            "confidence": self._overall_confidence(corrections),
        }

    def correct_pages(self, pages: List[str], use_model: bool = False) -> List[Dict]:
        return [self.correct(page, use_model=use_model) for page in pages]

    def batch_correct(self, texts: List[str], use_model: bool = False) -> List[Dict]:
        return [self.correct(text, use_model=use_model) for text in texts]

    def _rule_correct(self, text: str) -> Tuple[str, List[Dict]]:
        corrections = []
        corrected = text

        for wrong, right in self.COMMON_OCR_ERRORS.items():
            if wrong in corrected:
                start = corrected.find(wrong)
                corrections.append({
                    "original": wrong,
                    "corrected": right,
                    "start": start,
                    "end": start + len(wrong),
                    "confidence": 0.8,
                    "method": "rule",
                })
                corrected = corrected.replace(wrong, right, 1)

        corrected = self._fix_spacing(corrected, corrections)
        corrected = self._fix_capitalization(corrected, corrections)
        return corrected, corrections

    def _fix_spacing(self, text: str, corrections: list) -> str:
        import re
        fixed = re.sub(r"\s+", " ", text)
        fixed = re.sub(r"\s([.,;:!?)])", r"\1", fixed)
        fixed = re.sub(r"\(\s+", "(", fixed)
        return fixed

    def _fix_capitalization(self, text: str, corrections: list) -> str:
        import re
        sentences = re.split(r"([.!?]\s+)", text)
        result = []
        for i, sent in enumerate(sentences):
            if i % 2 == 0 and sent:
                result.append(sent[0].upper() + sent[1:] if sent else sent)
            else:
                result.append(sent)
        return "".join(result)

    def _model_correct(self, text: str) -> Dict:
        import torch
        prompt = (
            "Correct the OCR errors in this text. "
            "Only fix clear errors, do not change content.\n\n"
            f"OCR Text:\n{text}\n\n"
            "Corrected Text:"
        )
        input_ids = self.tokenizer.encode(prompt, max_length=2048, add_special=True)
        input_tensor = torch.tensor([input_ids], dtype=torch.long, device=self.device)
        output = self.model.generate(input_tensor, max_new_tokens=len(text) + 100, temperature=0.1)
        corrected = self.tokenizer.decode(output[0].tolist(), skip_special=True)

        corrections = []
        original_words = text.split()
        corrected_words = corrected.split()
        for orig, corr in zip(original_words, corrected_words):
            if orig != corr:
                corrections.append({
                    "original": orig,
                    "corrected": corr,
                    "confidence": 0.75,
                    "method": "model",
                })

        return {"text": corrected, "corrections": corrections}

    def _overall_confidence(self, corrections: list) -> float:
        if not corrections:
            return 1.0
        return sum(c.get("confidence", 0.5) for c in corrections) / len(corrections)
