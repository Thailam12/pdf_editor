"""PDFMind 100M — Full Training Pipeline.

Complete pipeline from data preparation to model deployment:
1. Train BPE tokenizer on corpus
2. Pre-train base model on general text
3. QLoRA fine-tune on PDF tasks (or distill from teacher)
4. Export to ONNX INT8 and GGUF Q4
5. Run benchmarks

Usage:
    python -m ai_model.scripts.train_full --all
    python -m ai_model.scripts.train_full --stage tokenizer
    python -m ai_model.scripts.train_full --stage pretrain
    python -m ai_model.scripts.train_full --stage finetune
    python -m ai_model.scripts.train_full --stage export
    python -m ai_model.scripts.train_full --stage benchmark
"""

import argparse
import os
import sys
import time

import torch


def train_tokenizer(data_dir: str = "./data", output_dir: str = "./tokenizer"):
    print("\n" + "=" * 60)
    print("STAGE 1: Training BPE Tokenizer")
    print("=" * 60)

    from ..tokenizer import PDFMindTokenizer
    tokenizer = PDFMindTokenizer(vocab_size=32000)

    texts = []
    for fname in os.listdir(data_dir):
        if fname.endswith(".jsonl"):
            import json
            with open(os.path.join(data_dir, fname), encoding="utf-8") as f:
                for line in f:
                    item = json.loads(line)
                    if "text" in item:
                        texts.append(item["text"])
                    if "instruction" in item:
                        texts.append(item["instruction"])
                    if "output" in item:
                        texts.append(item["output"])

    print(f"Training tokenizer on {len(texts)} text samples...")
    tokenizer.train(texts)
    tokenizer.save(output_dir)
    print(f"Tokenizer saved to {output_dir} (vocab_size={tokenizer.vocab_size})")
    return tokenizer


def pretrain_model(config_path=None, data_dir="./data", output_dir="./checkpoints/pretrain"):
    print("\n" + "=" * 60)
    print("STAGE 2: Pre-training Base Model")
    print("=" * 60)

    from ..config import PDFMindConfig
    from ..model import PDFMindForCausalLM
    from ..tokenizer import PDFMindTokenizer
    from ..dataset import TextDataset, PDFDatasetLoader
    from ..train_pretrain import PreTrainer

    config = PDFMindConfig() if not config_path else PDFMindConfig.load(config_path)
    model = PDFMindForCausalLM(config)
    params = model.count_parameters()
    print(f"Model: {params['total_m']} parameters")

    tokenizer = PDFMindTokenizer.load("./tokenizer") if os.path.exists("./tokenizer") else None
    if tokenizer is None:
        print("No tokenizer found. Run tokenizer stage first.")
        return None

    data_files = [os.path.join(data_dir, f) for f in os.listdir(data_dir) if f.endswith(".jsonl")]
    if not data_files:
        print("No data files found. Run data preparation first.")
        return None

    texts = PDFDatasetLoader.create_pretraining_data(data_files)
    print(f"Loaded {len(texts)} training samples")
    dataset = TextDataset(texts, tokenizer, max_length=config.max_seq_len)

    train_size = int(len(dataset) * 0.95)
    eval_size = len(dataset) - train_size
    train_ds, eval_ds = torch.utils.data.random_split(dataset, [train_size, eval_size])

    train_loader = torch.utils.data.DataLoader(train_ds, batch_size=4, shuffle=True, drop_last=True)
    eval_loader = torch.utils.data.DataLoader(eval_ds, batch_size=4, shuffle=False)

    device = "cuda" if torch.cuda.is_available() else "cpu"
    trainer = PreTrainer(
        model=model, train_loader=train_loader, eval_loader=eval_loader,
        output_dir=output_dir, device=device,
    )
    trainer.train(num_epochs=5)
    return os.path.join(output_dir, "final", "checkpoint.pt")


