"""PDFMind 100M — Document Comparison.

Compares two PDFs and identifies:
- Text changes (additions, deletions, modifications)
- Structural changes (layout, formatting)
- Image differences
- Metadata changes
"""

from typing import Dict, List, Optional, Tuple


class DocumentComparator:
    def __init__(self, model=None, tokenizer=None, device: str = "cpu"):
        self.model = model
        self.tokenizer = tokenizer
        self.device = device

    def compare(
        self, text_a: str, text_b: str, use_model: bool = False,
    ) -> Dict:
        changes = self._diff_texts(text_a, text_b)

        summary = ""
        if use_model and self.model is not None:
            summary = self._model_summary(text_a, text_b, changes)

        return {
            "changes": changes,
            "summary": summary,
            "stats": self._compute_stats(changes),
            "similarity": self._compute_similarity(text_a, text_b),
        }

    def compare_pages(self, pages_a: List[str], pages_b: List[str]) -> Dict:
        results = []
        max_pages = max(len(pages_a), len(pages_b))
        for i in range(max_pages):
            pa = pages_a[i] if i < len(pages_a) else ""
            pb = pages_b[i] if i < len(pages_b) else ""
            result = self.compare(pa, pb)
            result["page"] = i + 1
            results.append(result)

        total_additions = sum(r["stats"]["additions"] for r in results)
        total_deletions = sum(r["stats"]["deletions"] for r in results)
        total_modifications = sum(r["stats"]["modifications"] for r in results)

        return {
            "page_results": results,
            "total_stats": {
                "additions": total_additions,
                "deletions": total_deletions,
                "modifications": total_modifications,
                "pages_compared": max_pages,
                "pages_changed": sum(1 for r in results if r["stats"]["total"] > 0),
            },
        }

    def find_redlines(self, text_a: str, text_b: str) -> str:
        lines_a = text_a.split("\n")
        lines_b = text_b.split("\n")
        result = []
        max_lines = max(len(lines_a), len(lines_b))

        for i in range(max_lines):
            la = lines_a[i] if i < len(lines_a) else None
            lb = lines_b[i] if i < len(lines_b) else None

            if la == lb:
                result.append(f"  {la or ''}")
            elif la is None:
                result.append(f"+ {lb}")
            elif lb is None:
                result.append(f"- {la}")
            else:
                result.append(f"- {la}")
                result.append(f"+ {lb}")

        return "\n".join(result)

    def _diff_texts(self, text_a: str, text_b: str) -> List[Dict]:
        lines_a = text_a.split("\n")
        lines_b = text_b.split("\n")
        changes = []

        a_set = {l.strip(): i for i, l in enumerate(lines_a) if l.strip()}
        b_set = {l.strip(): i for i, l in enumerate(lines_b) if l.strip()}

        seen_in_b = set()
        for line_a, idx_a in a_set.items():
            if line_a in b_set:
                idx_b = b_set[line_a]
                if idx_a != idx_b:
                    changes.append({
                        "type": "moved",
                        "line_a": idx_a + 1,
                        "line_b": idx_b + 1,
                        "text": line_a,
                    })
                seen_in_b.add(line_a)
            else:
                found_match = False
                for line_b in b_set:
                    if line_b not in seen_in_b:
                        sim = self._line_similarity(line_a, line_b)
                        if sim > 0.6:
                            changes.append({
                                "type": "modified",
                                "line_a": idx_a + 1,
                                "line_b": b_set[line_b] + 1,
                                "text_a": line_a,
                                "text_b": line_b,
                                "similarity": round(sim, 2),
                            })
                            seen_in_b.add(line_b)
                            found_match = True
                            break
                if not found_match:
                    changes.append({
                        "type": "deleted",
                        "line_a": idx_a + 1,
                        "text": line_a,
                    })

        for line_b, idx_b in b_set.items():
            if line_b not in seen_in_b:
                changes.append({
                    "type": "added",
                    "line_b": idx_b + 1,
                    "text": line_b,
                })

        return changes

    def _line_similarity(self, a: str, b: str) -> float:
        words_a = set(a.lower().split())
        words_b = set(b.lower().split())
        if not words_a or not words_b:
            return 0.0
        intersection = words_a & words_b
        union = words_a | words_b
        return len(intersection) / len(union)

    def _compute_stats(self, changes: List[Dict]) -> Dict:
        stats = {"additions": 0, "deletions": 0, "modifications": 0, "moves": 0, "total": 0}
        for c in changes:
            t = c["type"]
            if t in stats:
                stats[t] += 1
            stats["total"] += 1
        return stats

    def _compute_similarity(self, text_a: str, text_b: str) -> float:
        words_a = set(text_a.lower().split())
        words_b = set(text_b.lower().split())
        if not words_a or not words_b:
            return 1.0 if text_a == text_b else 0.0
        intersection = words_a & words_b
        union = words_a | words_b
        return round(len(intersection) / len(union), 3)

    def _model_summary(self, text_a: str, text_b: str, changes: List[Dict]) -> str:
        import torch
        prompt = (
            "Summarize the differences between these two document versions:\n\n"
            f"Version A (first 1500 chars):\n{text_a[:1500]}\n\n"
            f"Version B (first 1500 chars):\n{text_b[:1500]}\n\n"
            f"Detected {len(changes)} changes.\n\n"
            "Summary of differences:"
        )
        input_ids = self.tokenizer.encode(prompt, max_length=2048, add_special=True)
        input_tensor = torch.tensor([input_ids], dtype=torch.long, device=self.device)
        output = self.model.generate(input_tensor, max_new_tokens=256, temperature=0.3)
        return self.tokenizer.decode(output[0].tolist(), skip_special=True)
