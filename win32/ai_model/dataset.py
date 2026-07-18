"""PDFMind 100M — Dataset Loaders.

Handles loading and preprocessing of training data for all PDF-specific tasks:
- Pre-training: general text corpus
- QLoRA fine-tuning: instruction-following data
- Distillation: teacher model outputs
- Task-specific: summarization, Q&A, redaction, OCR, forms, comparison

Supports HuggingFace datasets, local JSON/JSONL files, and streaming.
"""

import json
import os
import random
from typing import Dict, List, Optional, Tuple

import torch
from torch.utils.data import Dataset, DataLoader, random_split


class TextDataset(Dataset):
    def __init__(self, texts: List[str], tokenizer, max_length: int = 2048):
        self.texts = texts
        self.tokenizer = tokenizer
        self.max_length = max_length

    def __len__(self):
        return len(self.texts)

    def __getitem__(self, idx) -> Dict[str, torch.Tensor]:
        text = self.texts[idx]
        token_ids = self.tokenizer.encode(text, max_length=self.max_length, add_special=True)

        if len(token_ids) < 2:
            token_ids = [1] + token_ids + [2]

        input_ids = torch.tensor(token_ids, dtype=torch.long)
        labels = input_ids.clone()
        attention_mask = torch.ones_like(input_ids)

        if len(input_ids) < self.max_length:
            pad_len = self.max_length - len(input_ids)
            input_ids = torch.cat([input_ids, torch.zeros(pad_len, dtype=torch.long)])
            labels = torch.cat([labels, torch.full((pad_len,), -100, dtype=torch.long)])
            attention_mask = torch.cat([attention_mask, torch.zeros(pad_len, dtype=torch.long)])

        return {
            "input_ids": input_ids[:self.max_length],
            "attention_mask": attention_mask[:self.max_length],
            "labels": labels[:self.max_length],
        }


class InstructionDataset(Dataset):
    def __init__(self, data: List[Dict], tokenizer, max_length: int = 2048, task_prefix: str = ""):
        self.data = data
        self.tokenizer = tokenizer
        self.max_length = max_length
        self.task_prefix = task_prefix

    def __len__(self):
        return len(self.data)

    def __getitem__(self, idx) -> Dict[str, torch.Tensor]:
        item = self.data[idx]
        instruction = item.get("instruction", item.get("input", ""))
        response = item.get("response", item.get("output", ""))

        if self.task_prefix:
            prompt = f"{self.task_prefix}\n{instruction}\n\nResponse:"
        else:
            prompt = instruction

        full_text = f"{prompt}\n{response}"
        token_ids = self.tokenizer.encode(full_text, max_length=self.max_length)
        prompt_ids = self.tokenizer.encode(prompt, max_length=self.max_length)

        labels = torch.full((self.max_length,), -100, dtype=torch.long)
        for i in range(len(prompt_ids), min(len(token_ids), self.max_length)):
            labels[i] = token_ids[i]

        input_ids = torch.tensor(token_ids[:self.max_length], dtype=torch.long)
        attention_mask = torch.ones_like(input_ids)

        if len(input_ids) < self.max_length:
            pad_len = self.max_length - len(input_ids)
            input_ids = torch.cat([input_ids, torch.zeros(pad_len, dtype=torch.long)])
            attention_mask = torch.cat([attention_mask, torch.zeros(pad_len, dtype=torch.long)])

        return {
            "input_ids": input_ids,
            "attention_mask": attention_mask,
            "labels": labels,
        }


