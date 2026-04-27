import base64
import os
import re
import time
import uuid
from typing import Any, Dict, List, Optional

import boto3
import requests
from botocore.exceptions import BotoCoreError, ClientError
from runpod.serverless import start

COMFYUI_API_URL = os.getenv("COMFYUI_API_URL", "http://127.0.0.1:8188")
DEFAULT_TIMEOUT = int(os.getenv("DEFAULT_TIMEOUT", "180"))
MODEL_NAME = os.getenv("MODEL_NAME", "Comfy-Org/z_image_turbo")
S3_BUCKET = os.getenv("OUTPUT_S3_BUCKET")
S3_REGION = os.getenv("AWS_DEFAULT_REGION") or os.getenv("AWS_REGION")
S3_ENDPOINT_URL = os.getenv("S3_ENDPOINT_URL")
S3_PREFIX = os.getenv("OUTPUT_S3_PREFIX", "runpod-output")

BASE64_IMAGE_PREFIX_RE = re.compile(r"^data:image/(png|jpeg|jpg);base64,", re.I)
RAW_BASE64_RE = re.compile(r"^[A-Za-z0-9+/\n\r=]+${}", re.I)


def _has_aws_credentials() -> bool:
    return bool(os.getenv("AWS_ACCESS_KEY_ID") and os.getenv("AWS_SECRET_ACCESS_KEY"))


def _get_s3_client():
    if not _has_aws_credentials():
        return None

    client_args = {}
    if S3_REGION:
        client_args["region_name"] = S3_REGION
    if S3_ENDPOINT_URL:
        client_args["endpoint_url"] = S3_ENDPOINT_URL

    return boto3.client("s3", **client_args)


def _decode_base64_image(value: str) -> Optional[bytes]:
    if not isinstance(value, str):
        return None

    value = value.strip()
    if not value:
        return None

    match = BASE64_IMAGE_PREFIX_RE.match(value)
    if match:
        value = value[match.end():]

    try:
        decoded = base64.b64decode(value, validate=True)
    except Exception:
        return None

    if decoded.startswith(b"\x89PNG\r\n\x1a\n") or decoded.startswith(b"\xff\xd8\xff"):
        return decoded

    return None


def _traverse_for_images(payload: Any) -> List[bytes]:
    if isinstance(payload, dict):
        results: List[bytes] = []
        for value in payload.values():
            results.extend(_traverse_for_images(value))
        return results

    if isinstance(payload, list):
        results: List[bytes] = []
        for item in payload:
            results.extend(_traverse_for_images(item))
        return results

    if isinstance(payload, str):
        image_bytes = _decode_base64_image(payload)
        return [image_bytes] if image_bytes else []

    return []


def _post_workflow(workflow: Any, images: Optional[List[str]]) -> str:
    payload = {"workflow": workflow}
    if images:
        payload["images"] = images

    response = requests.post(f"{COMFYUI_API_URL}/prompt", json=payload, timeout=15)
    response.raise_for_status()

    body = response.json()
    prompt_id = body.get("id") or body.get("prompt_id") or body.get("uuid")
    if not prompt_id:
        raise ValueError("ComfyUI /prompt response did not return a prompt id")
    return str(prompt_id)


def _poll_workflow(prompt_id: str, timeout: int) -> Dict[str, Any]:
    deadline = time.time() + timeout
    while time.time() < deadline:
        response = requests.get(f"{COMFYUI_API_URL}/history/{prompt_id}", timeout=15)
        if response.status_code == 404:
            raise ValueError(f"Prompt history not found for id {prompt_id}")
        response.raise_for_status()

        history = response.json()
        status = str(history.get("status", "")).lower()
        done_flag = history.get("done") or history.get("finished") or history.get("success")

        if done_flag or status in {"completed", "finished", "success", "done"}:
            return history

        time.sleep(2)

    raise TimeoutError(f"ComfyUI workflow did not complete within {timeout} seconds")


def _build_image_response(images: List[bytes]) -> Dict[str, Any]:
    if _has_aws_credentials() and S3_BUCKET:
        s3 = _get_s3_client()
        if not s3:
            raise RuntimeError("Unable to initialize S3 client with the provided AWS credentials")

        uploaded: List[Dict[str, str]] = []
        for index, image_bytes in enumerate(images, start=1):
            key = f"{S3_PREFIX}/{int(time.time())}-{uuid.uuid4().hex[:8]}-{index}.png"
            content_type = "image/png"
            try:
                s3.put_object(Bucket=S3_BUCKET, Key=key, Body=image_bytes, ContentType=content_type)
            except (BotoCoreError, ClientError) as exc:
                raise RuntimeError(f"Failed to upload output image to S3: {exc}")

            if S3_ENDPOINT_URL:
                url = f"{S3_ENDPOINT_URL.rstrip('/')}/{S3_BUCKET}/{key}"
            elif S3_REGION:
                url = f"https://{S3_BUCKET}.s3.{S3_REGION}.amazonaws.com/{key}"
            else:
                url = f"https://{S3_BUCKET}.s3.amazonaws.com/{key}"

            uploaded.append({"url": url})

        return {"images": uploaded}

    encoded_images = [
        f"data:image/png;base64,{base64.b64encode(image_bytes).decode('utf-8')}"
        for image_bytes in images
    ]
    return {"images": encoded_images}


def handler(event: Dict[str, Any], context: Any) -> Dict[str, Any]:
    workflow = event.get("workflow")
    if workflow is None:
        return {"error": "Missing required field: workflow"}

    images = event.get("images")
    if images is not None and not isinstance(images, list):
        return {"error": "Optional field 'images' must be a list of base64-encoded strings"}

    timeout = int(event.get("timeout", DEFAULT_TIMEOUT))
    if timeout <= 0:
        timeout = DEFAULT_TIMEOUT

    try:
        prompt_id = _post_workflow(workflow, images)
        history = _poll_workflow(prompt_id, timeout)
        image_bytes = _traverse_for_images(history)
        if not image_bytes:
            raise ValueError("No generated images were found in ComfyUI workflow output")

        response_payload = _build_image_response(image_bytes)
        return {
            "prompt_id": prompt_id,
            "model": MODEL_NAME,
            "workflow": workflow,
            "result": response_payload,
        }

    except TimeoutError as exc:
        return {"error": str(exc), "timeout": timeout}
    except requests.RequestException as exc:
        return {"error": f"ComfyUI API request failed: {exc}"}
    except Exception as exc:
        return {"error": str(exc)}


if __name__ == "__main__":
    start({"handler": handler})
