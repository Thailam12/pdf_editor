"""PDFMind 100M — Knowledge Distillation Pipeline.

Distills knowledge from a larger teacher model (e.g., Mistral 7B) into
the 100M student model. Uses soft labels with temperature scaling.

This is how we get "7B-quality" reasoning in a 100M package:
1. Teacher generates responses on PDF tasks
2. Student learns from both hard labels AND teacher probability distributions
3. Combined with QLoRA for efficient training
"""

import json
import os
import time
from dataclasses import dataclass
from typing import Dict, List, Optional, Tuple

import torch
import torch.nn as nn
import torch.nn.functional as F
from torch.utils.data import DataLoader, Dataset

from .config import PDFMindConfig, PDFMindConfig as ModelConfig
from .model import PDFMindForCausalLM
from .train_qlora import apply_lora, QLoRATrainer


class TeacherLogitsDataset(Dataset):
    """Dataset with pre-computed teacher logits for distillation."""

    def __init__(self, data: List[Dict], tokenizer, max_length: int = 2048):
        self.data = data
        self.tokenizer = tokenizer
        self.max_length = max_length

    def __len__(self):
        return len(self.data)

    def __getitem__(self, idx) -> Dict[str, torch.Tensor]:
        item = self.data[idx]
        text = item.get("text", item.get("instruction", "") + "\n" + item.get("output", ""))

        token_ids = self.tokenizer.encode(text, max_length=self.max_length)
        input_ids = torch.tensor(token_ids[:self.max_length], dtype=torch.long)

        if len(input_ids) < self.max_length:
            pad_len = self.max_length - len(input_ids)
            input_ids = torch.cat([input_ids, torch.zeros(pad_len, dtype=torch.long)])

        attention_mask = (input_ids != 0).long()
        labels = input_ids.clone()
        labels[labels == 0] = -100

        result = {
            "input_ids": input_ids,
            "attention_mask": attention_mask,
            "labels": labels,
        }

        if "teacher_logits" in item:
            logits = torch.tensor(item["teacher_logits"], dtype=torch.float32)
            if logits.shape[0] < self.max_length:
                pad_len = self.max_length - logits.shape[0]
                logits = torch.cat([logits, torch.zeros(pad_len, logits.shape[1])])
            result["teacher_logits"] = logits[:self.max_length]

        return result


@dataclass
class DistillationLoss(nn.Module):
    """Combined distillation + cross-entropy loss."""

    def __init__(self, temperature: float = 2.0, alpha: float = 0.5):
        super().__init__()
        self.temperature = temperature
        self.alpha = alpha

    def forward(
        self,
        student_logits: torch.Tensor,
        labels: torch.Tensor,
        teacher_logits: Optional[torch.Tensor] = None,
    ) -> Tuple[torch.Tensor, Dict[str, float]]:
        ce_loss = F.cross_entropy(
            student_logits[:, :-1, :].contiguous().view(-1, student_logits.size(-1)),
            labels[:, 1:].contiguous().view(-1),
            ignore_index=-100,
        )

        if teacher_logits is None:
            return ce_loss, {"ce_loss": ce_loss.item()}

        T = self.temperature
        s_log_prob = F.log_softmax(student_logits[:, :-1, :] / T, dim=-1)
        t_log_prob = F.log_softmax(teacher_logits[:, :-1, :] / T, dim=-1)

        kl_loss = F.kl_div(
            s_log_prob, t_log_prob.exp(),
            reduction="batchmean",
        ) * (T * T)

        total_loss = self.alpha * kl_loss + (1.0 - self.alpha) * ce_loss

        return total_loss, {
            "total_loss": total_loss.item(),
            "ce_loss": ce_loss.item(),
            "kl_loss": kl_loss.item(),
        }


