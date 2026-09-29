"""PDFMind 100M — Transformer Architecture.

GPT-style decoder-only transformer with:
- SwiGLU activation (4/3 hidden dim expansion)
- Rotary Position Embeddings (RoPE)
- RMSNorm (faster than LayerNorm)
- Grouped Query Attention (GQA: 8 Q heads, 2 KV heads)
- ~100M parameters total

Designed for QLoRA training and INT8/INT4 deployment.
Runs on CPU, integrated GPU (Vulkan), or discrete GPU.
"""

import math
import struct
from typing import Optional, Tuple

import torch
import torch.nn as nn
import torch.nn.functional as F

from .config import PDFMindConfig


def precompute_freqs_cis(dim: int, max_seq_len: int, theta: float = 10000.0) -> torch.Tensor:
    freqs = 1.0 / (theta ** (torch.arange(0, dim, 2).float() / dim))
    t = torch.arange(max_seq_len).float()
    freqs = torch.outer(t, freqs)
    return torch.polar(torch.ones_like(freqs), freqs)


def apply_rotary_emb(x: torch.Tensor, freqs_cis: torch.Tensor) -> torch.Tensor:
    x_complex = torch.view_as_complex(x.float().reshape(*x.shape[:-1], -1, 2))
    freqs_cis = freqs_cis.expand_as(x_complex)
    x_rotated = torch.view_as_real(x_complex * freqs_cis).flatten(-2)
    return x_rotated.type_as(x)


class RMSNorm(nn.Module):
    def __init__(self, dim: int, eps: float = 1e-6):
        super().__init__()
        self.eps = eps
        self.weight = nn.Parameter(torch.ones(dim))

    def forward(self, x: torch.Tensor) -> torch.Tensor:
        norm = x.float().pow(2).mean(-1, keepdim=True).add(self.eps).rsqrt()
        return (x.float() * norm).type_as(x) * self.weight


class SwiGLU(nn.Module):
    def __init__(self, d_model: int, d_ff: int, dropout: float = 0.0):
        super().__init__()
        self.w_gate = nn.Linear(d_model, d_ff, bias=False)
        self.w_up = nn.Linear(d_model, d_ff, bias=False)
        self.w_down = nn.Linear(d_ff, d_model, bias=False)
        self.dropout = nn.Dropout(dropout)

    def forward(self, x: torch.Tensor) -> torch.Tensor:
        gate = F.silu(self.w_gate(x))
        up = self.w_up(x)
        return self.dropout(self.w_down(gate * up))


class GroupedQueryAttention(nn.Module):
    def __init__(self, config: PDFMindConfig):
        super().__init__()
        self.n_heads = config.n_heads
        self.n_kv_heads = config.n_kv_heads
        self.head_dim = config.head_dim
        self.n_kv_groups = config.n_heads // config.n_kv_heads

        self.q_proj = nn.Linear(config.d_model, config.n_heads * config.head_dim, bias=False)
        self.k_proj = nn.Linear(config.d_model, config.n_kv_heads * config.head_dim, bias=False)
        self.v_proj = nn.Linear(config.d_model, config.n_kv_heads * config.head_dim, bias=False)
        self.o_proj = nn.Linear(config.n_heads * config.head_dim, config.d_model, bias=False)

        self.attn_dropout = nn.Dropout(config.dropout)
        self.resid_dropout = nn.Dropout(config.dropout)

        self.register_buffer(
            "freqs_cis",
            precompute_freqs_cis(config.head_dim, config.max_seq_len * 2, config.rope_theta),
            persistent=False,
        )

    def forward(
        self,
        x: torch.Tensor,
        mask: Optional[torch.Tensor] = None,
        kv_cache: Optional[Tuple[torch.Tensor, torch.Tensor]] = None,
    ) -> Tuple[torch.Tensor, Optional[Tuple[torch.Tensor, torch.Tensor]]]:
        B, T, C = x.shape

        q = self.q_proj(x).view(B, T, self.n_heads, self.head_dim).transpose(1, 2)
        k = self.k_proj(x).view(B, T, self.n_kv_heads, self.head_dim).transpose(1, 2)
        v = self.v_proj(x).view(B, T, self.n_kv_heads, self.head_dim).transpose(1, 2)

        seq_start = 0
        if kv_cache is not None:
            k_cache, v_cache = kv_cache
            seq_start = k_cache.shape[2]
            k = torch.cat([k_cache, k], dim=2)
            v = torch.cat([v_cache, v], dim=2)
        new_kv_cache = (k, v) if kv_cache is not None or T > 0 else None

        freqs = self.freqs_cis[seq_start:seq_start + T].unsqueeze(0).unsqueeze(0)
        q = apply_rotary_emb(q, freqs)
        k = apply_rotary_emb(k, freqs)

        if self.n_kv_groups > 1:
            k = k.repeat_interleave(self.n_kv_groups, dim=1)
            v = v.repeat_interleave(self.n_kv_groups, dim=1)

        scale = 1.0 / math.sqrt(self.head_dim)
        attn = torch.matmul(q, k.transpose(-2, -1)) * scale

        if mask is not None:
            attn = attn.masked_fill(mask == 0, float("-inf"))

        attn = F.softmax(attn, dim=-1)
        attn = self.attn_dropout(attn)

        out = torch.matmul(attn, v)
        out = out.transpose(1, 2).contiguous().view(B, T, self.n_heads * self.head_dim)
        return self.resid_dropout(self.o_proj(out)), new_kv_cache


