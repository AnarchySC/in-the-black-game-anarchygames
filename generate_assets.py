#!/usr/bin/env python3
"""
IN THE BLACK — Asset Generator
Sends workflows to ComfyUI API to generate pixel art game assets.
"""

import json
import urllib.request
import urllib.error
import time
import os
import shutil

COMFY_URL = "http://127.0.0.1:8188"
OUTPUT_DIR = "/mnt/storage/Projects/shield-pong/assets"
COMFY_OUTPUT = os.path.expanduser("~/ComfyUI/output")

MODELS = [
    "animagine-xl-3.1.safetensors",
    "NoobAI-XL-v1.0.safetensors",
    "waiIllustriousSDXL_v160.safetensors",
    "ponyDiffusionV6XL.safetensors",
]

def make_workflow(prompt_text, negative, model, width=512, height=512, seed=None, steps=25, cfg=7.0, filename_prefix="asset"):
    """Build a ComfyUI API workflow JSON."""
    import random
    if seed is None:
        seed = random.randint(0, 2**32 - 1)

    return {
        "3": {  # KSampler
            "class_type": "KSampler",
            "inputs": {
                "model": ["4", 0],
                "positive": ["6", 0],
                "negative": ["7", 0],
                "latent_image": ["5", 0],
                "seed": seed,
                "steps": steps,
                "cfg": cfg,
                "sampler_name": "euler_ancestral",
                "scheduler": "karras",
                "denoise": 1.0,
            }
        },
        "4": {  # CheckpointLoaderSimple
            "class_type": "CheckpointLoaderSimple",
            "inputs": {
                "ckpt_name": model,
            }
        },
        "5": {  # EmptyLatentImage
            "class_type": "EmptyLatentImage",
            "inputs": {
                "width": width,
                "height": height,
                "batch_size": 1,
            }
        },
        "6": {  # CLIP Text Encode (positive)
            "class_type": "CLIPTextEncode",
            "inputs": {
                "text": prompt_text,
                "clip": ["4", 1],
            }
        },
        "7": {  # CLIP Text Encode (negative)
            "class_type": "CLIPTextEncode",
            "inputs": {
                "text": negative,
                "clip": ["4", 1],
            }
        },
        "8": {  # VAEDecode
            "class_type": "VAEDecode",
            "inputs": {
                "samples": ["3", 0],
                "vae": ["4", 2],
            }
        },
        "9": {  # SaveImage
            "class_type": "SaveImage",
            "inputs": {
                "images": ["8", 0],
                "filename_prefix": filename_prefix,
            }
        },
    }


def queue_prompt(workflow):
    """Send a workflow to ComfyUI and return the prompt_id."""
    data = json.dumps({"prompt": workflow}).encode("utf-8")
    req = urllib.request.Request(
        f"{COMFY_URL}/prompt",
        data=data,
        headers={"Content-Type": "application/json"},
    )
    try:
        resp = urllib.request.urlopen(req)
        result = json.loads(resp.read())
        return result.get("prompt_id")
    except urllib.error.URLError as e:
        print(f"  ERROR: {e}")
        return None


def wait_for_completion(prompt_id, timeout=120):
    """Poll until the prompt is done."""
    start = time.time()
    while time.time() - start < timeout:
        try:
            resp = urllib.request.urlopen(f"{COMFY_URL}/history/{prompt_id}")
            history = json.loads(resp.read())
            if prompt_id in history:
                return history[prompt_id]
        except:
            pass
        time.sleep(1)
    print(f"  TIMEOUT waiting for {prompt_id}")
    return None


def collect_images(history, dest_dir, label):
    """Copy generated images from ComfyUI output to our asset dir."""
    if not history or "outputs" not in history:
        print(f"  No output for {label}")
        return []

    os.makedirs(dest_dir, exist_ok=True)
    collected = []
    for node_id, node_out in history["outputs"].items():
        if "images" in node_out:
            for img_info in node_out["images"]:
                src = os.path.join(img_info.get("subfolder", ""), img_info["filename"])
                src_path = os.path.join(COMFY_OUTPUT, src)
                dst_path = os.path.join(dest_dir, f"{label}_{img_info['filename']}")
                if os.path.exists(src_path):
                    shutil.copy2(src_path, dst_path)
                    collected.append(dst_path)
                    print(f"  Saved: {dst_path}")
    return collected


# ============================================================
# ASSET DEFINITIONS
# ============================================================

PIXEL_STYLE = "pixel art, 32-bit retro game sprite, clean pixel edges, limited color palette, dark space background, transparent background style"
NEGATIVE = "blurry, photorealistic, 3d render, photograph, watermark, text, signature, low quality, deformed, ugly, extra limbs, bad anatomy, noise, grain"

ASSETS = []