def finetune_qlora(checkpoint_path: str, data_dir="./data", output_dir="./checkpoints/qlora"):
    print("\n" + "=" * 60)
    print("STAGE 3: QLoRA Fine-tuning")
    print("=" * 60)

    from ..config import PDFMindConfig
    from ..model import PDFMindForCausalLM
    from ..tokenizer import PDFMindTokenizer
    from ..dataset import InstructionDataset, PDFDatasetLoader
    from ..train_qlora import apply_lora, QLoRATrainer

    if checkpoint_path and os.path.exists(checkpoint_path):
        checkpoint = torch.load(checkpoint_path, map_location="cpu", weights_only=False)
        config = PDFMindConfig.from_dict(checkpoint.get("config", checkpoint.get("model_config", {})))
        model = PDFMindForCausalLM(config)
        model.load_state_dict(checkpoint.get("model_state_dict", checkpoint.get("state_dict", {})))
    else:
        model = PDFMindForCausalLM(PDFMindConfig())

    model = apply_lora(model, rank=16, alpha=32.0, dropout=0.05)

    tokenizer = PDFMindTokenizer.load("./tokenizer") if os.path.exists("./tokenizer") else None
    if tokenizer is None:
        print("No tokenizer found.")
        return None

    instruction_file = os.path.join(data_dir, "instructions.jsonl")
    if not os.path.exists(instruction_file):
        print("No instruction data found. Run data preparation first.")
        return None

    data = PDFDatasetLoader.load_dataset(instruction_file)
    print(f"Loaded {len(data)} instruction samples")
    dataset = InstructionDataset(data, tokenizer, max_length=2048)

    train_size = int(len(dataset) * 0.95)
    eval_size = len(dataset) - train_size
    train_ds, eval_ds = torch.utils.data.random_split(dataset, [train_size, eval_size])

    train_loader = torch.utils.data.DataLoader(train_ds, batch_size=4, shuffle=True, drop_last=True)
    eval_loader = torch.utils.data.DataLoader(eval_ds, batch_size=4, shuffle=False)

    device = "cuda" if torch.cuda.is_available() else "cpu"
    trainer = QLoRATrainer(
        model=model, train_loader=train_loader, eval_loader=eval_loader,
        output_dir=output_dir, device=device,
    )
    trainer.train(num_epochs=3)
    return os.path.join(output_dir, "lora_adapters.pt")


def export_models(checkpoint_path: str, output_dir: str = "./exports"):
    print("\n" + "=" * 60)
    print("STAGE 4: Model Export")
    print("=" * 60)

    from ..config import PDFMindConfig
    from ..model import PDFMindForCausalLM
    from ..tokenizer import PDFMindTokenizer
    from ..export_onnx import ONNXExporter
    from ..export_gguf import GGUFExporter

    checkpoint = torch.load(checkpoint_path, map_location="cpu", weights_only=False)
    config = PDFMindConfig.from_dict(checkpoint.get("config", checkpoint.get("model_config", {})))
    model = PDFMindForCausalLM(config)
    model.load_state_dict(checkpoint.get("model_state_dict", checkpoint.get("state_dict", {})))

    tokenizer = PDFMindTokenizer.load("./tokenizer") if os.path.exists("./tokenizer") else None

    print("\nExporting ONNX...")
    onnx_exporter = ONNXExporter(model, tokenizer)
    onnx_exporter.export_all(os.path.join(output_dir, "onnx"))

    print("\nExporting GGUF...")
    gguf_exporter = GGUFExporter(model, tokenizer)
    gguf_exporter.export(os.path.join(output_dir, "gguf", "pdfmind-100m-q4_k_m.gguf"), quantization="q4_k_m")

    print(f"\nAll models exported to {output_dir}")


def run_benchmarks(model_path: str = None):
    print("\n" + "=" * 60)
    print("STAGE 5: Benchmarks")
    print("=" * 60)

    from ..model import PDFMindForCausalLM
    from ..tokenizer import PDFMindTokenizer
    from ..benchmarks.evaluate import BenchmarkSuite

    tokenizer = PDFMindTokenizer.load("./tokenizer") if os.path.exists("./tokenizer") else None

    if model_path and os.path.exists(model_path):
        model = PDFMindForCausalLM.load(model_path)
    else:
        from ..config import PDFMindConfig
        model = PDFMindForCausalLM(PDFMindConfig())

    suite = BenchmarkSuite(model=model, tokenizer=tokenizer)
    return suite.run_all(output_path="./benchmarks/results.json")


def main():
    parser = argparse.ArgumentParser(description="PDFMind 100M Training Pipeline")
    parser.add_argument("--stage", choices=["tokenizer", "pretrain", "finetune", "export", "benchmark", "all"])
    parser.add_argument("--data-dir", default="./data")
    parser.add_argument("--output-dir", default="./checkpoints/pdfmind-100m")
    parser.add_argument("--checkpoint", default=None)
    parser.add_argument("--all", action="store_true")
    args = parser.parse_args()

    stage = args.stage or ("all" if args.all else "all")
    start = time.time()

    if stage in ("tokenizer", "all"):
        train_tokenizer(args.data_dir)

    checkpoint = args.checkpoint

    if stage in ("pretrain", "all"):
        checkpoint = pretrain_model(data_dir=args.data_dir)

    if stage in ("finetune", "all"):
        checkpoint = finetune_qlora(checkpoint, data_dir=args.data_dir, output_dir=args.output_dir)

    if stage in ("export", "all") and checkpoint:
        export_models(checkpoint)

    if stage in ("benchmark", "all"):
        run_benchmarks(checkpoint)

    elapsed = time.time() - start
    print(f"\nTotal time: {elapsed / 60:.1f} minutes")


if __name__ == "__main__":
    main()