class TransformerBlock(nn.Module):
    def __init__(self, config: PDFMindConfig):
        super().__init__()
        self.norm1 = RMSNorm(config.d_model, config.layer_norm_eps)
        self.attn = GroupedQueryAttention(config)
        self.norm2 = RMSNorm(config.d_model, config.layer_norm_eps)
        self.ffn = SwiGLU(config.d_model, config.d_ff, config.dropout)

    def forward(
        self,
        x: torch.Tensor,
        mask: Optional[torch.Tensor] = None,
        kv_cache: Optional[Tuple[torch.Tensor, torch.Tensor]] = None,
    ) -> Tuple[torch.Tensor, Optional[Tuple[torch.Tensor, torch.Tensor]]]:
        residual = x
        x = self.norm1(x)
        x, new_kv_cache = self.attn(x, mask, kv_cache)
        x = residual + x

        residual = x
        x = self.norm2(x)
        x = self.ffn(x)
        x = residual + x
        return x, new_kv_cache


class PDFMindModel(nn.Module):
    def __init__(self, config: PDFMindConfig):
        super().__init__()
        self.config = config

        self.tok_emb = nn.Embedding(config.vocab_size, config.d_model)
        self.drop = nn.Dropout(config.dropout)

        self.layers = nn.ModuleList([TransformerBlock(config) for _ in range(config.n_layers)])
        self.norm = RMSNorm(config.d_model, config.layer_norm_eps)

        self.lm_head = nn.Linear(config.d_model, config.vocab_size, bias=False)

        if config.tie_word_embeddings:
            self.lm_head.weight = self.tok_emb.weight

        self.apply(self._init_weights)

        for p in self.parameters():
            if p.dim() > 1:
                nn.init.normal_(p, mean=0.0, std=config.initializer_range)

    def _init_weights(self, module):
        if isinstance(module, nn.Linear):
            nn.init.normal_(module.weight, mean=0.0, std=self.config.initializer_range)
            if module.bias is not None:
                nn.init.zeros_(module.bias)
        elif isinstance(module, nn.Embedding):
            nn.init.normal_(module.weight, mean=0.0, std=self.config.initializer_range)

    def forward(
        self,
        input_ids: torch.Tensor,
        labels: Optional[torch.Tensor] = None,
        kv_caches: Optional[list] = None,
        use_cache: bool = False,
    ) -> Tuple[torch.Tensor, Optional[torch.Tensor], Optional[list]]:
        B, T = input_ids.shape
        assert T <= self.config.max_seq_len, f"Sequence length {T} exceeds max {self.config.max_seq_len}"

        x = self.drop(self.tok_emb(input_ids))

        if kv_caches is None:
            kv_caches = [None] * self.config.n_layers

        if T > 1:
            mask = torch.tril(torch.ones(T, T, device=input_ids.device, dtype=torch.bool))
            mask = mask.unsqueeze(0).unsqueeze(0)
        else:
            mask = None

        new_kv_caches = []
        for i, layer in enumerate(self.layers):
            x, new_cache = layer(x, mask, kv_caches[i])
            new_kv_caches.append(new_cache if use_cache else None)

        x = self.norm(x)
        logits = self.lm_head(x)

        loss = None
        if labels is not None:
            shift_logits = logits[:, :-1, :].contiguous()
            shift_labels = labels[:, 1:].contiguous()
            loss = F.cross_entropy(
                shift_logits.view(-1, self.config.vocab_size),
                shift_labels.view(-1),
                ignore_index=self.config.pad_token_id,
            )

        return logits, loss, new_kv_caches if use_cache else None


