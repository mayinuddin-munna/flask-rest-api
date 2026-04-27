# RunPod ComfyUI Z-Image-Turbo Serverless Endpoint

This folder contains a complete RunPod serverless deployment for the `Comfy-Org/z_image_turbo` model using ComfyUI.

## Files

- `handler.py` - Python RunPod serverless handler that sends ComfyUI workflows to the local ComfyUI internal API and returns generated images.
- `Dockerfile` - CUDA-compatible Docker image using `runpod/base:1.0.3-cuda1290-ubuntu2204`.
- `requirements.txt` - Python dependency list.
- `comfyui_start.sh` - Startup script to launch ComfyUI and then start the handler.

## Build the Docker image

```bash
cd runpod-comfyui-endpoint
docker build -t your-docker-username/comfyui-z-image-turbo:latest .
```

## Push the Docker image

```bash
docker push your-docker-username/comfyui-z-image-turbo:latest
```

## Create a RunPod template

Use the RunPod dashboard or CLI to create a serverless template with the following recommended settings:

- GPU: choose a card with at least 24 GB VRAM (for example A5000, A6000, or equivalent)
- Container disk: 50 GB
- Volume disk: 100 GB
- Container image: `your-docker-username/comfyui-z-image-turbo:latest`
- Environment variables:
  - `OUTPUT_S3_BUCKET` (optional): name of the S3 bucket to upload generated images
  - `AWS_ACCESS_KEY_ID` and `AWS_SECRET_ACCESS_KEY` (optional): AWS credentials for S3 uploads
  - `AWS_DEFAULT_REGION` or `AWS_REGION` (optional): AWS region for signed S3 URLs
  - `S3_ENDPOINT_URL` (optional): S3-compatible endpoint for custom storage providers
  - `COMFYUI_API_URL` (optional): internal ComfyUI endpoint, defaults to `http://127.0.0.1:8188`

## Create the RunPod serverless endpoint

1. In the RunPod dashboard, create a new endpoint using the template you created.
2. Select the image and volume settings.
3. Start the endpoint.

## Example request payload

```json
{
  "workflow": {
    "nodes": [
      {
        "id": "prompt_1",
        "type": "TextPrompt",
        "args": {
          "text": "A futuristic city skyline at sunset, cinematic lighting"
        }
      },
      {
        "id": "z_turbo_1",
        "type": "ZImageTurbo",
        "args": {
          "model": "Comfy-Org/z_image_turbo",
          "width": 768,
          "height": 768,
          "steps": 28,
          "guidance_scale": 7.5
        }
      }
    ],
    "connections": [
      {
        "from": "prompt_1",
        "output": "text",
        "to": "z_turbo_1",
        "input": "prompt"
      }
    ]
  }
}
```

> Note: The workflow JSON example is minimal and assumes the custom Z-Image-Turbo node is available in ComfyUI. Adjust node names and fields to match your custom node implementation.

## Test the endpoint with `curl`

### Base64 result output

```bash
curl -X POST https://<your-endpoint-url> \
  -H "Content-Type: application/json" \
  -d '{
    "workflow": {"nodes": [{"id": "prompt_1", "type": "TextPrompt", "args": {"text": "A dramatic glowing forest at dawn"}}, {"id": "z_turbo_1", "type": "ZImageTurbo", "args": {"model": "Comfy-Org/z_image_turbo", "width": 768, "height": 768, "steps": 20, "guidance_scale": 7.0}}], "connections": [{"from": "prompt_1", "output": "text", "to": "z_turbo_1", "input": "prompt"}]}
  }'
```

### S3 upload output

If `OUTPUT_S3_BUCKET` and AWS credentials are configured, the handler will upload generated images to S3 and return URLs.

```bash
curl -X POST https://<your-endpoint-url> \
  -H "Content-Type: application/json" \
  -d '{"workflow": {"nodes": [{"id": "prompt_1", "type": "TextPrompt", "args": {"text": "A photorealistic canyon landscape"}}, {"id": "z_turbo_1", "type": "ZImageTurbo", "args": {"model": "Comfy-Org/z_image_turbo", "width": 768, "height": 768, "steps": 24, "guidance_scale": 8.0}}], "connections": [{"from": "prompt_1", "output": "text", "to": "z_turbo_1", "input": "prompt"}]}}
```

## Notes

- The handler posts workflows to ComfyUI's internal `/prompt` endpoint and polls `/history/<prompt_id>` until completion.
- If the custom node produces PNG output, the handler will return valid `data:image/png;base64,...` strings or upload PNG files to S3.
- Tune the `timeout` field in requests if workflows require more than the default 180 seconds.
# RunPod-serverless
