"""Thin client for the local Gemma model served by Ollama (HTTP on localhost only)."""
import json
import re
import subprocess
import time
import urllib.error
import urllib.request

from . import config


class ModelUnavailable(RuntimeError):
    pass


def _post(path, payload, stream=False):
    req = urllib.request.Request(
        config.OLLAMA_URL + path,
        data=json.dumps(payload).encode(),
        headers={"Content-Type": "application/json"},
    )
    try:
        return urllib.request.urlopen(req, timeout=config.REQUEST_TIMEOUT)
    except urllib.error.HTTPError as e:
        body = e.read().decode(errors="replace")
        if e.code == 404:
            raise ModelUnavailable(
                f"Model '{config.MODEL}' is not installed locally.\n"
                f"  Fix (while online): ollama pull {config.MODEL}"
            ) from None
        raise ModelUnavailable(f"Ollama returned HTTP {e.code}: {body}") from None
    except urllib.error.URLError:
        raise ModelUnavailable(
            f"Cannot reach the local Ollama server at {config.OLLAMA_URL}.\n"
            "  Fix: start it with `ollama serve` (or open the Ollama app), then retry."
        ) from None


def chat(messages, temperature=0.2, json_schema=None, on_token=None):
    """Send messages to local Gemma. Returns (text, stats).

    on_token: optional callback that receives streamed text as it is generated.
    json_schema: optional JSON schema; Ollama constrains the output to match it.
    """
    payload = {
        "model": config.MODEL,
        "messages": messages,
        "stream": on_token is not None,
        "think": False,
        "options": {"num_ctx": config.NUM_CTX, "temperature": temperature},
    }
    if json_schema is not None:
        payload["format"] = json_schema

    start = time.time()
    resp = _post("/api/chat", payload)
    text, final = "", {}
    if on_token is None:
        final = json.loads(resp.read())
        text = final["message"]["content"]
    else:
        for line in resp:
            chunk = json.loads(line)
            piece = chunk.get("message", {}).get("content", "")
            if piece:
                text += piece
                on_token(piece)
            if chunk.get("done"):
                final = chunk
    stats = {
        "wall_seconds": round(time.time() - start, 2),
        "load_seconds": round(final.get("load_duration", 0) / 1e9, 2),
        "prompt_tokens": final.get("prompt_eval_count"),
        "output_tokens": final.get("eval_count"),
    }
    return text, stats


def model_info():
    """Model identity for evidence records."""
    return {
        "model": config.MODEL,
        "runtime": ollama_version(),
        "execution": "local",
        "num_ctx": config.NUM_CTX,
    }


def ollama_version():
    try:
        out = subprocess.run(["ollama", "--version"], capture_output=True, text=True).stdout
        return "Ollama " + out.strip().split()[-1]
    except Exception:
        return "Ollama (version unknown)"


def memory_snapshot():
    """Memory used by the loaded model.

    phys_footprint (macOS `footprint`) of Ollama's llama-server process is the real number on
    Apple Silicon: it includes the Metal/GPU buffers in unified memory, which RSS leaves out.
    Ollama's own /api/ps size is recorded too, for comparison.
    """
    snap = {}
    try:
        with urllib.request.urlopen(config.OLLAMA_URL + "/api/ps", timeout=5) as r:
            for m in json.loads(r.read()).get("models", []):
                if m["name"] == config.MODEL:
                    snap["ollama_reported_gb"] = round(m["size"] / 1e9, 2)
    except Exception:
        pass
    try:
        pids = subprocess.run(["pgrep", "-f", "ollama/llama-server"], capture_output=True, text=True).stdout.split()
        total = peak = 0
        for pid in pids:
            out = subprocess.run(["footprint", "-p", pid], capture_output=True, text=True).stdout
            m = re.search(r"Footprint: ([\d.]+) (MB|GB)", out)
            k = re.search(r"phys_footprint_peak: ([\d.]+) (MB|GB)", out)
            to_gb = lambda v, u: float(v) / (1000 if u == "MB" else 1)
            if m:
                total += to_gb(*m.groups())
            if k:
                peak += to_gb(*k.groups())
        if pids:
            snap["model_process_footprint_gb"] = round(total, 2)
            snap["model_process_peak_gb"] = round(peak, 2)
    except Exception:
        pass
    return snap