class PDFMindForCausalLM(nn.Module):
    def __init__(self, config: PDFMindConfig):
        super().__init__()
        self.config = config
        self.model = PDFMindModel(config)
        self.num_parameters = sum(p.numel() for p in self.parameters())
        self.num_trainable = sum(p.numel() for p in self.parameters() if p.requires_grad)

    def forward(
        self,
        input_ids: torch.Tensor,
        labels: Optional[torch.Tensor] = None,
        kv_caches: Optional[list] = None,
        use_cache: bool = False,
    ) -> Tuple[torch.Tensor, Optional[torch.Tensor], Optional[list]]:
        return self.model(input_ids, labels, kv_caches, use_cache)

    @torch.no_grad()
    def generate(
        self,
        input_ids: torch.Tensor,
        max_new_tokens: int = 256,
        temperature: float = 0.8,
        top_k: int = 50,
        top_p: float = 0.9,
        stop_tokens: Optional[list] = None,
    ) -> torch.Tensor:
        self.eval()
        kv_caches = None
        generated = input_ids.clone()

        for _ in range(max_new_tokens):
            idx_cond = generated if kv_caches is None else generated[:, -1:]
            logits, _, kv_caches = self(idx_cond, kv_caches=kv_caches, use_cache=True)
            logits = logits[:, -1, :] / max(temperature, 1e-8)

            if top_k > 0:
                v, _ = torch.topk(logits, min(top_k, logits.size(-1)))
                logits[logits < v[:, [-1]]] = float("-inf")

            if top_p < 1.0:
                sorted_logits, sorted_indices = torch.sort(logits, descending=True)
                cumulative_probs = torch.cumsum(F.softmax(sorted_logits, dim=-1), dim=-1)
                sorted_indices_to_remove = cumulative_probs > top_p
                sorted_indices_to_remove[:, 1:] = sorted_indices_to_remove[:, :-1].clone()
                sorted_indices_to_remove[:, 0] = 0
                indices_to_remove = sorted_indices_to_remove.scatter(1, sorted_indices, sorted_indices_to_remove)
                logits[indices_to_remove] = float("-inf")

            probs = F.softmax(logits, dim=-1)
            next_token = torch.multinomial(probs, num_samples=1)
            generated = torch.cat([generated, next_token], dim=1)

            if stop_tokens is not None:
                for stop_id in stop_tokens:
                    if (next_token == stop_id).all():
                        return generated

            if generated.shape[1] >= self.config.max_seq_len:
                break

        return generated

    def get_parameter_groups(self, lr: float, weight_decay: float) -> list:
        decay = []
        no_decay = []
        for name, param in self.named_parameters():
            if not param.requires_grad:
                continue
            if "norm" in name or "bias" in name:
                no_decay.append(param)
            else:
                decay.append(param)
        return [
            {"params": decay, "weight_decay": weight_decay, "lr": lr},
            {"params": no_decay, "weight_decay": 0.0, "lr": lr},
        ]

    def count_parameters(self) -> dict:
        total = sum(p.numel() for p in self.parameters())
        trainable = sum(p.numel() for p in self.parameters() if p.requires_grad)
        embedding = sum(p.numel() for n, p in self.named_parameters() if "tok_emb" in n)
        attention = sum(p.numel() for n, p in self.named_parameters() if "attn" in n)
        ffn = sum(p.numel() for n, p in self.named_parameters() if "ffn" in n)
        other = total - embedding - attention - ffn
        return {
            "total": total,
            "trainable": trainable,
            "embedding": embedding,
            "attention": attention,
            "ffn": ffn,
            "other": other,
            "total_m": f"{total / 1e6:.1f}M",
            "trainable_m": f"{trainable / 1e6:.1f}M",
        }

    def save(self, path: str):
        torch.save({
            "config": self.config.to_dict(),
            "model_state_dict": self.model.state_dict(),
        }, path)

    @classmethod
    def load(cls, path: str, device: str = "cpu") -> "PDFMindForCausalLM":
        checkpoint = torch.load(path, map_location=device, weights_only=False)
        config = PDFMindConfig.from_dict(checkpoint["config"])
        model = cls(config)
        model.load_state_dict(checkpoint["model_state_dict"])
        return model.to(device)


# Backwards-compatible alias for legacy imports that expect `PDFMind`.
PDFMind = PDFMindForCausalLM
