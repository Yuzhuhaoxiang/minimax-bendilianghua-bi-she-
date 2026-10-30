# -*- coding: utf-8 -*-
"""用 MiniMax H3 的 ref2v（参考图 + 参考视频）把一段母版视频改写成指定画风。

    python h3_restyle.py \
        --video master.mp4 \
        --style anchor.png \
        --prompt @prompt.txt \
        --width 960 --height 544 --frames 73 \
        --seed 20261030 \
        --prefix ink_koi

产物落在 <workdir>/out/<prefix>_0000N_.mp4。
--audio-from master.mp4 可把母版原声流拷贝回去（H3 自带的音轨会被丢掉）。

依赖：comfy_client.py 在同目录。
"""
import argparse
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import comfy_client as cc

UNET = "minimax_h3_ref2va_pruned_int8_convrot.safetensors"
TEXT_ENC = "qwen3vl_32b_minimax_h3_nvfp4_awq.safetensors"
VAE_VIDEO = "minimax_h3_video_vae_int8_convrot.safetensors"
VAE_AUDIO = "minimax_h3_audio_vae_fp32.safetensors"
LORA = "minimax_h3_ref2v_turbo_4step_v0.1_comfyui_bf16.safetensors"


def snap_frames(n):
    """H3 要求帧数落在 17k+5 网格上（24fps）。"""
    n = max(5, int(n))
    while n % 17 != 5:
        n += 1
    return n


def build(prompt, width, height, frames, seed, steps, sampler, scheduler,
          video_name=None, style_name=None, lora_strength=1.0):
    g = {
        "1": {"class_type": "UNETLoader",
              "inputs": {"unet_name": UNET, "weight_dtype": "default"}},
        "2": {"class_type": "CLIPLoader",
              "inputs": {"clip_name": TEXT_ENC, "type": "minimax"}},
        "3": {"class_type": "VAELoader", "inputs": {"vae_name": VAE_VIDEO}},
        "4": {"class_type": "VAELoader", "inputs": {"vae_name": VAE_AUDIO}},
        "5": {"class_type": "LoraLoaderModelOnly",
              "inputs": {"model": ["1", 0], "lora_name": LORA, "strength_model": lora_strength}},
        "7": {"class_type": "MiniMaxH3ReferenceToVideo",
              "inputs": {"clip": ["2", 0], "prompt": prompt, "width": width, "height": height,
                         "length": frames, "ref_image_size": "match",
                         "vae": ["3", 0], "audio_vae": ["4", 0]}},
        "8": {"class_type": "BasicGuider", "inputs": {"model": ["5", 0], "conditioning": ["7", 0]}},
        "9": {"class_type": "KSamplerSelect", "inputs": {"sampler_name": sampler}},
        "10": {"class_type": "BasicScheduler",
               "inputs": {"model": ["5", 0], "scheduler": scheduler, "steps": steps, "denoise": 1.0}},
        "11": {"class_type": "RandomNoise", "inputs": {"noise_seed": seed}},
        "12": {"class_type": "SamplerCustomAdvanced",
               "inputs": {"noise": ["11", 0], "guider": ["8", 0], "sampler": ["9", 0],
                          "sigmas": ["10", 0], "latent_image": ["7", 1]}},
        "13": {"class_type": "VAEDecode", "inputs": {"samples": ["12", 0], "vae": ["3", 0]}},
        "14": {"class_type": "VAEDecodeAudio", "inputs": {"samples": ["12", 0], "vae": ["4", 0]}},
        "15": {"class_type": "CreateVideo",
               "inputs": {"images": ["13", 0], "audio": ["14", 0], "fps": 24}},
        "16": {"class_type": "SaveVideo",
               "inputs": {"video": ["15", 0], "filename_prefix": "out", "format": "auto"}},
    }
    if video_name:
        g["6"] = {"class_type": "LoadVideo", "inputs": {"file": video_name}}
        g["6b"] = {"class_type": "GetVideoComponents", "inputs": {"video": ["6", 0]}}
        # Autogrow 输入的键名必须是 "<组名>.<子名>"
        g["7"]["inputs"]["ref_videos.ref_video_0"] = ["6b", 0]
    if style_name:
        g["6c"] = {"class_type": "LoadImage", "inputs": {"image": style_name}}
        g["7"]["inputs"]["ref_images.ref_image_0"] = ["6c", 0]
    return g


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--workdir", default=os.getcwd())
    ap.add_argument("--video", help="input 目录下的母版文件名")
    ap.add_argument("--style", help="input 目录下的风格锚图文件名")
    ap.add_argument("--prompt", required=True, help="提示词，或 @file.txt")
    ap.add_argument("--width", type=int, default=960)
    ap.add_argument("--height", type=int, default=544)
    ap.add_argument("--frames", type=int, default=73, help="会自动吸附到 17k+5")
    ap.add_argument("--seed", type=int, default=20261030)
    ap.add_argument("--steps", type=int, default=4)
    ap.add_argument("--sampler", default="res_multistep")
    ap.add_argument("--scheduler", default="beta")
    ap.add_argument("--prefix", default="restyle")
    ap.add_argument("--audio-from", help="把这段 mp4 的音轨拷回成片（相对 workdir/in）")
    ap.add_argument("--no-start", action="store_true", help="不自动启动 ComfyUI")
    args = ap.parse_args()

    if args.prompt.startswith("@"):
        with open(args.prompt[1:], "r", encoding="utf-8") as f:
            prompt = f.read().strip()
    else:
        prompt = args.prompt

    if not args.no_start:
        cc.ensure_server(args.workdir)

    frames = snap_frames(args.frames)
    graph = build(prompt, args.width, args.height, frames, args.seed, args.steps,
                  args.sampler, args.scheduler, args.video, args.style)
    graph["16"]["inputs"]["filename_prefix"] = args.prefix

    print(f"提交：{frames} 帧 / {args.width}x{args.height} / seed={args.seed}")
    pid = cc.submit(graph)
    entry = cc.wait(pid, label="h3")
    files = [f for f in cc.outputs(entry) if f.lower().endswith((".mp4", ".webm"))]
    if not files:
        print("未找到视频产物：", cc.outputs(entry))
        return 1

    src = os.path.join(args.workdir, "out", files[-1])
    print("DONE", src)

    if args.audio_from:
        import prep_master
        audio_src = os.path.join(args.workdir, "in", args.audio_from)
        if os.path.isfile(audio_src):
            prep_master._mux_audio(audio_src, src)
            print("已把母版音轨拷回")
        else:
            print("找不到音源：", audio_src)
    return 0


if __name__ == "__main__":
    sys.exit(main())
