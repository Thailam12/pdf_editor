"""PDFMind 100M — PDF Summarization Task.

Summarizes PDF content with configurable detail levels:
- Quick: 1-2 sentence summary
- Standard: paragraph summary
- Detailed: section-by-section breakdown
"""

from typing import Dict, List, Optional


class PDFSummarizer:
    def __init__(self, model, tokenizer, device: str = "cpu"):
        self.model = model
        self.tokenizer = tokenizer
        self.device = device
        self.prompts = {
            "quick": "Summarize this PDF in one sentence:",
            "standard": "Summarize this PDF content in a concise paragraph:",
            "detailed": "Provide a detailed summary of this PDF with key points:",
            "bullet": "List the key points of this PDF as bullet points:",
        }

    def summarize(
        self,
        text: str,
        level: str = "standard",
        max_length: int = 256,
        temperature: float = 0.7,
    ) -> str:
        prompt = self.prompts.get(level, self.prompts["standard"])
        full_prompt = f"{prompt}\n\n{text[:3000]}\n\nSummary:"
        return self._generate(full_prompt, max_length, temperature)

    def summarize_pages(self, pages: List[str], level: str = "standard") -> Dict[str, str]:
        results = {}
        for i, page in enumerate(pages):
            results[f"page_{i + 1}"] = self.summarize(page, level=level)
        combined = "\n".join(results.values())
        results["overall"] = self.summarize(combined, level=level)
        return results

    def extract_keywords(self, text: str, n_keywords: int = 10) -> List[str]:
        prompt = f"Extract the {n_keywords} most important keywords from this text:\n\n{text[:3000]}\n\nKeywords (comma-separated):"
        response = self._generate(prompt, max_length=128, temperature=0.3)
        keywords = [kw.strip() for kw in response.split(",")]
        return keywords[:n_keywords]

    def create_toc(self, text: str) -> str:
        prompt = f"Generate a table of contents for this document:\n\n{text[:5000]}\n\nTable of Contents:"
        return self._generate(prompt, max_length=512, temperature=0.3)

    def _generate(self, prompt: str, max_length: int, temperature: float) -> str:
        import torch
        input_ids = self.tokenizer.encode(prompt, max_length=2048, add_special=True)
        input_tensor = torch.tensor([input_ids], dtype=torch.long, device=self.device)
        output = self.model.generate(input_tensor, max_new_tokens=max_length, temperature=temperature)
        return self.tokenizer.decode(output[0].tolist(), skip_special=True)