class DistillationDataset(Dataset):
    def __init__(self, data: List[Dict], tokenizer, max_length: int = 2048):
        self.data = data
        self.tokenizer = tokenizer
        self.max_length = max_length

    def __len__(self):
        return len(self.data)

    def __getitem__(self, idx) -> Dict[str, torch.Tensor]:
        item = self.data[idx]
        input_text = item["input"]
        teacher_logits = item.get("teacher_logits", None)

        input_ids = self.tokenizer.encode(input_text, max_length=self.max_length)
        input_ids_tensor = torch.tensor(input_ids[:self.max_length], dtype=torch.long)
        attention_mask = torch.ones_like(input_ids_tensor)

        if len(input_ids_tensor) < self.max_length:
            pad_len = self.max_length - len(input_ids_tensor)
            input_ids_tensor = torch.cat([input_ids_tensor, torch.zeros(pad_len, dtype=torch.long)])
            attention_mask = torch.cat([attention_mask, torch.zeros(pad_len, dtype=torch.long)])

        result = {
            "input_ids": input_ids_tensor,
            "attention_mask": attention_mask,
            "labels": input_ids_tensor.clone(),
        }

        if teacher_logits is not None:
            logits = torch.tensor(teacher_logits, dtype=torch.float32)
            if logits.shape[0] < self.max_length:
                pad_len = self.max_length - logits.shape[0]
                logits = torch.cat([logits, torch.zeros(pad_len, logits.shape[1])])
            result["teacher_logits"] = logits[:self.max_length]

        return result


