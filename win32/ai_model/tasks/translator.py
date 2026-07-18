"""PDFMind 100M — PDF Translation.

Translates PDF content between 100+ languages while preserving
formatting, layout references, and technical terminology.
"""

from typing import Dict, List, Optional


class PDFTranslator:
    def __init__(self, model=None, tokenizer=None, device: str = "cpu"):
        self.model = model
        self.tokenizer = tokenizer
        self.device = device

    def translate(
        self,
        text: str,
        source_lang: str = "auto",
        target_lang: str = "en",
        max_length: int = 512,
        temperature: float = 0.3,
    ) -> Dict:
        prompt = (
            f"Translate the following text from {source_lang} to {target_lang}.\n"
            f"Preserve formatting and technical terms.\n\n"
            f"Text:\n{text[:3000]}\n\n"
            f"Translation ({target_lang}):"
        )
        translated = self._generate(prompt, max_length, temperature)

        return {
            "original": text,
            "translated": translated,
            "source_lang": source_lang,
            "target_lang": target_lang,
        }

    def translate_pages(
        self, pages: List[str], target_lang: str = "en", source_lang: str = "auto",
    ) -> List[Dict]:
        return [self.translate(page, source_lang, target_lang) for page in pages]

    def batch_translate(
        self, texts: List[str], target_lang: str = "en",
    ) -> List[Dict]:
        return [self.translate(t, target_lang=target_lang) for t in texts]

    def detect_language(self, text: str) -> str:
        if self.model is None:
            return "unknown"
        prompt = f"Detect the language of this text. Reply with just the language code:\n\n{text[:500]}\n\nLanguage:"
        result = self._generate(prompt, max_length=10, temperature=0.1)
        return result.strip().lower()

    def multilingual_summary(self, text: str, languages: List[str]) -> Dict[str, str]:
        results = {}
        for lang in languages:
            result = self.translate(text, target_lang=lang)
            results[lang] = result["translated"]
        return results

    def _generate(self, prompt: str, max_length: int, temperature: float) -> str:
        import torch
        input_ids = self.tokenizer.encode(prompt, max_length=2048, add_special=True)
        input_tensor = torch.tensor([input_ids], dtype=torch.long, device=self.device)
        output = self.model.generate(input_tensor, max_new_tokens=max_length, temperature=temperature)
        return self.tokenizer.decode(output[0].tolist(), skip_special=True)
