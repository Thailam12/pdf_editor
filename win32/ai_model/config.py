"""PDFMind 100M — Model Configuration.

A ~100M parameter transformer for PDF-specific tasks.
Designed to run on integrated graphics (Intel Iris Xe / AMD Vega) and weak CPUs.
QLoRA training requires only ~400MB VRAM. Inference at ~100MB INT8.
"""

import json
import math
from dataclasses import dataclass, field
from typing import Optional


@dataclass
class PDFMindConfig:
    vocab_size: int = 32000
    max_seq_len: int = 2048
    n_layers: int = 24
    n_heads: int = 8
    n_kv_heads: int = 2
    d_model: int = 512
    d_ff: int = 1408
    dropout: float = 0.0
    layer_norm_eps: float = 1e-6
    rope_theta: float = 10000.0
    rope_scaling: Optional[float] = None
    activation: str = "swiglu"
    tie_word_embeddings: bool = False
    initializer_range: float = 0.02
    use_cache: bool = True
    pad_token_id: int = 0
    bos_token_id: int = 1
    eos_token_id: int = 2
    mask_token_id: int = 3
    head_dim: int = 64
    rms_norm: bool = True

    def __post_init__(self):
        if self.head_dim is None:
            self.head_dim = self.d_model // self.n_heads
        assert self.d_model % self.n_heads == 0, (
            f"d_model ({self.d_model}) must be divisible by n_heads ({self.n_heads})"
        )
        assert self.n_heads % self.n_kv_heads == 0, (
            f"n_heads ({self.n_heads}) must be divisible by n_kv_heads ({self.n_kv_heads})"
        )
        if self.d_ff is None:
            self.d_ff = int(self.d_model * 8 / 3)
            self.d_ff = ((self.d_ff + 255) // 256) * 256

    @property
    def n_kv_groups(self) -> int:
        return self.n_heads // self.n_kv_heads

    def count_params(self) -> int:
        embed = self.vocab_size * self.d_model
        if not self.tie_word_embeddings:
            embed += self.vocab_size * self.d_model
        attn_per_layer = 4 * self.d_model * self.d_model
        kv_per_layer = 2 * self.d_model * (self.d_model // self.n_heads * self.n_kv_heads)
        ffn_per_layer = 3 * self.d_model * self.d_ff
        norm_per_layer = 4 * self.d_model
        total = self.n_layers * (attn_per_layer + kv_per_layer + ffn_per_layer + norm_per_layer) + embed + self.d_model
        return total

    def estimate_memory_mb(self, dtype_bytes: int = 2) -> float:
        return self.count_params() * dtype_bytes / (1024 * 1024)

    def to_dict(self) -> dict:
        return {
            "vocab_size": self.vocab_size,
            "max_seq_len": self.max_seq_len,
            "n_layers": self.n_layers,
            "n_heads": self.n_heads,
            "n_kv_heads": self.n_kv_heads,
            "d_model": self.d_model,
            "d_ff": self.d_ff,
            "dropout": self.dropout,
            "layer_norm_eps": self.layer_norm_eps,
            "rope_theta": self.rope_theta,
            "rope_scaling": self.rope_scaling,
            "activation": self.activation,
            "tie_word_embeddings": self.tie_word_embeddings,
            "initializer_range": self.initializer_range,
            "use_cache": self.use_cache,
            "pad_token_id": self.pad_token_id,
            "bos_token_id": self.bos_token_id,
            "eos_token_id": self.eos_token_id,
            "mask_token_id": self.mask_token_id,
            "head_dim": self.head_dim,
            "rms_norm": self.rms_norm,
        }

    @classmethod
    def from_dict(cls, d: dict) -> "PDFMindConfig":
        return cls(**{k: v for k, v in d.items() if k in cls.__dataclass_fields__})

    def save(self, path: str):
        with open(path, "w") as f:
            json.dump(self.to_dict(), f, indent=2)

    @classmethod
    def load(cls, path: str) -> "PDFMindConfig":
        with open(path) as f:
            return cls.from_dict(json.load(f))


PRETRAINED_CONFIG = PDFMindConfig(
    vocab_size=32000,
    max_seq_len=2048,
    n_layers=24,
    n_heads=8,
    n_kv_heads=2,
    d_model=512,
    d_ff=1408,
    dropout=0.0,
    rope_theta=10000.0,
    activation="swiglu",
    tie_word_embeddings=False,
    rms_norm=True,
)

QLORA_CONFIG = {
    "r": 16,
    "lora_alpha": 32,
    "lora_dropout": 0.05,
    "target_modules": ["q_proj", "k_proj", "v_proj", "o_proj", "gate_proj", "up_proj", "down_proj"],
    "bias": "none",
    "task_type": "CAUSAL_LM",
}

QUANTIZATION_CONFIG = {
    "load_in_4bit": True,
    "bnb_4bit_quant_type": "nf4",
    "bnb_4bit_compute_dtype": "bfloat16",
    "bnb_4bit_use_double_quant": True,
}

TRAINING_CONFIG = {
    "output_dir": "./checkpoints/pdfmind-100m",
    "num_train_epochs": 3,
    "per_device_train_batch_size": 4,
    "gradient_accumulation_steps": 8,
    "learning_rate": 2e-4,
    "weight_decay": 0.01,
    "warmup_steps": 500,
    "max_grad_norm": 1.0,
    "logging_steps": 10,
    "save_steps": 500,
    "eval_steps": 500,
    "fp16": False,
    "bf16": True,
    "optim": "paged_adamw_8bit",
    "lr_scheduler_type": "cosine",
    "seed": 42,
    "report_to": "tensorboard",
    "dataloader_num_workers": 4,
    "gradient_checkpointing": True,
    "max_seq_length": 2048,
}

DISTILLATION_CONFIG = {
    "teacher_model": "mistralai/Mistral-7B-Instruct-v0.3",
    "temperature": 2.0,
    "alpha": 0.5,
    "max_length": 2048,
    "batch_size": 2,
}
