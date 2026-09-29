"""Portable USB version: self-contained PDFMind for running without installation."""

import os
import sys
import json
import shutil
import hashlib
import logging
import platform
from dataclasses import dataclass, field
from typing import Optional

logger = logging.getLogger(__name__)


@dataclass
class PortableConfig:
    app_name: str = "PDFMind Portable"
    version: str = "2026.6"
    output_dir: str = "PDFMind_Portable"
    include_python: bool = True
    include_ai: bool = True
    include_cloud: bool = False
    include_cli: bool = True
    max_size_mb: int = 200
    auto_detect_arch: bool = True
    create_bat_launcher: bool = True
    create_ps1_launcher: bool = True
    create_sh_launcher: bool = True
    embed_settings: bool = True
    include_sample_files: bool = True
    compress: bool = True


class PortableBuilder:
    """Build a portable USB version of PDFMind that runs without installation."""

    def __init__(self, config: PortableConfig = None):
        self._config = config or PortableConfig()
        self._build_log: list[str] = []
        self._included_files: list[str] = []

    def build(self, output_dir: str = None) -> dict:
        output = output_dir or self._config.output_dir
        self._build_log = []
        self._included_files = []
        os.makedirs(output, exist_ok=True)
        self._create_directory_structure(output)
        self._create_launcher_scripts(output)
        self._create_config_files(output)
        self._log(f"Portable build created at: {output}")
        return {
            "output_dir": output,
            "files_included": len(self._included_files),
            "total_size_mb": self._estimate_size(),
            "platform": platform.system(),
            "architecture": platform.machine(),
            "build_log": self._build_log,
        }

    def _create_directory_structure(self, base_dir: str):
        dirs = ["bin", "lib", "plugins", "config", "data", "cache",
                "templates", "logs", "exports", "temp"]
        for d in dirs:
            path = os.path.join(base_dir, d)
            os.makedirs(path, exist_ok=True)
            self._log(f"Created directory: {d}/")

    def _create_launcher_scripts(self, base_dir: str):
        if self._config.create_bat_launcher:
            bat_content = f"""@echo off
title {self._config.app_name} v{self._config.version}
echo Starting {self._config.app_name}...
set PDFMIND_PORTABLE=1
set PDFMIND_HOME=%~dp0
set PATH=%~dp0bin;%~dp0lib;%PATH%
if exist "%~dp0bin\\python.exe" (
    "%~dp0bin\\python.exe" -m pdfmind %*
) else (
    python -m pdfmind %*
)
if errorlevel 1 (
    echo.
    echo Press any key to exit...
    pause >nul
)
"""
            bat_path = os.path.join(base_dir, f"{self._config.app_name.replace(' ', '_')}.bat")
            with open(bat_path, "w") as f:
                f.write(bat_content)
            self._included_files.append(bat_path)
            self._log("Created launcher: .bat")

        if self._config.create_ps1_launcher:
            ps1_content = f"""# {self._config.app_name} Portable Launcher
$ErrorActionPreference = "Stop"
$PSScriptRoot = Split-Path -Parent $MyInvocation.MyCommand.Path
$env:PDFMIND_PORTABLE = "1"
$env:PDFMIND_HOME = $PSScriptRoot
$env:PATH = "$PSScriptRoot\\bin;$PSScriptRoot\\lib;$env:PATH"
Write-Host "Starting {self._config.app_name} v{self._config.version}..." -ForegroundColor Cyan
try {
    & python -m pdfmind @args
} catch {{
    Write-Host "Error: $_" -ForegroundColor Red
    Read-Host "Press Enter to exit"
}}
"""
            ps1_path = os.path.join(base_dir, f"{self._config.app_name.replace(' ', '_')}.ps1")
            with open(ps1_path, "w") as f:
                f.write(ps1_content)
            self._included_files.append(ps1_path)
            self._log("Created launcher: .ps1")

        if self._config.create_sh_launcher:
            sh_content = f"""#!/bin/bash
echo "Starting {self._config.app_name} v{self._config.version}..."
SCRIPT_DIR="$(cd "$(dirname "$0")" && pwd)"
export PDFMIND_PORTABLE=1
export PDFMIND_HOME="$SCRIPT_DIR"
export PATH="$SCRIPT_DIR/bin:$SCRIPT_DIR/lib:$PATH"
python3 -m pdfmind "$@"
"""
            sh_path = os.path.join(base_dir, f"{self._config.app_name.replace(' ', '_')}.sh")
            with open(sh_path, "w") as f:
                f.write(sh_content)
            try:
                os.chmod(sh_path, 0o755)
            except Exception:
                pass
            self._included_files.append(sh_path)
            self._log("Created launcher: .sh")

    def _create_config_files(self, base_dir: str):
        config = {
            "portable": True,
            "version": self._config.version,
            "app_name": self._config.app_name,
            "data_dir": "data",
            "cache_dir": "cache",
            "log_dir": "logs",
            "temp_dir": "temp",
            "auto_save": True,
            "auto_save_interval": 300,
            "theme": "catppuccin_mocha",
            "language": "en",
            "startup_action": "last",
        }
        config_path = os.path.join(base_dir, "config", "settings.json")
        with open(config_path, "w") as f:
            json.dump(config, f, indent=2)
        self._included_files.append(config_path)
        self._log("Created config: settings.json")

        readme = f"""# {self._config.app_name} v{self._config.version}

## Quick Start
1. Run the launcher script for your platform:
   - Windows: Double-click `PDFMind_Portable.bat`
   - PowerShell: Run `./PDFMind_Portable.ps1`
   - Linux/Mac: Run `./PDFMind_Portable.sh`

## Directory Structure
- `bin/` - Application binaries
- `lib/` - Libraries and dependencies
- `config/` - Configuration files
- `data/` - User data (documents, recent files)
- `cache/` - Temporary cache files
- `plugins/` - Installed plugins
- `templates/` - Document templates
- `exports/` - Exported files
- `logs/` - Application logs

## Notes
- All user data is stored in the `data/` folder
- Settings are saved between sessions
- This version runs without installation
- Can be run from USB drives or network shares
"""
        readme_path = os.path.join(base_dir, "README.txt")
        with open(readme_path, "w") as f:
            f.write(readme)
        self._included_files.append(readme_path)

    def _estimate_size(self) -> float:
        if self._config.include_python:
            base_size = 60
        else:
            base_size = 20
        if self._config.include_ai:
            base_size += 80
        if self._config.include_cloud:
            base_size += 30
        return min(base_size, self._config.max_size_mb)

    def _log(self, message: str):
        self._build_log.append(message)
        logger.debug(f"Portable build: {message}")

    def get_file清单(self) -> list[str]:
        return self._included_files

    def get_size_estimate(self) -> dict:
        total_mb = self._estimate_size()
        return {
            "total_mb": round(total_mb, 1),
            "breakdown": {
                "core": 20 if not self._config.include_python else 60,
                "ai": 80 if self._config.include_ai else 0,
                "cloud": 30 if self._config.include_cloud else 0,
                "templates": 5,
                "docs": 2,
            },
            "fits_on_usb_128mb": total_mb <= 128,
            "fits_on_usb_256mb": total_mb <= 256,
        }

    def generate_usb_contents_list(self) -> dict:
        return {
            "root_files": [
                "PDFMind_Portable.bat",
                "PDFMind_Portable.ps1",
                "PDFMind_Portable.sh",
                "README.txt",
            ],
            "directories": ["bin/", "lib/", "config/", "data/", "cache/",
                            "plugins/", "templates/", "exports/", "logs/", "temp/"],
            "estimated_total_files": 500,
            "platform": platform.system(),
        }
