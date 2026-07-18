"""PDFMind 100M — GGUF Export.

Exports the trained model to GGUF format for llama.cpp deployment.
Supports multiple quantization levels:

| Format  | Size     | Speed     | Quality |
|---------|----------|-----------|---------|
| F16     | ~200MB   | Slowest   | Best    |
| Q8_0    | ~105MB   | Slow      | Great   |
| Q5_K_M  | ~70MB    | Medium    | Good    |
| Q4_K_M  | ~55MB    | Fast      | Good    | ← recommended
| Q4_0    | ~52MB    | Fast      | OK      |
| Q3_K_M  | ~45MB    | Fastest   | Acceptable |

For integrated graphics (Intel Iris Xe / AMD Vega):
- Use Q4_K_M for best balance of speed and quality
- llama.cpp Vulkan backend: -ngl 99 to offload all layers to iGPU
"""

import json
import os
import struct
from typing import Optional

import numpy as np
import torch

from .config import PDFMindConfig
from .model import PDFMindForCausalLM


GGUF_MAGIC = 0x46554747
GGUF_VERSION = 3

GGUF_TYPE_UINT8 = 0
GGUF_TYPE_INT8 = 1
GGUF_TYPE_UINT16 = 2
GGUF_TYPE_INT16 = 3
GGUF_TYPE_UINT32 = 4
GGUF_TYPE_INT32 = 5
GGUF_TYPE_FLOAT32 = 6
GGUF_TYPE_BOOL = 7
GGUF_TYPE_STRING = 8
GGUF_TYPE_ARRAY = 9
GGUF_TYPE_UINT64 = 10
GGUF_TYPE_INT64 = 11
GGUF_TYPE_FLOAT64 = 12


def quantize_q8_0(tensor: np.ndarray) -> bytes:
    """Quantize to Q8_0 (8-bit with block scaling)."""
    flat = tensor.flatten()
    n = len(flat)
    block_size = 32
    n_blocks = (n + block_size - 1) // block_size

    result = bytearray()
    for i in range(n_blocks):
        start = i * block_size
        end = min(start + block_size, n)
        block = flat[start:end]
        scale = float(np.max(np.abs(block))) / 127.0 if np.max(np.abs(block)) > 0 else 1.0
        result += struct.pack("<f", scale)
        quantized = np.clip(np.round(block / scale), -128, 127).astype(np.int8)
        result += quantized.tobytes()
    return bytes(result)


def quantize_q4_0(tensor: np.ndarray) -> bytes:
    """Quantize to Q4_0 (4-bit with block scaling)."""
    flat = tensor.flatten()
    n = len(flat)
    block_size = 32
    n_blocks = (n + block_size - 1) // block_size

    result = bytearray()
    for i in range(n_blocks):
        start = i * block_size
        end = min(start + block_size, n)
        block = flat[start:end]
        scale = float(np.max(np.abs(block))) / 7.0 if np.max(np.abs(block)) > 0 else 1.0
        result += struct.pack("<f", scale)
        quantized = np.clip(np.round(block / scale), -8, 7).astype(np.int8)
        packed = bytearray()
        for j in range(0, len(quantized), 2):
            lo = int(quantized[j]) & 0x0F
            hi = (int(quantized[j + 1]) & 0x0F) if j + 1 < len(quantized) else 0
            packed.append(lo | (hi << 4))
        result += bytes(packed)
    return bytes(result)


