#!/usr/bin/env python3
"""
Generate wide scrolling space backgrounds for IN THE BLACK.
Uses ComfyUI with pixel art LoRA for consistent style.
"""

import json
import urllib.request
import time
import os
import shutil
import random

COMFY_URL = "http://127.0.0.1:8188"
OUTPUT_DIR = "/mnt/storage/Projects/shield-pong/assets/backgrounds"
COMFY_OUTPUT = os.path.expanduser("~/ComfyUI/output")

MODEL = "animagine-xl-3.1.safetensors"
LORA = "pixel-art-xl-v1.1.safetensors"
LORA_WEIGHT = 1.0

NEGATIVE = "blurry, photorealistic, 3d render, photograph, watermark, text, signature, low quality, deformed, noise, bright, planets close-up, busy, cluttered"

# Wide panoramic backgrounds — dark, subtle, game-friendly
BACKGROUNDS = [
    ("bg_nebula_purple", "pixel art deep space background, dark void with distant purple nebula clouds, scattered tiny stars, very dark, subtle purple blue tint, retro game aesthetic, seamless tileable"),
    ("bg_stars_blue", "pixel art deep space background, dark void, many tiny distant stars, faint blue cosmic dust wisps, very dark, minimal, retro game aesthetic, seamless tileable"),
    ("bg_dust_teal", "pixel art deep space background, dark void, subtle teal green cosmic dust streaks, scattered dim stars, very dark atmospheric, retro game aesthetic, seamless tileable"),
    ("bg_galaxy_deep", "pixel art deep space background, very distant spiral galaxy, dark void, tiny scattered stars, deep purple black void, retro game aesthetic, seamless tileable"),
    ("bg_void_red", "pixel art deep space background, dark void, faint red distant nebula, scattered dim stars, dark atmospheric, crimson tint, retro game aesthetic, seamless tileable"),
]


def make_workflow(prompt_text, negative, width, height, seed=None, steps=28, cfg=7.0, filename_prefix="bg"):
    if seed is None:
        seed = random.randint(0, 2**32 - 1)

    return {
        "1": {
            "class_type": "CheckpointLoaderSimple",
            "inputs": {"ckpt_name": MODEL}
        },
        "2": {
            "class_type": "LoraLoader",
            "inputs": {
                "model": ["1", 0],
                "clip": ["1", 1],
                "lora_name": LORA,
                "strength_model": LORA_WEIGHT,
                "strength_clip": LORA_WEIGHT,
            }
        },
        "3": {
            "class_type": "CLIPTextEncode",
            "inputs": {"text": prompt_text, "clip": ["2", 1]}
        },
        "4": {
            "class_type": "CLIPTextEncode",
            "inputs": {"text": negative, "clip": ["2", 1]}
        },
        "5": {
            "class_type": "EmptyLatentImage",
            "inputs": {"width": width, "height": height, "batch_size": 1}
        },
        "6": {
            "class_type": "KSampler",
            "inputs": {
                "model": ["2", 0],
                "positive": ["3", 0],
                "negative": ["4", 0],
                "latent_image": ["5", 0],
                "seed": seed,
                "steps": steps,
                "cfg": cfg,
                "sampler_name": "euler_ancestral",
                "scheduler": "karras",
                "denoise": 1.0,
            }
        },
        "7": {
            "class_type": "VAEDecode",
            "inputs": {"samples": ["6", 0], "vae": ["1", 2]}
        },
        "8": {
            "class_type": "SaveImage",
            "inputs": {"images": ["7", 0], "filename_prefix": filename_prefix}
        },
    }


def queue_prompt(workflow):
    data = json.dumps({"prompt": workflow}).encode("utf-8")
    req = urllib.request.Request(f"{COMFY_URL}/prompt", data=data, headers={"Content-Type": "application/json"})
    try:
        resp = urllib.request.urlopen(req)
        return json.loads(resp.read()).get("prompt_id")
    except Exception as e:
        print(f"  ERROR: {e}")
        return None


def wait_for_completion(prompt_id, timeout=300):
    start = time.time()
    while time.time() - start < timeout:
        try:
            resp = urllib.request.urlopen(f"{COMFY_URL}/history/{prompt_id}")
            history = json.loads(resp.read())
            if prompt_id in history:
                return history[prompt_id]
        except:
            pass
        time.sleep(2)
    print(f"  TIMEOUT: {prompt_id}")
    return None


def collect_images(history, dest_dir, label):
    if not history or "outputs" not in history:
        return []
    os.makedirs(dest_dir, exist_ok=True)
    collected = []
    for node_id, node_out in history["outputs"].items():
        if "images" in node_out:
            for img in node_out["images"]:
                src = os.path.join(COMFY_OUTPUT, img.get("subfolder", ""), img["filename"])
                dst = os.path.join(dest_dir, f"{label}.png")
                if os.path.exists(src):
                    shutil.copy2(src, dst)
                    collected.append(dst)
                    print(f"  -> {dst}")
    return collected


def main():
    print("=== IN THE BLACK — Background Generation ===")
    print(f"Generating {len(BACKGROUNDS)} wide scrolling backgrounds\n")

    jobs = []
    for name, prompt in BACKGROUNDS:
        prefix = f"itb_{name}"
        print(f"[QUEUE] {name} (1920x512)")
        wf = make_workflow(prompt, NEGATIVE, 1920, 512, filename_prefix=prefix)
        pid = queue_prompt(wf)
        if pid:
            jobs.append((pid, name, prefix))
            print(f"  queued: {pid}")
        time.sleep(0.3)

    print(f"\n=== Waiting for {len(jobs)} jobs ===\n")

    for pid, name, prefix in jobs:
        print(f"[WAIT] {name}...")
        history = wait_for_completion(pid)
        collect_images(history, OUTPUT_DIR, prefix)

    print("\n=== Done! ===")
    if os.path.exists(OUTPUT_DIR):
        bg_files = [f for f in os.listdir(OUTPUT_DIR) if f.startswith("itb_bg_")]
        print(f"backgrounds/: {len(bg_files)} files")
        for f in sorted(bg_files):
            print(f"  {f}")


if __name__ == "__main__":
    main()