# --- SHIP TIERS ---
ship_tiers = [
    ("tier0_starter", "tiny simple spaceship, gray hull, small blue cockpit, basic design, minimal detail"),
    ("tier1_scout", "small scout spaceship, blue accents, slightly sleeker, single engine glow"),
    ("tier2_interceptor", "fast interceptor spaceship, cyan highlights, angular wings, dual engines"),
    ("tier3_viper", "aggressive viper spaceship, teal and yellow markings, side cannons, sharp nose"),
    ("tier4_phantom", "phantom stealth spaceship, dark blue with bright cyan edges, swept wings"),
    ("tier5_wraith", "wraith class spaceship, purple energy lines, ornate design, triple engines"),
    ("tier6_nova", "nova class spaceship, red and magenta hull, heavy armor plating, imposing"),
    ("tier7_supernova", "supernova spaceship, pink and white glow, crystalline wings, energy shield"),
    ("tier8_celestial", "celestial warship, purple aurora glow, massive wings, golden accents, divine"),
    ("tier9_legendary", "legendary golden spaceship, radiant glow, ornate cosmic design, ultimate power, yellow and white energy"),
]

for tier_name, tier_desc in ship_tiers:
    ASSETS.append({
        "name": tier_name,
        "prompt": f"{PIXEL_STYLE}, side view, {tier_desc}, facing right, game asset, sprite sheet style, black background",
        "negative": NEGATIVE,
        "dest": "ships",
        "size": (512, 512),
        "models": ["animagine-xl-3.1.safetensors", "NoobAI-XL-v1.0.safetensors"],
    })

# --- SHIELD ORB ---
ASSETS.append({
    "name": "shield_orb",
    "prompt": f"{PIXEL_STYLE}, glowing energy orb, translucent sphere, magical barrier, shifting colors cyan green blue purple, sparkle effects, force field bubble, game power-up, black background",
    "negative": NEGATIVE,
    "dest": "shield",
    "size": (512, 512),
    "models": ["animagine-xl-3.1.safetensors", "waiIllustriousSDXL_v160.safetensors"],
})

# --- BULLET EFFECTS ---
ASSETS.append({
    "name": "bullet_blue",
    "prompt": f"{PIXEL_STYLE}, blue laser projectile, energy bolt, horizontal beam, cyan plasma shot, game projectile sprite, black background",
    "negative": NEGATIVE,
    "dest": "bullets",
    "size": (512, 256),
    "models": ["animagine-xl-3.1.safetensors"],
})

ASSETS.append({
    "name": "bullet_red",
    "prompt": f"{PIXEL_STYLE}, red laser projectile, energy bolt, horizontal beam, crimson plasma shot, game projectile sprite, black background",
    "negative": NEGATIVE,
    "dest": "bullets",
    "size": (512, 256),
    "models": ["animagine-xl-3.1.safetensors"],
})

# --- BACKGROUNDS ---
ASSETS.append({
    "name": "bg_nebula",
    "prompt": "pixel art space background, deep space nebula, stars, cosmic dust, purple blue cyan colors, retro game background, parallax scrolling style, 16-bit aesthetic, dark void",
    "negative": "text, watermark, bright, planets, close-up, blurry",
    "dest": "backgrounds",
    "size": (1024, 512),
    "models": ["waiIllustriousSDXL_v160.safetensors", "NoobAI-XL-v1.0.safetensors"],
})

ASSETS.append({
    "name": "bg_deepspace",
    "prompt": "pixel art space background, deep black void, distant stars, faint galaxy, minimal, dark atmospheric, retro game aesthetic, subtle blue tint",
    "negative": "text, watermark, bright, colorful, busy, planets",
    "dest": "backgrounds",
    "size": (1024, 512),
    "models": ["ponyDiffusionV6XL.safetensors"],
})


# ============================================================
# GENERATE
# ============================================================

def main():
    total = sum(len(a["models"]) for a in ASSETS)
    print(f"=== IN THE BLACK — Asset Generation ===")
    print(f"Queuing {total} generations across {len(ASSETS)} asset types...\n")

    all_jobs = []

    for asset in ASSETS:
        for model in asset["models"]:
            model_short = model.replace(".safetensors", "").replace("-", "").replace(".", "")[:12]
            prefix = f"itb_{asset['name']}_{model_short}"
            w, h = asset["size"]

            print(f"[QUEUE] {asset['name']} via {model} ({w}x{h})")
            workflow = make_workflow(
                prompt_text=asset["prompt"],
                negative=asset["negative"],
                model=model,
                width=w,
                height=h,
                filename_prefix=prefix,
                steps=28,
                cfg=7.0,
            )
            prompt_id = queue_prompt(workflow)
            if prompt_id:
                all_jobs.append((prompt_id, asset, model, prefix))
                print(f"  -> Queued: {prompt_id}")
            else:
                print(f"  -> FAILED to queue")

            # Small delay between queuing to not overwhelm
            time.sleep(0.3)

    print(f"\n=== Waiting for {len(all_jobs)} jobs to complete ===\n")

    for prompt_id, asset, model, prefix in all_jobs:
        print(f"[WAIT] {asset['name']} ({model})...")
        history = wait_for_completion(prompt_id, timeout=180)
        dest = os.path.join(OUTPUT_DIR, asset["dest"])
        collect_images(history, dest, prefix)

    print(f"\n=== Done! Assets saved to {OUTPUT_DIR} ===")

    # List what we got
    for subdir in ["ships", "shield", "bullets", "backgrounds"]:
        path = os.path.join(OUTPUT_DIR, subdir)
        if os.path.exists(path):
            files = os.listdir(path)
            print(f"\n{subdir}/: {len(files)} files")
            for f in sorted(files):
                print(f"  {f}")


if __name__ == "__main__":
    main()
