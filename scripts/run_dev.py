#!/usr/bin/env python3
"""FreshGuard Local Multi-Service Runner

Orchestrates all FreshGuard subsystems for local development, demos, and end-to-end testing:
  1. Python Verification Service (FastAPI / Uvicorn on http://127.0.0.1:8000)
  2. Frontend React / Vite Sandbox (http://localhost:3000)
  3. Bifrost Proxy with FreshGuard Go Plugin (optional if binary present)
"""

import argparse
import os
import shutil
import signal
import subprocess
import sys
import time
from pathlib import Path

ROOT_DIR = Path(__file__).resolve().parent.parent
VERIFICATION_SERVICE_DIR = ROOT_DIR / "verification-service"
FRONTEND_DIR = ROOT_DIR / "frontend"
EXAMPLES_DIR = ROOT_DIR / "examples"


def check_prerequisites():
    print("=" * 60)
    print("🛡️  FreshGuard System Pre-Flight Check")
    print("=" * 60)

    # 1. Python check
    py_ver = sys.version.split()[0]
    print(f"  [✓] Python Runtime: {py_ver}")

    # 2. Node check
    node_cmd = shutil.which("node")
    if node_cmd:
        node_ver = subprocess.run([node_cmd, "-v"], capture_output=True, text=True).stdout.strip()
        print(f"  [✓] Node.js Runtime: {node_ver} ({node_cmd})")
    else:
        print("  [!] Node.js not detected in PATH; frontend dev server may not start.")

    # 3. Go check
    go_cmd = shutil.which("go")
    if not go_cmd:
        # Check standard local paths
        candidate = Path("C:/Users/admin/go-sdk/bin/go.exe")
        if candidate.exists():
            go_cmd = str(candidate)
    if go_cmd:
        go_ver = subprocess.run([go_cmd, "version"], capture_output=True, text=True).stdout.strip()
        print(f"  [✓] Go Runtime: {go_ver}")
    else:
        print("  [!] Go runtime not in PATH.")

    # 4. Bifrost binary check
    bifrost_binary = None
    default_bf = Path("C:/Users/admin/AppData/Local/bifrost/v2.5.1/bin/bifrost-http.exe-0")
    if default_bf.exists():
        bifrost_binary = default_bf
    elif shutil.which("bifrost-http"):
        bifrost_binary = Path(shutil.which("bifrost-http"))

    if bifrost_binary:
        print(f"  [✓] Bifrost Gateway: {bifrost_binary}")
    else:
        print("  [i] Bifrost Gateway: binary not found; running Python + Frontend services.")

    print("=" * 60 + "\n")
    return bifrost_binary


def main():
    parser = argparse.ArgumentParser(description="Start FreshGuard development stack.")
    parser.add_argument("--no-frontend", action="store_true", help="Do not start frontend dev server")
    parser.add_argument("--with-bifrost", action="store_true", help="Start Bifrost gateway if binary exists")
    parser.add_argument("--port", type=int, default=8000, help="Verification service port")
    args = parser.parse_args()

    bifrost_bin = check_prerequisites()

    processes = []

    def cleanup(sig=None, frame=None):
        print("\n🛑 Shutting down FreshGuard services...")
        for p, name in processes:
            print(f"  Terminating {name} (PID: {p.pid})...")
            try:
                p.terminate()
                p.wait(timeout=3)
            except Exception:
                try:
                    p.kill()
                except Exception:
                    pass
        print("✓ All FreshGuard services stopped.")
        sys.exit(0)

    signal.signal(signal.SIGINT, cleanup)
    signal.signal(signal.SIGTERM, cleanup)

    # 1. Start Python Verification Service
    print(f"🚀 Starting Python Verification Service on http://127.0.0.1:{args.port}...")
    env = os.environ.copy()
    env["PYTHONPATH"] = str(VERIFICATION_SERVICE_DIR)
    py_proc = subprocess.Popen(
        [sys.executable, "-m", "uvicorn", "app.main:app", "--host", "127.0.0.1", "--port", str(args.port)],
        cwd=str(VERIFICATION_SERVICE_DIR),
        env=env,
    )
    processes.append((py_proc, "Python Verification Service"))

    # 2. Start Frontend Dev Server
    if not args.no_frontend:
        npm_cmd = shutil.which("npm.cmd") or shutil.which("npm")
        if npm_cmd and (FRONTEND_DIR / "package.json").exists():
            print("🎨 Starting Frontend Dev Server on http://localhost:3000...")
            frontend_proc = subprocess.Popen(
                [npm_cmd, "run", "dev"],
                cwd=str(FRONTEND_DIR),
            )
            processes.append((frontend_proc, "Frontend Dev Server"))

    # 3. Start Bifrost if requested and binary exists
    if args.with_bifrost and bifrost_bin and bifrost_bin.exists():
        cfg_path = EXAMPLES_DIR / "bifrost.yaml"
        print(f"🌐 Starting Bifrost Gateway with config {cfg_path}...")
        bf_proc = subprocess.Popen(
            [str(bifrost_bin), "--config", str(cfg_path)],
            cwd=str(ROOT_DIR),
        )
        processes.append((bf_proc, "Bifrost Gateway"))

    print("\n✨ FreshGuard is running!")
    print("   • Verification API:  http://127.0.0.1:8000")
    print("   • API Documentation: http://127.0.0.1:8000/docs")
    print("   • Verification UI:   http://localhost:3000")
    print("\nPress Ctrl+C to terminate all services.\n")

    try:
        while True:
            time.sleep(1)
            # Check if any process exited unexpectedly
            for p, name in processes:
                ret = p.poll()
                if ret is not None:
                    print(f"⚠️  {name} exited with code {ret}")
    except KeyboardInterrupt:
        cleanup()


if __name__ == "__main__":
    main()

