"""PDFMind 100M — Pre-training Pipeline.

Stage 1 of training: Pre-train the base transformer on a general text corpus
followed by PDF-specific text. This gives the model language understanding
before task-specific fine-tuning.

Training stages:
1. General corpus pre-training (Wikipedia, Books, WebText)
2. PDF-specific corpus (academic papers, legal docs, financial reports)
3. Curriculum learning: easy -> hard documents
"""

import json
import math
import os
import time
from typing import Dict, List, Optional

import torch
import torch.nn as nn
from torch.utils.data import DataLoader

from .config import PDFMindConfig, PDFMindConfig as ModelConfig
from .model import PDFMindForCausalLM
from .dataset import TextDataset, PDFDatasetLoader


class PreTrainer:
    """Pre-training loop for PDFMind base model."""

    def __init__(
        self,
        model: PDFMindForCausalLM,
        train_loader: DataLoader,
        eval_loader: Optional[DataLoader] = None,
        lr: float = 3e-4,
        weight_decay: float = 0.1,
        warmup_steps: int = 1000,
        max_grad_norm: float = 1.0,
        gradient_accumulation_steps: int = 4,
        logging_steps: int = 10,
        save_steps: int = 1000,
        output_dir: str = "./checkpoints/pdfmind-pretrain",
        bf16: bool = True,
        device: str = "auto",
    ):
        if device == "auto":
            if torch.cuda.is_available():
                self.device = torch.device("cuda")
            elif hasattr(torch.backends, "mps") and torch.backends.mps.is_available():
                self.device = torch.device("mps")
            else:
                self.device = torch.device("cpu")
        else:
            self.device = torch.device(device)

        self.model = model.to(self.device)
        self.train_loader = train_loader
        self.eval_loader = eval_loader
        self.max_grad_norm = max_grad_norm
        self.gradient_accumulation_steps = gradient_accumulation_steps
        self.logging_steps = logging_steps
        self.save_steps = save_steps
        self.output_dir = output_dir
        self.bf16 = bf16 and self.device.type == "cuda"
        self.step = 0
        self.epoch = 0
        self.best_eval_loss = float("inf")

        self.optimizer = torch.optim.AdamW(
            model.parameters(), lr=lr, weight_decay=weight_decay,
            betas=(0.9, 0.95), eps=1e-8,
        )

        total_steps = len(train_loader) * 10 // gradient_accumulation_steps
        self.scheduler = self._cosine_with_warmup(lr, warmup_steps, total_steps)
        self.scaler = torch.amp.GradScaler("cuda") if self.device.type == "cuda" else None

        os.makedirs(output_dir, exist_ok=True)

    def _cosine_with_warmup(self, lr, warmup, total):
        def lr_lambda(step):
            if step < warmup:
                return step / max(1, warmup)
            progress = (step - warmup) / max(1, total - warmup)
            return max(0.01, 0.5 * (1.0 + math.cos(math.pi * progress)))
        return torch.optim.lr_scheduler.LambdaLR(self.optimizer, lr_lambda)

    def train_epoch(self) -> float:
        self.model.train()
        total_loss = 0.0
        start_time = time.time()

        for batch_idx, batch in enumerate(self.train_loader):
            input_ids = batch["input_ids"].to(self.device)
            attention_mask = batch["attention_mask"].to(self.device)
            labels = batch["labels"].to(self.device)

            use_amp = self.bf16 and self.device.type == "cuda"
            with torch.amp.autocast("cuda", enabled=use_amp, dtype=torch.bfloat16):
                _, loss, _ = self.model(input_ids, labels=labels)

            loss = loss / self.gradient_accumulation_steps

            if self.scaler:
                self.scaler.scale(loss).backward()
            else:
                loss.backward()

            total_loss += loss.item() * self.gradient_accumulation_steps

            if (batch_idx + 1) % self.gradient_accumulation_steps == 0:
                if self.scaler:
                    self.scaler.unscale_(self.optimizer)
                    torch.nn.utils.clip_grad_norm_(self.model.parameters(), self.max_grad_norm)
                    self.scaler.step(self.optimizer)
                    self.scaler.update()
                else:
                    torch.nn.utils.clip_grad_norm_(self.model.parameters(), self.max_grad_norm)
                    self.optimizer.step()

                self.scheduler.step()
                self.optimizer.zero_grad()
                self.step += 1

                if self.step % self.logging_steps == 0:
                    elapsed = time.time() - start_time
                    avg_loss = total_loss / (batch_idx + 1)
                    lr = self.scheduler.get_last_lr()[0]
                    print(f"Step {self.step} | Loss: {avg_loss:.4f} | LR: {lr:.2e} | Time: {elapsed:.1f}s")

                if self.step % self.save_steps == 0:
                    self.save_checkpoint(f"step-{self.step}")

        self.epoch += 1
        return total_loss / max(len(self.train_loader), 1)

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
                _, loss, _ = self.model(input_ids, labels=labels)
                total_loss += loss.item()
                n += 1

        avg_loss = total_loss / max(n, 1)
        print(f"Eval Loss: {avg_loss:.4f}")

        if avg_loss < self.best_eval_loss:
            self.best_eval_loss = avg_loss
            self.save_checkpoint("best")

        self.model.train()
        return avg_loss

    def train(self, num_epochs: int = 10):
        print(f"Starting pre-training for {num_epochs} epochs")
        print(f"Device: {self.device}")
        params = self.model.count_parameters()
        print(f"Total params: {params['total_m']} | Trainable: {params['trainable_m']}")

        for _ in range(num_epochs):
            self.train_epoch()
            self.evaluate()
            self.save_checkpoint(f"epoch-{self.epoch}")

        self.save_checkpoint("final")
        print("Pre-training complete!")

    def save_checkpoint(self, name: str):
        path = os.path.join(self.output_dir, name)
        os.makedirs(path, exist_ok=True)
        torch.save({
            "step": self.step,
            "epoch": self.epoch,
            "model_config": self.model.config.to_dict(),
            "model_state_dict": self.model.state_dict(),
            "optimizer_state_dict": self.optimizer.state_dict(),
            "best_eval_loss": self.best_eval_loss,
        }, os.path.join(path, "checkpoint.pt"))
        print(f"Checkpoint saved: {path}")


