"""PDFMind 100M — Question Answering Task.

Answers questions about PDF content with citations and confidence scores.
Supports single-document and multi-document Q&A.
"""

from typing import Dict, List, Optional, Tuple


class PDFQuestionAnswerer:
    def __init__(self, model, tokenizer, device: str = "cpu"):
        self.model = model
        self.tokenizer = tokenizer
        self.device = device
        self.context_window = 3000

    def answer(
        self,
        question: str,
        context: str,
        max_length: int = 256,
        temperature: float = 0.3,
    ) -> Dict:
        prompt = (
            f"Based on the following document, answer the question.\n\n"
            f"Document:\n{context[:self.context_window]}\n\n"
            f"Question: {question}\n\n"
            f"Answer:"
        )
        response = self._generate(prompt, max_length, temperature)

        confidence = self._estimate_confidence(question, context, response)

        return {
            "answer": response,
            "confidence": confidence,
            "question": question,
            "sources": self._find_relevant_sentences(question, context),
        }

    def answer_with_citations(
        self, question: str, context: str, page_texts: Optional[List[str]] = None,
    ) -> Dict:
        result = self.answer(question, context)
        if page_texts:
            citations = []
            for i, page in enumerate(page_texts):
                if any(word.lower() in page.lower() for word in result["answer"].split()[:3]):
                    citations.append(i + 1)
            result["page_citations"] = citations
        return result

    def multi_qa(self, questions: List[str], context: str) -> List[Dict]:
        return [self.answer(q, context) for q in questions]

    def conversational(self, messages: List[Dict[str, str]], context: str) -> str:
        history = "\n".join(f"{m['role'].capitalize()}: {m['content']}" for m in messages[-5:])
        prompt = (
            f"Document context:\n{context[:self.context_window]}\n\n"
            f"Conversation:\n{history}\n\nAssistant:"
        )
        return self._generate(prompt, max_length=256, temperature=0.7)

    def _estimate_confidence(self, question: str, context: str, answer: str) -> float:
        if not answer or answer.lower() in ["i don't know", "not mentioned", "not found"]:
            return 0.0
        question_words = set(question.lower().split())
        context_words = set(context.lower().split())
        overlap = len(question_words & context_words) / max(len(question_words), 1)
        answer_words = set(answer.lower().split())
        answer_in_context = sum(1 for w in answer_words if w in context_words) / max(len(answer_words), 1)
        confidence = min(1.0, (overlap * 0.3 + answer_in_context * 0.7))
        return round(confidence, 2)

    def _find_relevant_sentences(self, question: str, context: str, n: int = 3) -> List[str]:
        sentences = [s.strip() for s in context.replace("\n", " ").split(".") if len(s.strip()) > 10]
        question_words = set(question.lower().split())
        scored = []
        for sent in sentences:
            sent_words = set(sent.lower().split())
            score = len(question_words & sent_words) / max(len(question_words), 1)
            scored.append((score, sent))
        scored.sort(reverse=True)
        return [s for _, s in scored[:n]]

    def _generate(self, prompt: str, max_length: int, temperature: float) -> str:
        import torch
        input_ids = self.tokenizer.encode(prompt, max_length=2048, add_special=True)
        input_tensor = torch.tensor([input_ids], dtype=torch.long, device=self.device)
        output = self.model.generate(input_tensor, max_new_tokens=max_length, temperature=temperature)
        return self.tokenizer.decode(output[0].tolist(), skip_special=True)
