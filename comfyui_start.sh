#!/bin/bash
set -e

cd /workspace/ComfyUI

if [ -f custom_nodes/ComfyUI-Z-Image-Turbo/requirements.txt ]; then
  python -m pip install -r custom_nodes/ComfyUI-Z-Image-Turbo/requirements.txt
fi

python main.py --listen 0.0.0.0 --port 8188 &
COMFYUI_PID=$!
echo "Started ComfyUI with PID ${COMFYUI_PID}"

python - <<'PY'
import sys
import time
import requests

base_url = "http://127.0.0.1:8188"
endpoints = ["/status", "/health", "/"]
ready_deadline = time.time() + 60

while time.time() < ready_deadline:
    for path in endpoints:
        try:
            response = requests.get(base_url + path, timeout=5)
            if response.ok:
                print(f"ComfyUI is ready at {base_url}{path}")
                sys.exit(0)
        except Exception:
            pass
    time.sleep(2)

print("ComfyUI did not become ready in 60 seconds", file=sys.stderr)
sys.exit(1)
PY

cd /workspace
exec python /workspace/handler.py
