"""PDFMind 100M — ONNX Export.

Exports the trained model to ONNX format for deployment:
- FP32 ONNX (~200MB)
- INT8 quantized ONNX (~100MB) — primary deployment format
- Dynamic axes for variable sequence lengths
- Optimized graph with fused operations

Supports ONNX Runtime with DirectML (iGPU), CPU, and CUDA execution providers.
"""

import os
from typing import Optional, Tuple

import torch
import torch.nn as nn

from .config import PDFMindConfig
from .model import PDFMindForCausalLM


class ONNXExporter:
    def __init__(self, model: PDFMindForCausalLM, tokenizer=None):
        self.model = model
        self.tokenizer = tokenizer
        self.config = model.config

    def export_fp32(
        self, output_path: str, max_seq_len: Optional[int] = None,
    ) -> str:
        if max_seq_len is None:
            max_seq_len = self.config.max_seq_len

        self.model.eval()
        dummy_input = torch.zeros(1, min(128, max_seq_len), dtype=torch.long)

        class ExportWrapper(nn.Module):
            def __init__(self, model):
                super().__init__()
                self.model = model

            def forward(self, input_ids):
                logits, _, _ = self.model(input_ids, use_cache=False)
                return logits

        wrapper = ExportWrapper(self.model)

        os.makedirs(os.path.dirname(output_path) if os.path.dirname(output_path) else ".", exist_ok=True)

        torch.onnx.export(
            wrapper,
            dummy_input,
            output_path,
            input_names=["input_ids"],
            output_names=["logits"],
            dynamic_axes={
                "input_ids": {0: "batch_size", 1: "sequence_length"},
                "logits": {0: "batch_size", 1: "sequence_length"},
            },
            opset_version=14,
            do_constant_folding=True,
        )

        size_mb = os.path.getsize(output_path) / (1024 * 1024)
        print(f"FP32 ONNX exported: {output_path} ({size_mb:.1f} MB)")
        return output_path

    def export_int8(self, output_path: str, calibration_data: Optional[list] = None) -> str:
        try:
            import onnxruntime
            from onnxruntime.quantization import quantize_dynamic, QuantType
        except ImportError:
            print("Install onnxruntime: pip install onnxruntime")
            return ""

        fp32_path = output_path.replace("_int8", "_fp32")
        if not os.path.exists(fp32_path):
            self.export_fp32(fp32_path)

        quantize_dynamic(
            fp32_path,
            output_path,
            weight_type=QuantType.QInt8,
        )

        size_mb = os.path.getsize(output_path) / (1024 * 1024)
        print(f"INT8 ONNX exported: {output_path} ({size_mb:.1f} MB)")
        return output_path

    def export_all(self, output_dir: str) -> dict:
        os.makedirs(output_dir, exist_ok=True)
        results = {}

        fp32_path = os.path.join(output_dir, "pdfmind-100m-fp32.onnx")
        results["fp32"] = self.export_fp32(fp32_path)

        int8_path = os.path.join(output_dir, "pdfmind-100m-int8.onnx")
        results["int8"] = self.export_int8(int8_path)

        if self.tokenizer:
            self.tokenizer.save(os.path.join(output_dir, "tokenizer"))

        self.config.save(os.path.join(output_dir, "config.json"))

        print(f"\nAll exports complete in {output_dir}")
        return results

    @staticmethod
    def verify_onnx(onnx_path: str, test_input: Optional[torch.Tensor] = None) -> bool:
        try:
            import onnxruntime as ort
        except ImportError:
            print("Install onnxruntime: pip install onnxruntime")
            return False

        session = ort.InferenceSession(onnx_path)
        input_name = session.get_inputs()[0].name

        if test_input is None:
            test_input = torch.randint(0, 1000, (1, 64))

        outputs = session.run(None, {input_name: test_input.numpy()})
        print(f"ONNX verification passed. Output shape: {outputs[0].shape}")
        return True


def export_onnx(checkpoint_path: str, output_dir: str = "./exports/onnx"):
    """Export a checkpoint to ONNX format."""
    checkpoint = torch.load(checkpoint_path, map_location="cpu", weights_only=False)
    config = PDFMindConfig.from_dict(checkpoint.get("config", checkpoint.get("model_config", {})))
    model = PDFMindForCausalLM(config)

    state_dict = checkpoint.get("model_state_dict", checkpoint.get("state_dict", {}))
    model.load_state_dict(state_dict)

    exporter = ONNXExporter(model)
    return exporter.export_all(output_dir)


if __name__ == "__main__":
    import sys
    if len(sys.argv) > 1:
        export_onnx(sys.argv[1])
    else:
        print("Usage: python -m ai_model.export_onnx <checkpoint_path>")
