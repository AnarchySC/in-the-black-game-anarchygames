#!/usr/bin/env python3
"""
IN THE BLACK — V2 Asset Generator
Uses Pixel Art XL LoRA for clean game sprites.
"""

import json
import urllib.request
import time
import os
import shutil

COMFY_URL = "http://127.0.0.1:8188"
OUTPUT_DIR = "/mnt/storage/Projects/shield-pong/assets"
COMFY_OUTPUT = os.path.expanduser("~/ComfyUI/output")

# Best combo: animagine + pixel art LoRA
MODEL = "animagine-xl-3.1.safetensors"
LORA = "pixel-art-xl-v1.1.safetensors"
LORA_WEIGHT = 1.0

def make_workflow_with_lora(prompt_text, negative, width=512, height=512, seed=None, steps=28, cfg=7.0, filename_prefix="asset"):
    import random
    if seed is None:
        seed = random.randint(0, 2**32 - 1)

    return {
        "1": {  # CheckpointLoaderSimple
            "class_type": "CheckpointLoaderSimple",
            "inputs": { "ckpt_name": MODEL }
        },
        "2": {  # LoraLoader
            "class_type": "LoraLoader",
            "inputs": {
                "model": ["1", 0],
                "clip": ["1", 1],
                "lora_name": LORA,
                "strength_model": LORA_WEIGHT,
                "strength_clip": LORA_WEIGHT,
            }
        },
        "3": {  # CLIP positive
            "class_type": "CLIPTextEncode",
            "inputs": {
                "text": prompt_text,
                "clip": ["2", 1],
            }
        },
        "4": {  # CLIP negative
            "class_type": "CLIPTextEncode",
            "inputs": {
                "text": negative,
                "clip": ["2", 1],
            }
        },
        "5": {  # EmptyLatentImage
            "class_type": "EmptyLatentImage",
            "inputs": { "width": width, "height": height, "batch_size": 1 }
        },
        "6": {  # KSampler
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
        "7": {  # VAEDecode
            "class_type": "VAEDecode",
            "inputs": {
                "samples": ["6", 0],
                "vae": ["1", 2],
            }
        },
        "8": {  # SaveImage
            "class_type": "SaveImage",
            "inputs": {
                "images": ["7", 0],
                "filename_prefix": filename_prefix,
            }
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


def wait_for_completion(prompt_id, timeout=180):
    start = time.time()
    while time.time() - start < timeout:
        try:
            resp = urllib.request.urlopen(f"{COMFY_URL}/history/{prompt_id}")
            history = json.loads(resp.read())
            if prompt_id in history:
                return history[prompt_id]
        except:
            pass
        time.sleep(1.5)
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


NEGATIVE = "blurry, photorealistic, 3d render, photograph, watermark, text, signature, low quality, deformed, noise, multiple views, collage, border, frame"

# Ship tiers — cleaner prompts focused on single isolated sprites
SHIPS = [
    ("ship_t0", "small gray spaceship, simple basic design, blue cockpit light, side view facing right, single sprite, isolated on solid black background"),
    ("ship_t1", "sleek scout spaceship, blue accent lines, single engine glow, side view facing right, single sprite, isolated on solid black background"),
    ("ship_t2", "fast interceptor spaceship, cyan highlights, angular swept wings, side view facing right, single sprite, isolated on solid black background"),
    ("ship_t3", "aggressive viper spaceship, teal and yellow markings, side cannons, sharp nose, side view facing right, single sprite, isolated on solid black background"),
    ("ship_t4", "dark blue stealth spaceship, bright cyan edge lights, swept wings, side view facing right, single sprite, isolated on solid black background"),
    ("ship_t5", "purple energy spaceship, glowing purple lines, ornate triple engines, side view facing right, single sprite, isolated on solid black background"),
    ("ship_t6", "red and magenta heavy warship, armored plating, imposing design, side view facing right, single sprite, isolated on solid black background"),
    ("ship_t7", "pink and white crystalline spaceship, energy wings, glowing shield, side view facing right, single sprite, isolated on solid black background"),
    ("ship_t8", "purple aurora warship, massive golden wings, divine glow, side view facing right, single sprite, isolated on solid black background"),
    ("ship_t9", "legendary golden spaceship, radiant cosmic energy, ornate ultimate design, side view facing right, single sprite, isolated on solid black background"),
]

OTHER = [
    ("shield_orb", "glowing energy sphere, translucent force field orb, shifting colors, cyan green purple, sparkle effects, isolated on solid black background", "shield", 512, 512),
    ("bullet_p1", "blue laser bolt, horizontal energy projectile, cyan plasma, isolated on solid black background", "bullets", 512, 256),
    ("bullet_p2", "red laser bolt, horizontal energy projectile, crimson plasma, isolated on solid black background", "bullets", 512, 256),
    ("bg_space", "deep space background, distant stars, subtle nebula, dark void, purple blue tint, retro game aesthetic", "backgrounds", 1024, 512),
    ("blackhole", "black hole in space, dark void center, purple accretion disk, swirling energy, glowing event horizon, isolated on solid black background", "shield", 512, 512),
]


def main():
    print("=== IN THE BLACK — V2 Asset Generation ===")
    print(f"Model: {MODEL} + LoRA: {LORA} @ {LORA_WEIGHT}\n")

    jobs = []

    # Ships
    for name, prompt in SHIPS:
        prefix = f"itb_v2_{name}"
        print(f"[QUEUE] {name}")
        wf = make_workflow_with_lora(prompt, NEGATIVE, 512, 512, filename_prefix=prefix)
        pid = queue_prompt(wf)
        if pid:
            jobs.append((pid, name, os.path.join(OUTPUT_DIR, "ships"), prefix))
            print(f"  queued: {pid}")
        time.sleep(0.3)

    # Other assets
    for name, prompt, subdir, w, h in OTHER:
        prefix = f"itb_v2_{name}"
        print(f"[QUEUE] {name}")
        wf = make_workflow_with_lora(prompt, NEGATIVE, w, h, filename_prefix=prefix)
        pid = queue_prompt(wf)
        if pid:
            jobs.append((pid, name, os.path.join(OUTPUT_DIR, subdir), prefix))
            print(f"  queued: {pid}")
        time.sleep(0.3)

    print(f"\n=== Waiting for {len(jobs)} jobs ===\n")

    for pid, name, dest, prefix in jobs:
        print(f"[WAIT] {name}...")
        history = wait_for_completion(pid)
        collect_images(history, dest, prefix)

    print("\n=== Done! ===")
    for subdir in ["ships", "shield", "bullets", "backgrounds"]:
        path = os.path.join(OUTPUT_DIR, subdir)
        if os.path.exists(path):
            v2_files = [f for f in os.listdir(path) if f.startswith("itb_v2_")]
            print(f"{subdir}/: {len(v2_files)} v2 files")
            for f in sorted(v2_files):
                print(f"  {f}")


if __name__ == "__main__":
    main()
