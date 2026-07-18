"""PDFMind 100M — Deployment Script.

Automates the full deployment pipeline:
1. Build llama.cpp with Vulkan support
2. Convert model to GGUF Q4_K_M
3. Start llama-server with iGPU offload
4. Verify inference works
"""

import os
import platform
import shutil
import subprocess
import sys
import time


def build_llama_cpp(source_dir: str = None):
    print("Building llama.cpp with Vulkan support...")
    if source_dir is None:
        source_dir = os.path.expanduser("~/llama.cpp")

    if not os.path.exists(source_dir):
        print("Cloning llama.cpp...")
        subprocess.run(["git", "clone", "https://github.com/ggerganov/llama.cpp.git", source_dir], check=True)

    build_dir = os.path.join(source_dir, "build")
    os.makedirs(build_dir, exist_ok=True)

    system = platform.system()
    cmake_args = [
        "cmake", "..",
        "-DCMAKE_BUILD_TYPE=Release",
        "-DGGML_VULKAN=ON",
        "-DGGML_NATIVE=ON",
    ]

    subprocess.run(cmake_args, cwd=build_dir, check=True)

    n_jobs = os.cpu_count() or 4
    subprocess.run(
        ["cmake", "--build", ".", "--config", "Release", f"-j{n_jobs}"],
        cwd=build_dir, check=True,
    )

    print("llama.cpp built successfully!")


def convert_to_gguf(checkpoint_path: str, output_path: str = "./model.gguf"):
    print(f"Converting {checkpoint_path} to GGUF...")
    import torch
    from ..config import PDFMindConfig
    from ..model import PDFMindForCausalLM
    from ..export_gguf import GGUFExporter

    checkpoint = torch.load(checkpoint_path, map_location="cpu", weights_only=False)
    config = PDFMindConfig.from_dict(checkpoint.get("config", checkpoint.get("model_config", {})))
    model = PDFMindForCausalLM(config)
    model.load_state_dict(checkpoint.get("model_state_dict", checkpoint.get("state_dict", {})))

    exporter = GGUFExporter(model)
    return exporter.export(output_path, quantization="q4_k_m")


def start_server(
    gguf_path: str,
    host: str = "127.0.0.1",
    port: int = 8080,
    n_gpu_layers: int = 99,
    n_ctx: int = 2048,
):
    from ..inference_vulkan import VulkanEngine
    engine = VulkanEngine(
        gguf_path=gguf_path, host=host, port=port,
        n_gpu_layers=n_gpu_layers, n_ctx=n_ctx,
    )
    if engine.start():
        print(f"\nPDFMind AI server running at http://{host}:{port}")
        print("API endpoints:")
        print(f"  POST {engine.base_url}/completion    — Text completion")
        print(f"  POST {engine.base_url}/v1/chat/completions — Chat API")
        print(f"  GET  {engine.base_url}/health         — Health check")
        print("\nPress Ctrl+C to stop.")
        try:
            while True:
                time.sleep(1)
        except KeyboardInterrupt:
            engine.stop()
    return engine


def main():
    print("=" * 60)
    print("PDFMind 100M — Deployment")
    print("=" * 60)

    if len(sys.argv) < 2:
        print("\nUsage:")
        print("  python -m ai_model.scripts.deploy build     — Build llama.cpp")
        print("  python -m ai_model.scripts.deploy convert   — Convert to GGUF")
        print("  python -m ai_model.scripts.deploy serve     — Start server")
        print("  python -m ai_model.scripts.deploy full      — Full pipeline")
        return

    cmd = sys.argv[1]

    if cmd == "build":
        build_llama_cpp()
    elif cmd == "convert":
        checkpoint = sys.argv[2] if len(sys.argv) > 2 else "./checkpoints/pdfmind-100m/final/checkpoint.pt"
        convert_to_gguf(checkpoint)
    elif cmd == "serve":
        gguf_path = sys.argv[2] if len(sys.argv) > 2 else "./model.gguf"
        start_server(gguf_path)
    elif cmd == "full":
        checkpoint = sys.argv[2] if len(sys.argv) > 2 else "./checkpoints/pdfmind-100m/final/checkpoint.pt"
        build_llama_cpp()
        gguf_path = convert_to_gguf(checkpoint)
        start_server(gguf_path)
    else:
        print(f"Unknown command: {cmd}")


if __name__ == "__main__":
    main()