class DistillationTrainer:
    """Knowledge distillation trainer for PDFMind."""

    def __init__(
        self,
        student_model: PDFMindForCausalLM,
        train_loader: DataLoader,
        eval_loader: Optional[DataLoader] = None,
        temperature: float = 2.0,
        alpha: float = 0.5,
        lr: float = 1e-4,
        weight_decay: float = 0.01,
        warmup_steps: int = 200,
        max_grad_norm: float = 1.0,
        gradient_accumulation_steps: int = 4,
        output_dir: str = "./checkpoints/pdfmind-distill",
        device: str = "cpu",
    ):
        self.device = torch.device(device)
        self.model = student_model.to(self.device)
        self.train_loader = train_loader
        self.eval_loader = eval_loader
        self.max_grad_norm = max_grad_norm
        self.gradient_accumulation_steps = gradient_accumulation_steps
        self.output_dir = output_dir
        self.step = 0
        self.epoch = 0

        self.criterion = DistillationLoss(temperature=temperature, alpha=alpha)

        trainable_params = [p for p in self.model.parameters() if p.requires_grad]
        self.optimizer = torch.optim.AdamW(
            trainable_params, lr=lr, weight_decay=weight_decay,
        )

        total_steps = len(train_loader) * 3 // gradient_accumulation_steps
        self.scheduler = self._cosine_schedule_with_warmup(lr, warmup_steps, total_steps)

        os.makedirs(output_dir, exist_ok=True)

    def _cosine_schedule_with_warmup(self, lr, warmup, total):
        def lr_lambda(step):
            if step < warmup:
                return step / max(1, warmup)
            progress = (step - warmup) / max(1, total - warmup)
            return max(0.0, 0.5 * (1.0 + math.cos(math.pi * progress)))
        return torch.optim.lr_scheduler.LambdaLR(self.optimizer, lr_lambda)

    def train_epoch(self):
        import math
        self.model.train()
        total_loss = 0.0
        start_time = time.time()

        for batch_idx, batch in enumerate(self.train_loader):
            input_ids = batch["input_ids"].to(self.device)
            attention_mask = batch["attention_mask"].to(self.device)
            labels = batch["labels"].to(self.device)
            teacher_logits = batch.get("teacher_logits")
            if teacher_logits is not None:
                teacher_logits = teacher_logits.to(self.device)

            student_logits, _, _ = self.model(input_ids)
            loss, metrics = self.criterion(student_logits, labels, teacher_logits)
            loss = loss / self.gradient_accumulation_steps
            loss.backward()

            total_loss += loss.item() * self.gradient_accumulation_steps

            if (batch_idx + 1) % self.gradient_accumulation_steps == 0:
                torch.nn.utils.clip_grad_norm_(
                    [p for p in self.model.parameters() if p.requires_grad],
                    self.max_grad_norm,
                )
                self.optimizer.step()
                self.scheduler.step()
                self.optimizer.zero_grad()
                self.step += 1

                if self.step % 10 == 0:
                    elapsed = time.time() - start_time
                    print(f"Step {self.step} | Loss: {metrics.get('total_loss', 0):.4f} | "
                          f"CE: {metrics.get('ce_loss', 0):.4f} | KL: {metrics.get('kl_loss', 0):.4f}")

        self.epoch += 1
        avg_loss = total_loss / max(len(self.train_loader), 1)
        print(f"Epoch {self.epoch} complete. Avg Loss: {avg_loss:.4f}")
        return avg_loss

    def train(self, num_epochs: int = 3):
        print(f"Starting distillation training for {num_epochs} epochs")
        for _ in range(num_epochs):
            self.train_epoch()
            if self.eval_loader:
                self.evaluate()
            self.save_checkpoint(f"epoch-{self.epoch}")

        self.save_checkpoint("final")
        self.export_weights()
        print("Distillation complete!")

    def evaluate(self) -> float:
        if self.eval_loader is None:
            return 0.0
        self.model.eval()
        total_loss = 0.0
        n = 0
        with torch.no_grad():
            for batch in self.eval_loader:
                input_ids = batch["input_ids"].to(self.device)
                labels = batch["labels"].to(self.device)
                teacher_logits = batch.get("teacher_logits")
                if teacher_logits is not None:
                    teacher_logits = teacher_logits.to(self.device)
                logits, _, _ = self.model(input_ids)
                loss, _ = self.criterion(logits, labels, teacher_logits)
                total_loss += loss.item()
                n += 1
        avg = total_loss / max(n, 1)
        print(f"Eval Loss: {avg:.4f}")
        self.model.train()
        return avg

    def save_checkpoint(self, name: str):
        path = os.path.join(self.output_dir, name)
        os.makedirs(path, exist_ok=True)
        state = {n: p.cpu().detach() for n, p in self.model.named_parameters() if p.requires_grad}
        torch.save({"state_dict": state, "config": self.model.config.to_dict()},
                    os.path.join(path, "checkpoint.pt"))

    def export_weights(self):
        path = os.path.join(self.output_dir, "distilled_weights.pt")
        state = {n: p.cpu().detach() for n, p in self.model.named_parameters()}
        torch.save(state, path)
        size_mb = os.path.getsize(path) / (1024 * 1024)
        print(f"Distilled weights exported: {path} ({size_mb:.2f} MB)")


def generate_teacher_data(
    teacher_model_name: str,
    prompts: List[str],
    max_length: int = 512,
    temperature: float = 1.0,
) -> List[Dict]:
    """Generate teacher logits for distillation data."""
    try:
        from transformers import AutoModelForCausalLM, AutoTokenizer
    except ImportError:
        print("Install transformers: pip install transformers")
        return []

    print(f"Loading teacher model: {teacher_model_name}")
    tokenizer = AutoTokenizer.from_pretrained(teacher_model_name)
    model = AutoModelForCausalLM.from_pretrained(
        teacher_model_name, torch_dtype=torch.float16, device_map="auto",
    )
    model.eval()

    data = []
    for i, prompt in enumerate(prompts):
        inputs = tokenizer(prompt, return_tensors="pt", truncation=True, max_length=max_length)
        inputs = {k: v.to(model.device) for k, v in inputs.items()}

        with torch.no_grad():
            outputs = model(**inputs)
            logits = outputs.logits.cpu().float()

        response = model.generate(**inputs, max_new_tokens=256, temperature=temperature)
        response_text = tokenizer.decode(response[0], skip_special_tokens=True)

        data.append({
            "text": response_text,
            "teacher_logits": logits.numpy().tolist(),
            "prompt": prompt,
        })

        if (i + 1) % 100 == 0:
            print(f"Generated {i + 1}/{len(prompts)} teacher samples")

    return data
