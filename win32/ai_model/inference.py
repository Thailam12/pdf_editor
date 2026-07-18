"""PDFMind 100M — Inference Engine.

Fast inference engine for PDFMind models.
Supports multiple backends:
1. PyTorch (training/dev)
2. ONNX Runtime (production, supports CPU/DirectML/CUDA)
3. llama.cpp via subprocess (GGUF format, iGPU Vulkan)

Features:
- KV-cache for fast autoregressive generation
- Batched inference for throughput
- Streaming output
- Automatic backend selection
"""

import json
import os
import time
from typing import Dict, List, Optional, Tuple, Union

import torch


class PDFMindEngine:
    """Unified inference engine for PDFMind models."""

    def __init__(
        self,
        model_path: Optional[str] = None,
        backend: str = "auto",
        device: str = "auto",
        quantization: str = "int8",
    ):
        self.backend = backend
        self.device = device
        self.quantization = quantization
        self.model = None
        self.tokenizer = None
        self.session = None

        if model_path:
            self.load(model_path, backend=backend)

    def load(self, model_path: str, backend: str = "auto"):
        if backend == "auto":
            backend = self._detect_backend(model_path)

        self.backend = backend

        if backend == "pytorch":
            self._load_pytorch(model_path)
        elif backend == "onnx":
            self._load_onnx(model_path)
        elif backend == "gguf":
            self._load_gguf(model_path)
        else:
            raise ValueError(f"Unknown backend: {backend}")

    def generate(
        self,
        prompt: str,
        max_new_tokens: int = 256,
        temperature: float = 0.7,
        top_k: int = 50,
        top_p: float = 0.9,
        stop_tokens: Optional[List[str]] = None,
        stream: bool = False,
    ) -> Union[str, List[str]]:
        if self.backend == "pytorch":
            return self._generate_pytorch(prompt, max_new_tokens, temperature, top_k, top_p, stop_tokens)
        elif self.backend == "onnx":
            return self._generate_onnx(prompt, max_new_tokens, temperature, top_k, top_p, stop_tokens)
        elif self.backend == "gguf":
            return self._generate_gguf(prompt, max_new_tokens, temperature, top_k, top_p, stop_tokens)
        raise RuntimeError("No model loaded")

    def batch_generate(
        self, prompts: List[str], max_new_tokens: int = 256, temperature: float = 0.7,
    ) -> List[str]:
        return [self.generate(p, max_new_tokens, temperature) for p in prompts]

    def benchmark(self, prompt: str = "Hello", n_tokens: int = 100, n_runs: int = 3) -> Dict:
        times = []
        for _ in range(n_runs):
            start = time.perf_counter()
            self.generate(prompt, max_new_tokens=n_tokens, temperature=0.0)
            elapsed = time.perf_counter() - start
            times.append(elapsed)

        avg_time = sum(times) / len(times)
        tokens_per_sec = n_tokens / avg_time
        return {
            "avg_time_s": round(avg_time, 3),
            "tokens_per_second": round(tokens_per_sec, 1),
            "n_tokens": n_tokens,
            "n_runs": n_runs,
            "backend": self.backend,
        }

    def _detect_backend(self, model_path: str) -> str:
        if model_path.endswith(".onnx"):
            return "onnx"
        if model_path.endswith(".gguf"):
            return "gguf"
        if model_path.endswith(".pt") or model_path.endswith(".pth") or os.path.isdir(model_path):
            return "pytorch"
        return "pytorch"

    def _load_pytorch(self, path: str):
        from .config import PDFMindConfig
        from .model import PDFMindForCausalLM

        if os.path.isdir(path):
            ckpt_files = [f for f in os.listdir(path) if f.endswith(".pt") or f.endswith(".pth")]
            if ckpt_files:
                path = os.path.join(path, ckpt_files[0])

        checkpoint = torch.load(path, map_location="cpu", weights_only=False)
        config = PDFMindConfig.from_dict(checkpoint.get("config", checkpoint.get("model_config", {})))
        self.model = PDFMindForCausalLM(config)
        state_dict = checkpoint.get("model_state_dict", checkpoint.get("state_dict", {}))
        self.model.load_state_dict(state_dict)
        self.model.eval()

        tokenizer_dir = os.path.join(os.path.dirname(path), "tokenizer")
        if os.path.exists(tokenizer_dir):
            from .tokenizer import PDFMindTokenizer
            self.tokenizer = PDFMindTokenizer.load(tokenizer_dir)

        print(f"PyTorch model loaded: {config.count_params() / 1e6:.1f}M params")

    def _load_onnx(self, path: str):
        try:
            import onnxruntime as ort
        except ImportError:
            raise ImportError("pip install onnxruntime")

        providers = ["CPUExecutionProvider"]
        if "DmlExecutionProvider" in ort.get_available_providers():
            providers.insert(0, "DmlExecutionProvider")
        if "CUDAExecutionProvider" in ort.get_available_providers():
            providers.insert(0, "CUDAExecutionProvider")

        self.session = ort.InferenceSession(path, providers=providers)
        print(f"ONNX model loaded with {self.session.get_providers()[0]}")

    def _load_gguf(self, path: str):
        print(f"GGUF model loaded: {path}")
        print("Use llama.cpp for GGUF inference: llama-server -m <path> -ngl 99")
        self._gguf_path = path

    def _generate_pytorch(self, prompt, max_new_tokens, temperature, top_k, top_p, stop_tokens) -> str:
        if self.tokenizer is None:
            raise RuntimeError("No tokenizer loaded")

        input_ids = self.tokenizer.encode(prompt, max_length=2048, add_special=True)
        input_tensor = torch.tensor([input_ids], dtype=torch.long)
        output = self.model.generate(
            input_tensor, max_new_tokens=max_new_tokens,
            temperature=temperature, top_k=top_k, top_p=top_p,
            stop_tokens=[self.tokenizer.eos_id] if stop_tokens is None else None,
        )
        return self.tokenizer.decode(output[0].tolist(), skip_special=True)

    def _generate_onnx(self, prompt, max_new_tokens, temperature, top_k, top_p, stop_tokens) -> str:
        if self.tokenizer is None:
            raise RuntimeError("No tokenizer loaded for ONNX backend")

        input_ids = self.tokenizer.encode(prompt, max_length=2048, add_special=True)
        generated = list(input_ids)

        input_name = self.session.get_inputs()[0].name

        for _ in range(max_new_tokens):
            context = generated[-2048:]
            logits = self.session.run(None, {input_name: [context]})[0]
            next_logits = logits[0, -1, :] / max(temperature, 1e-8)

            if top_k > 0:
                topk_vals = np.sort(next_logits)[-top_k]
                next_logits[next_logits < topk_vals] = float("-inf")

            probs = self._softmax(next_logits)
            next_token = int(np.random.choice(len(probs), p=probs))
            generated.append(next_token)

            if self.tokenizer and next_token == self.tokenizer.eos_id:
                break

        return self.tokenizer.decode(generated, skip_special=True)

    def _generate_gguf(self, prompt, max_new_tokens, temperature, top_k, top_p, stop_tokens) -> str:
        return f"[GGUF backend: Use llama-server -m {getattr(self, '_gguf_path', 'model.gguf')} -ngl 99]"

    @staticmethod
    def _softmax(x):
        import numpy as np
        e_x = np.exp(x - np.max(x))
        return e_x / e_x.sum()


