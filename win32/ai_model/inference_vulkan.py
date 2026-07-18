"""PDFMind 100M — Vulkan iGPU Inference.

Accelerated inference using llama.cpp with Vulkan backend for
integrated GPUs (Intel Iris Xe, AMD Radeon Vega, etc.).

Performance on integrated graphics:
| Chip            | Model     | Q4_K_M    | Speed       |
|-----------------|-----------|-----------|-------------|
| Intel Iris Xe   | 100M Q4   | ~55MB     | 300-500 t/s |
| AMD Radeon 780M | 100M Q4   | ~55MB     | 400-700 t/s |
| Intel UHD 620   | 100M Q4   | ~55MB     | 150-300 t/s |

Setup:
1. Build llama.cpp with Vulkan: cmake -DGGML_VULKAN=ON
2. Export model to GGUF Q4_K_M format
3. Run: llama-server -m model.gguf -ngl 99 --host 0.0.0.0 --port 8080
"""

import json
import os
import shutil
import subprocess
import time
from typing import Dict, List, Optional

import requests


class VulkanEngine:
    """Vulkan-accelerated inference via llama.cpp."""

    def __init__(
        self,
        gguf_path: str,
        llama_cpp_dir: Optional[str] = None,
        host: str = "127.0.0.1",
        port: int = 8080,
        n_gpu_layers: int = 99,
        n_ctx: int = 2048,
        n_threads: Optional[int] = None,
    ):
        self.gguf_path = gguf_path
        self.host = host
        self.port = port
        self.n_gpu_layers = n_gpu_layers
        self.n_ctx = n_ctx
        self.n_threads = n_threads
        self.process = None
        self.base_url = f"http://{host}:{port}"

        self.llama_cpp_dir = llama_cpp_dir or self._find_llama_cpp()
        self.server_path = self._find_server()

    def _find_llama_cpp(self) -> Optional[str]:
        candidates = [
            os.path.expanduser("~/llama.cpp"),
            "C:/llama.cpp",
            "D:/llama.cpp",
            "/usr/local/llama.cpp",
            "/opt/llama.cpp",
        ]
        for path in candidates:
            if os.path.exists(path):
                return path
        return None

    def _find_server(self) -> Optional[str]:
        if not self.llama_cpp_dir:
            return None
        build_dirs = ["build/bin", "build/Release", "build"]
        names = ["llama-server", "llama-server.exe", "server", "server.exe"]
        for bd in build_dirs:
            for name in names:
                path = os.path.join(self.llama_cpp_dir, bd, name)
                if os.path.exists(path):
                    return path
        return None

    def start(self, timeout: int = 30) -> bool:
        if not self.server_path:
            print("llama-server not found. Build llama.cpp with Vulkan support:")
            print("  git clone https://github.com/ggerganov/llama.cpp")
            print("  cd llama.cpp && mkdir build && cd build")
            print("  cmake .. -DGGML_VULKAN=ON -DCMAKE_BUILD_TYPE=Release")
            print("  cmake --build . --config Release -j")
            return False

        cmd = [
            self.server_path,
            "-m", self.gguf_path,
            "-ngl", str(self.n_gpu_layers),
            "-c", str(self.n_ctx),
            "--host", self.host,
            "--port", str(self.port),
            "-fa", "auto",
        ]

        if self.n_threads:
            cmd.extend(["-t", str(self.n_threads)])

        print(f"Starting llama-server: {' '.join(cmd)}")
        self.process = subprocess.Popen(
            cmd, stdout=subprocess.PIPE, stderr=subprocess.PIPE,
        )

        start_time = time.time()
        while time.time() - start_time < timeout:
            try:
                resp = requests.get(f"{self.base_url}/health", timeout=2)
                if resp.status_code == 200:
                    print(f"llama-server started on {self.base_url}")
                    return True
            except (requests.ConnectionError, requests.Timeout):
                pass
            time.sleep(0.5)

        print("Timeout waiting for llama-server to start")
        return False

    def stop(self):
        if self.process:
            self.process.terminate()
            self.process.wait(timeout=10)
            self.process = None
            print("llama-server stopped")

    def generate(
        self,
        prompt: str,
        max_tokens: int = 256,
        temperature: float = 0.7,
        top_k: int = 40,
        top_p: float = 0.9,
        stop: Optional[List[str]] = None,
    ) -> str:
        payload = {
            "prompt": prompt,
            "n_predict": max_tokens,
            "temperature": temperature,
            "top_k": top_k,
            "top_p": top_p,
            "stream": False,
        }
        if stop:
            payload["stop"] = stop

        try:
            resp = requests.post(f"{self.base_url}/completion", json=payload, timeout=120)
            resp.raise_for_status()
            return resp.json().get("content", "")
        except requests.RequestException as e:
            return f"[Error: {e}]"

    def chat(
        self,
        messages: List[Dict[str, str]],
        max_tokens: int = 256,
        temperature: float = 0.7,
    ) -> str:
        payload = {
            "messages": messages,
            "n_predict": max_tokens,
            "temperature": temperature,
            "stream": False,
        }

        try:
            resp = requests.post(f"{self.base_url}/v1/chat/completions", json=payload, timeout=120)
            resp.raise_for_status()
            return resp.json()["choices"][0]["message"]["content"]
        except requests.RequestException as e:
            return f"[Error: {e}]"

    def embedding(self, text: str) -> List[float]:
        try:
            resp = requests.post(
                f"{self.base_url}/embedding",
                json={"content": text},
                timeout=30,
            )
            resp.raise_for_status()
            return resp.json()["embedding"]
        except requests.RequestException:
            return []

    def health(self) -> Dict:
        try:
            resp = requests.get(f"{self.base_url}/health", timeout=5)
            return {"status": "ok", "status_code": resp.status_code}
        except requests.RequestException:
            return {"status": "error"}

    def get_server_info(self) -> Dict:
        try:
            resp = requests.get(f"{self.base_url}/props", timeout=5)
            return resp.json()
        except requests.RequestException:
            return {}

    def benchmark(self, prompt: str = "What is a PDF?", n_tokens: int = 100, n_runs: int = 3) -> Dict:
        times = []
        for _ in range(n_runs):
            start = time.perf_counter()
            self.generate(prompt, max_tokens=n_tokens, temperature=0.0)
            elapsed = time.perf_counter() - start
            times.append(elapsed)

        avg_time = sum(times) / len(times)
        return {
            "avg_time_s": round(avg_time, 3),
            "tokens_per_second": round(n_tokens / avg_time, 1),
            "n_tokens": n_tokens,
            "n_runs": n_runs,
            "backend": "vulkan",
            "server": self.base_url,
        }


