#!/usr/bin/env python3
"""ATLAS Prototype 1 Launcher Script.

Launches the FastAPI backend server and interactive web dashboard
with automatic virtual environment detection, friendly startup banners,
and helpful engineering guidance.
"""

import os
import platform
import subprocess
import sys
from pathlib import Path


def get_prototype_dir() -> Path:
    """Return the absolute path to prototype-1 directory."""
    return Path(__file__).resolve().parent


def get_venv_python(base_dir: Path) -> Path:
    """Detect the virtual environment Python interpreter path."""
    if platform.system() == "Windows":
        return base_dir / ".venv" / "Scripts" / "python.exe"
    return base_dir / ".venv" / "bin" / "python"


def ensure_venv_execution(base_dir: Path) -> None:
    """Ensure that this script is running inside the dedicated .venv."""
    venv_python = get_venv_python(base_dir)

    if not venv_python.exists():
        print(f"[!] Warning: Virtual environment python not found at: {venv_python}")
        print("    Proceeding with current python interpreter...")
        return

    venv_dir = (base_dir / ".venv").resolve()
    current_prefix = Path(sys.prefix).resolve()
    if current_prefix == venv_dir:
        return

    try:
        print(f"[*] Activating virtual environment: {venv_python}")
        # Re-execute with .venv python
        result = subprocess.run([str(venv_python), str(Path(__file__).resolve()), *sys.argv[1:]])
        sys.exit(result.returncode)
    except Exception as err:
        print(f"[!] Note on venv activation: {err}")


def print_startup_banner(host: str, port: int) -> None:
    """Display the ATLAS syndicate startup banner and usage guide."""
    if hasattr(sys.stdout, "reconfigure"):
        try:
            sys.stdout.reconfigure(encoding="utf-8", errors="replace")
        except Exception:
            pass

    url = f"http://{host}:{port}"
    banner = f"""
================================================================================
   ___ _____ _        _   ____  
  / _ \\_   _| |      / \\ / ___| 
 / /_\\ \\| | | |     / _ \\\\___ \\ 
/ /_ \\ \\| | | |___ / ___ \\ ___) |
\\_/   \\_\\|_| |_____/_/   \\_\\____/ 
A Triaged Learning Agent Syndicate  |  Prototype 1.0
================================================================================

  * Web Dashboard:          {url}
  * Interactive API Docs:   {url}/docs
  * Redoc Specification:    {url}/redoc

  Core Subsystems Active:
    - Ingestion Gateway:    Pydantic V2 Schemas & Validation
    - Triage Supervisor:    Task Classification & Domain Routing
    - Worker Domain:        Isolated Scratchpad (Maintenance & R&D)
    - Context Isolation:    GlobalState vs LocalState Boundary
    - Memory Engine:        VectorMemoryStore (Semantic Cosine Search)
    - Telemetry Layer:      Fine-grained Spans, Latency & Token Accounting
    - Self-Improvement:     Offline Meta-Improver & Prompt Mutation Loop

  Controls:
    - Open your browser to {url} to access the interactive dashboard.
    - Press Ctrl + C to stop the server.
================================================================================
"""
    print(banner)


def main() -> None:
    base_dir = get_prototype_dir()
    ensure_venv_execution(base_dir)

    # Ensure prototype directory is on sys.path for backend imports
    if str(base_dir) not in sys.path:
        sys.path.insert(0, str(base_dir))

    host = "127.0.0.1"
    port = 8000

    print_startup_banner(host, port)

    try:
        import uvicorn
    except ImportError:
        print("[!] Error: 'uvicorn' is not installed in the active environment.")
        print(f"    Please install requirements using: {get_venv_python(base_dir)} -m pip install -r requirements.txt")
        sys.exit(1)

    try:
        uvicorn.run(
            "backend.app:app",
            host=host,
            port=port,
            reload=True,
            app_dir=str(base_dir),
            log_level="info",
        )
    except KeyboardInterrupt:
        print("\n[*] ATLAS Prototype 1 server shutdown cleanly. Goodbye!")


if __name__ == "__main__":
    main()