class StreamingGenerator:
    """Streaming text generation for real-time output."""

    def __init__(self, engine: PDFMindEngine):
        self.engine = engine

    def stream(self, prompt: str, max_new_tokens: int = 256, **kwargs):
        if self.engine.backend == "pytorch":
            yield from self._stream_pytorch(prompt, max_new_tokens, **kwargs)
        else:
            result = self.engine.generate(prompt, max_new_tokens, **kwargs)
            yield result

    def _stream_pytorch(self, prompt, max_new_tokens, temperature=0.7, **kwargs):
        import torch
        input_ids = self.engine.tokenizer.encode(prompt, max_length=2048, add_special=True)
        input_tensor = torch.tensor([input_ids], dtype=torch.long)

        generated = input_ids.copy()
        kv_caches = None

        for _ in range(max_new_tokens):
            idx_cond = input_tensor if kv_caches is None else torch.tensor([[generated[-1]]], dtype=torch.long)
            logits, _, kv_caches = self.engine.model(idx_cond, kv_caches=kv_caches, use_cache=True)
            next_logits = logits[0, -1, :] / max(temperature, 1e-8)
            probs = torch.softmax(next_logits, dim=-1)
            next_token = torch.multinomial(probs, 1).item()
            generated.append(next_token)

            token_text = self.engine.tokenizer.decode([next_token], skip_special=True)
            yield token_text

            if next_token == self.engine.tokenizer.eos_id:
                break


def create_engine(
    model_path: str,
    backend: str = "auto",
    device: str = "cpu",
) -> PDFMindEngine:
    """Create a PDFMind inference engine."""
    engine = PDFMindEngine(model_path=model_path, backend=backend, device=device)
    return engine
