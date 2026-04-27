FROM runpod/base:1.0.3-cuda1290-ubuntu2204

ENV PYTHONUNBUFFERED=1
WORKDIR /workspace

RUN apt-get update && apt-get install -y --no-install-recommends \
    git \
    ffmpeg \
    libgl1-mesa-glx \
    libglib2.0-0 \
 && rm -rf /var/lib/apt/lists/*

COPY requirements.txt /workspace/
RUN python -m pip install --upgrade pip setuptools wheel && \
    python -m pip install -r requirements.txt

COPY comfyui_start.sh /workspace/
COPY handler.py /workspace/

RUN git clone https://github.com/comfyanonymous/ComfyUI.git /workspace/ComfyUI
RUN mkdir -p /workspace/ComfyUI/custom_nodes && \
    git clone https://github.com/Comfy-Org/ComfyUI-Z-Image-Turbo.git /workspace/ComfyUI/custom_nodes/ComfyUI-Z-Image-Turbo || true

WORKDIR /workspace/ComfyUI
RUN if [ -f requirements.txt ]; then python -m pip install -r requirements.txt || true; fi
WORKDIR /workspace
RUN chmod +x comfyui_start.sh

CMD ["./comfyui_start.sh"]
