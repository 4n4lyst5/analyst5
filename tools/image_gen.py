#!/usr/bin/env python3
"""
Génération d'images via HuggingFace Inference API (FLUX.1-schnell).
Usage :
  python3 image_gen.py "un chat astronaute" [output_path]
  python3 image_gen.py "prompt" --reference photo.jpg
"""
import sys, os, argparse, time
from pathlib import Path

TOKEN_FILE = Path.home() / ".analyst5" / "hf_token"
DEFAULT_MODEL = "black-forest-labs/FLUX.1-schnell"
FALLBACK_MODEL = "stabilityai/stable-diffusion-xl-base-1.0"
HF_BASE_URL = "https://router.huggingface.co/hf-inference/models"


def load_token() -> str:
    if not TOKEN_FILE.exists():
        raise RuntimeError("Token HuggingFace manquant. Lance : echo 'hf_...' > ~/.analyst5/hf_token")
    return TOKEN_FILE.read_text().strip()


def generate(prompt: str, output: str = "/tmp/a5_output.png", model: str = DEFAULT_MODEL) -> str:
    import requests

    token = load_token()
    headers = {"Authorization": f"Bearer {token}"}
    payload = {"inputs": prompt, "parameters": {"num_inference_steps": 4}}

    url = f"{HF_BASE_URL}/{model}"

    for attempt in range(3):
        resp = requests.post(url, headers=headers, json=payload, timeout=120)
        if resp.status_code == 200 and resp.headers.get("content-type", "").startswith("image"):
            with open(output, "wb") as f:
                f.write(resp.content)
            return output
        elif resp.status_code == 503:
            wait = resp.json().get("estimated_time", 20)
            print(f"Modèle en chargement, attente {wait:.0f}s...", flush=True)
            time.sleep(min(wait, 30))
        else:
            # Essayer le modèle de fallback
            if model != FALLBACK_MODEL and attempt == 1:
                return generate(prompt, output, FALLBACK_MODEL)
            raise RuntimeError(f"Erreur HuggingFace {resp.status_code}: {resp.text[:200]}")

    raise RuntimeError("Modèle indisponible après 3 tentatives.")


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("prompt", help="Description de l'image à générer")
    parser.add_argument("output", nargs="?", default="/tmp/a5_output.png", help="Chemin de sortie")
    parser.add_argument("--model", default=DEFAULT_MODEL)
    args = parser.parse_args()

    print(f"Génération : {args.prompt[:60]}...", flush=True)
    path = generate(args.prompt, args.output, args.model)
    print(f"IMAGE_READY:{path}")


if __name__ == "__main__":
    main()
