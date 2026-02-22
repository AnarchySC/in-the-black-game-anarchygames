#!/usr/bin/env python3
"""Generate beautiful wide space backgrounds — NO pixel art LoRA."""

import json, urllib.request, time, os, shutil, random

COMFY_URL = "http://127.0.0.1:8188"
OUTPUT_DIR = "/mnt/storage/Projects/shield-pong/assets/backgrounds"
COMFY_OUTPUT = os.path.expanduser("~/ComfyUI/output")

NEGATIVE = "text, watermark, signature, blurry, low quality, deformed, pixel art, pixelated, 8-bit, retro, planets close-up, spaceship, character, person, face, busy, cluttered, bright white"

BACKGROUNDS = [
    ("bg_cosmos1", "animagine-xl-3.1.safetensors",
     "stunning deep space nebula, cosmic dust clouds, vibrant purple and blue colors, scattered bright stars, dark void background, atmospheric, cinematic, beautiful, masterpiece"),
    ("bg_cosmos2", "animagine-xl-3.1.safetensors",
     "beautiful spiral galaxy in deep space, starfield, cosmic aurora, teal and cyan nebula wisps, dark atmospheric background, stunning, masterpiece"),
    ("bg_cosmos3", "animagine-xl-3.1.safetensors",
     "deep space starfield, distant red nebula clouds, scattered stars, dark void, atmospheric cosmic dust, cinematic lighting, beautiful, masterpiece"),
    ("bg_cosmos4", "waiIllustriousSDXL_v160.safetensors",
     "vast deep space panorama, purple nebula formation, bright star clusters, cosmic dust lanes, dark background, stunning detail, masterpiece"),
    ("bg_cosmos5", "waiIllustriousSDXL_v160.safetensors",
     "dark space void, distant blue and orange nebula, star clusters, cosmic atmosphere, deep beautiful space scene, masterpiece"),
]


def make_workflow(prompt_text, negative, model, width, height, seed=None):
    if seed is None:
        seed = random.randint(0, 2**32 - 1)
    return {
        "1": {"class_type": "CheckpointLoaderSimple", "inputs": {"ckpt_name": model}},
        "3": {"class_type": "CLIPTextEncode", "inputs": {"text": prompt_text, "clip": ["1", 1]}},
        "4": {"class_type": "CLIPTextEncode", "inputs": {"text": negative, "clip": ["1", 1]}},
        "5": {"class_type": "EmptyLatentImage", "inputs": {"width": width, "height": height, "batch_size": 1}},
        "6": {"class_type": "KSampler", "inputs": {
            "model": ["1", 0], "positive": ["3", 0], "negative": ["4", 0],
            "latent_image": ["5", 0], "seed": seed, "steps": 28, "cfg": 7.0,
            "sampler_name": "euler_ancestral", "scheduler": "karras", "denoise": 1.0}},
        "7": {"class_type": "VAEDecode", "inputs": {"samples": ["6", 0], "vae": ["1", 2]}},
        "8": {"class_type": "SaveImage", "inputs": {"images": ["7", 0], "filename_prefix": "itb_bg"}},
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
    return None


def collect_images(history, dest_dir, label):
    if not history or "outputs" not in history:
        return []
    os.makedirs(dest_dir, exist_ok=True)
    for node_id, node_out in history["outputs"].items():
        if "images" in node_out:
            for img in node_out["images"]:
                src = os.path.join(COMFY_OUTPUT, img.get("subfolder", ""), img["filename"])
                dst = os.path.join(dest_dir, f"{label}.png")
                if os.path.exists(src):
                    shutil.copy2(src, dst)
                    print(f"  -> {dst}")
                    return [dst]
    return []


def main():
    print("=== Generating beautiful space backgrounds (no LoRA) ===\n")
    jobs = []
    for name, model, prompt in BACKGROUNDS:
        print(f"[QUEUE] {name} via {model[:12]}...")
        wf = make_workflow(prompt, NEGATIVE, model, 1920, 512)
        pid = queue_prompt(wf)
        if pid:
            jobs.append((pid, name))
            print(f"  queued: {pid}")
        time.sleep(0.3)

    print(f"\n=== Waiting for {len(jobs)} jobs ===\n")
    for pid, name in jobs:
        print(f"[WAIT] {name}...")
        history = wait_for_completion(pid)
        collect_images(history, OUTPUT_DIR, f"itb_{name}")

    print("\n=== Done! ===")


if __name__ == "__main__":
    main()