class VulkanDetector:
    """Detects Vulkan-capable integrated GPUs."""

    @staticmethod
    def detect_gpus() -> List[Dict]:
        gpus = []
        try:
            result = subprocess.run(
                ["vulkaninfo", "--json"], capture_output=True, text=True, timeout=10,
            )
            if result.returncode == 0:
                data = json.loads(result.stdout)
                for device in data.get("devices", []):
                    gpus.append({
                        "name": device.get("deviceName", "Unknown"),
                        "vendor": device.get("vendorID", 0),
                        "type": device.get("deviceType", "unknown"),
                        "vulkan_version": device.get("apiVersion", "unknown"),
                    })
        except (FileNotFoundError, subprocess.TimeoutExpired, json.JSONDecodeError):
            pass
        return gpus

    @staticmethod
    def is_igpu() -> bool:
        gpus = VulkanDetector.detect_gpus()
        igpu_keywords = ["iris", "radeon", "vega", "uhd", "intel", "radeon graphics"]
        for gpu in gpus:
            name_lower = gpu["name"].lower()
            if any(kw in name_lower for kw in igpu_keywords):
                return True
        return False

    @staticmethod
    def recommend_config() -> Dict:
        gpus = VulkanDetector.detect_gpus()
        if not gpus:
            return {"n_gpu_layers": 0, "n_ctx": 1024, "note": "No Vulkan GPU detected"}

        gpu_name = gpus[0]["name"].lower()

        if "780m" in gpu_name or "radeon 7" in gpu_name:
            return {"n_gpu_layers": 99, "n_ctx": 2048, "note": "AMD Radeon 780M: full offload recommended"}
        elif "iris" in gpu_name or "xe" in gpu_name:
            return {"n_gpu_layers": 99, "n_ctx": 2048, "note": "Intel Iris Xe: full offload works"}
        elif "uhd" in gpu_name:
            return {"n_gpu_layers": 24, "n_ctx": 1024, "note": "Intel UHD: partial offload"}
        else:
            return {"n_gpu_layers": 99, "n_ctx": 2048, "note": "Unknown GPU: trying full offload"}