class PDFDatasetLoader:
    """Unified dataset loader for all PDFMind training phases."""

    TASK_PREFIXES = {
        "summarize": "Summarize the following PDF content:",
        "qa": "Answer the question based on the PDF content:",
        "redact": "Identify PII/PHI entities that should be redacted:",
        "ocr_correct": "Correct the OCR errors in this text:",
        "form_extract": "Extract form field information:",
        "compare": "Compare these two documents and list differences:",
        "translate": "Translate the following text:",
        "proofread": "Proofread and correct this text:",
    }

    @staticmethod
    def load_jsonl(path: str) -> List[Dict]:
        data = []
        with open(path, encoding="utf-8") as f:
            for line in f:
                line = line.strip()
                if line:
                    data.append(json.loads(line))
        return data

    @staticmethod
    def load_json(path: str) -> List[Dict]:
        with open(path, encoding="utf-8") as f:
            data = json.load(f)
        if isinstance(data, list):
            return data
        return [data]

    @classmethod
    def load_dataset(cls, path: str) -> List[Dict]:
        if os.path.isdir(path):
            all_data = []
            for fname in sorted(os.listdir(path)):
                fpath = os.path.join(path, fname)
                if fname.endswith(".jsonl"):
                    all_data.extend(cls.load_jsonl(fpath))
                elif fname.endswith(".json"):
                    all_data.extend(cls.load_json(fpath))
            return all_data
        elif path.endswith(".jsonl"):
            return cls.load_jsonl(path)
        elif path.endswith(".json"):
            return cls.load_json(path)
        else:
            raise ValueError(f"Unsupported file format: {path}")

    @classmethod
    def load_hf_dataset(cls, name: str, split: str = "train") -> List[Dict]:
        try:
            from datasets import load_dataset
            ds = load_dataset(name, split=split, trust_remote_code=True)
            return [dict(item) for item in ds]
        except ImportError:
            print("Install `datasets` for HuggingFace dataset support: pip install datasets")
            return []

    @classmethod
    def create_pretraining_data(cls, paths: List[str]) -> List[str]:
        texts = []
        for path in paths:
            data = cls.load_dataset(path)
            for item in data:
                text = item.get("text", item.get("content", ""))
                if text and len(text) > 50:
                    texts.append(text)
        return texts

    @classmethod
    def create_instruction_data(cls, paths: List[str], task: str = "") -> List[Dict]:
        all_data = []
        for path in paths:
            data = cls.load_dataset(path)
            for item in data:
                if task and task in cls.TASK_PREFIXES:
                    item["task_prefix"] = cls.TASK_PREFIXES[task]
                all_data.append(item)
        return all_data

    @staticmethod
    def prepare_dataloaders(
        dataset: Dataset,
        tokenizer,
        batch_size: int = 4,
        train_split: float = 0.9,
        num_workers: int = 0,
    ) -> Tuple[DataLoader, DataLoader]:
        train_size = int(len(dataset) * train_split)
        eval_size = len(dataset) - train_size
        train_ds, eval_ds = random_split(dataset, [train_size, eval_size])

        train_loader = DataLoader(
            train_ds, batch_size=batch_size, shuffle=True,
            num_workers=num_workers, pin_memory=True, drop_last=True,
        )
        eval_loader = DataLoader(
            eval_ds, batch_size=batch_size, shuffle=False,
            num_workers=num_workers, pin_memory=True,
        )
        return train_loader, eval_loader

    @staticmethod
    def create_synthetic_pdf_data(n_samples: int = 1000) -> List[Dict]:
        """Generate synthetic training data for PDF-specific tasks."""
        data = []
        templates = {
            "summarize": [
                {"input": "This document discusses the quarterly financial results...", "output": "Q3 financial summary with revenue growth."},
                {"input": "The research paper presents a novel approach to...", "output": "Novel methodology for the described research area."},
            ],
            "qa": [
                {"input": "What is the revenue? The revenue was $1.2M in Q3.", "output": "$1.2M in Q3"},
                {"input": "When was the report published? Published March 15, 2026.", "output": "March 15, 2026"},
            ],
            "redact": [
                {"input": "John Smith SSN: 123-45-6789 email: john@example.com", "output": "PERSON: John Smith, SSN: [REDACTED], EMAIL: [REDACTED]"},
                {"input": "Call 555-0123 or visit 123 Main St, New York", "output": "PHONE: [REDACTED], ADDRESS: [REDACTED]"},
            ],
        }

        for task, examples in templates.items():
            prefix = PDFDatasetLoader.TASK_PREFIXES.get(task, "")
            for _ in range(n_samples // len(templates)):
                example = random.choice(examples)
                data.append({
                    "instruction": f"{prefix}\n{example['input']}",
                    "response": example["output"],
                    "task": task,
                })
        return data

    @staticmethod
    def generate_pii_training_data(n_samples: int = 5000) -> List[Dict]:
        """Generate synthetic PII detection training data."""
        import random
        names = ["John Smith", "Jane Doe", "Bob Johnson", "Alice Brown", "Charlie Wilson",
                 "Maria Garcia", "David Lee", "Sarah Kim", "Michael Wang", "Emily Davis"]
        emails = ["john@example.com", "jane@corp.org", "bob@work.net", "alice@school.edu"]
        phones = ["555-0123", "555-0456", "555-0789", "555-1234", "555-5678"]
        addresses = ["123 Main St, New York, NY 10001", "456 Oak Ave, Los Angeles, CA 90001",
                     "789 Pine Rd, Chicago, IL 60601"]
        ssns = ["123-45-6789", "987-65-4321", "555-12-3456"]

        data = []
        for _ in range(n_samples):
            text_parts = []
            labels = []
            n_entities = random.randint(1, 5)
            for _ in range(n_entities):
                etype = random.choice(["NAME", "EMAIL", "PHONE", "ADDRESS", "SSN"])
                if etype == "NAME":
                    val = random.choice(names)
                    text_parts.append(f"Name: {val}")
                    labels.append(f"NAME: {val}")
                elif etype == "EMAIL":
                    val = random.choice(emails)
                    text_parts.append(f"Email: {val}")
                    labels.append(f"EMAIL: {val}")
                elif etype == "PHONE":
                    val = random.choice(phones)
                    text_parts.append(f"Phone: {val}")
                    labels.append(f"PHONE: {val}")
                elif etype == "ADDRESS":
                    val = random.choice(addresses)
                    text_parts.append(f"Address: {val}")
                    labels.append(f"ADDRESS: {val}")
                elif etype == "SSN":
                    val = random.choice(ssns)
                    text_parts.append(f"SSN: {val}")
                    labels.append(f"SSN: [REDACTED]")

            data.append({
                "instruction": f"Identify and redact PII:\n{text_parts[0]}",
                "response": labels[0],
                "task": "redact",
            })
        return data