def pretrain_from_config(config_path: Optional[str] = None):
    """Pre-train from a config file."""
    if config_path:
        config = PDFMindConfig.load(config_path)
    else:
        config = ModelConfig()

    model = PDFMindForCausalLM(config)

    tokenizer_dir = "./tokenizer"
    if os.path.exists(tokenizer_dir):
        from .tokenizer import PDFMindTokenizer
        tokenizer = PDFMindTokenizer.load(tokenizer_dir)
    else:
        print("No tokenizer found. Run tokenizer training first.")
        return

    data_paths = [
        "./data/pretrain_texts.jsonl",
        "./data/pdf_corpus.jsonl",
    ]

    existing_paths = [p for p in data_paths if os.path.exists(p)]
    if not existing_paths:
        print("No training data found. Place data files in ./data/")
        print("Expected: pretrain_texts.jsonl, pdf_corpus.jsonl")
        return

    texts = PDFDatasetLoader.create_pretraining_data(existing_paths)
    print(f"Loaded {len(texts)} text samples")

    max_length = config.max_seq_len
    dataset = TextDataset(texts, tokenizer, max_length=max_length)

    train_size = int(len(dataset) * 0.95)
    eval_size = len(dataset) - train_size
    train_ds, eval_ds = torch.utils.data.random_split(dataset, [train_size, eval_size])

    train_loader = DataLoader(train_ds, batch_size=4, shuffle=True, drop_last=True)
    eval_loader = DataLoader(eval_ds, batch_size=4, shuffle=False)

    trainer = PreTrainer(
        model=model,
        train_loader=train_loader,
        eval_loader=eval_loader,
        output_dir="./checkpoints/pdfmind-pretrain",
    )

    trainer.train(num_epochs=10)


if __name__ == "__main__":
    pretrain_from_config()