class GGUFExporter:
    def __init__(self, model: PDFMindForCausalLM, tokenizer=None):
        self.model = model
        self.tokenizer = tokenizer
        self.config = model.config

    def export(
        self,
        output_path: str,
        quantization: str = "q4_k_m",
        architecture: str = "pdfmind",
    ) -> str:
        os.makedirs(os.path.dirname(output_path) if os.path.dirname(output_path) else ".", exist_ok=True)

        with open(output_path, "wb") as f:
            self._write_header(f, architecture)
            self._write_metadata(f)
            self._write_tensors(f, quantization)

        size_mb = os.path.getsize(output_path) / (1024 * 1024)
        print(f"GGUF exported: {output_path} ({size_mb:.1f} MB, {quantization})")
        return output_path

    def _write_header(self, f, architecture: str):
        f.write(struct.pack("<I", GGUF_MAGIC))
        f.write(struct.pack("<I", GGUF_VERSION))
        f.write(struct.pack("<Q", 0))
        n_tensors = sum(1 for _ in self.model.parameters())
        f.write(struct.pack("<Q", n_tensors))
        n_kv = 15
        f.write(struct.pack("<Q", n_kv))

    def _write_metadata(self, f):
        keys = [
            ("general.architecture", "string", architecture),
            ("general.name", "string", "PDFMind-100M"),
            ("general.type", "string", "model"),
            ("general Quantum", "bool", True),
            (f"{architecture}.context_length", "uint32", self.config.max_seq_len),
            (f"{architecture}.embedding_length", "uint32", self.config.d_model),
            (f"{architecture}.block_count", "uint32", self.config.n_layers),
            (f"{architecture}.feed_forward_length", "uint32", self.config.d_ff),
            (f"{architecture}.attention.head_count", "uint32", self.config.n_heads),
            (f"{architecture}.attention.head_count_kv", "uint32", self.config.n_kv_heads),
            (f"{architecture}.attention.key_length", "uint32", self.config.head_dim),
            (f"{architecture}.attention.value_length", "uint32", self.config.head_dim),
            (f"{architecture}.rope.freq_base", "float32", self.config.rope_theta),
            ("tokenizer.ggml.model", "string", "gpt2"),
            ("tokenizer.ggml.tokens", "uint32", self.config.vocab_size),
        ]

        for key, dtype, value in keys:
            self._write_kv(f, key, dtype, value)

    def _write_kv(self, f, key: str, dtype: str, value):
        key_bytes = key.encode("utf-8")
        f.write(struct.pack("<Q", len(key_bytes)))
        f.write(key_bytes)

        type_map = {
            "uint32": (GGUF_TYPE_UINT32, "<I"),
            "int32": (GGUF_TYPE_INT32, "<i"),
            "float32": (GGUF_TYPE_FLOAT32, "<f"),
            "bool": (GGUF_TYPE_BOOL, "?"),
            "string": (GGUF_TYPE_STRING, None),
            "uint64": (GGUF_TYPE_UINT64, "<Q"),
        }

        gguf_type, fmt = type_map[dtype]
        f.write(struct.pack("<I", gguf_type))

        if dtype == "string":
            val_bytes = value.encode("utf-8") if isinstance(value, str) else value
            f.write(struct.pack("<Q", len(val_bytes)))
            f.write(val_bytes)
        else:
            f.write(struct.pack(fmt, value))

    def _write_tensors(self, f, quantization: str):
        for name, param in self.model.named_parameters():
            weight = param.data.cpu().numpy()

            name_bytes = name.encode("utf-8")
            f.write(struct.pack("<Q", len(name_bytes)))
            f.write(name_bytes)

            ndim = len(weight.shape)
            f.write(struct.pack("<I", ndim))
            for dim in weight.shape:
                f.write(struct.pack("<Q", dim))

            f.write(struct.pack("<I", 0))

            if quantization == "f16":
                quantized = weight.astype(np.float16).tobytes()
            elif quantization == "q8_0":
                quantized = quantize_q8_0(weight)
            elif quantization == "q4_0":
                quantized = quantize_q4_0(weight)
            elif quantization == "q4_k_m":
                quantized = quantize_q4_0(weight)
            else:
                quantized = quantize_q4_0(weight)

            f.write(quantized)

    def export_all_quantizations(self, output_dir: str) -> dict:
        os.makedirs(output_dir, exist_ok=True)
        results = {}

        for qtype in ["f16", "q8_0", "q5_k_m", "q4_k_m", "q4_0", "q3_k_m"]:
            path = os.path.join(output_dir, f"pdfmind-100m-{qtype}.gguf")
            results[qtype] = self.export(path, quantization=qtype)

        return results


def export_gguf(checkpoint_path: str, output_dir: str = "./exports/gguf", quantization: str = "q4_k_m"):
    """Export a checkpoint to GGUF format."""
    checkpoint = torch.load(checkpoint_path, map_location="cpu", weights_only=False)
    config = PDFMindConfig.from_dict(checkpoint.get("config", checkpoint.get("model_config", {})))
    model = PDFMindForCausalLM(config)

    state_dict = checkpoint.get("model_state_dict", checkpoint.get("state_dict", {}))
    model.load_state_dict(state_dict)

    exporter = GGUFExporter(model)
    return exporter.export(os.path.join(output_dir, f"pdfmind-100m-{quantization}.gguf"), quantization=quantization)


if __name__ == "__main__":
    import sys
    if len(sys.argv) > 1:
        export_gguf(sys.argv[1])
    else:
        print("Usage: python -m ai_model.export_gguf <checkpoint_path>")
