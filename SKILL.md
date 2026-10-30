---
name: comfy-video-restyle
description: This skill should be used when the user supplies a reference video (often a Blender render, AI clip, or existing footage) and asks to re-render or rewrite it in a different art style while keeping the same motion, path, framing and rhythm — e.g. "把这段改成水墨风 / 国潮 / 赛博朋克 / 黑白手绘动画 / 吉卜力水彩", or "以这个视频为母版重做一版". It drives a local ComfyUI (SDXL style anchor + MiniMax H3 reference-to-video) end to end, including deterministic master preprocessing, style-anchor generation, video generation, and audio handling.
agent_created: true
---

# 参考视频画风改写（ComfyUI + MiniMax H3）

拿一段视频当"编辑母版"，保留它的运动/轨迹/构图/节奏，把画面材质与色调整体换成另一种画风，
输出 3–6 秒的新视频。

本地管线：**母版预处理 → SDXL 风格锚图 → MiniMax H3 ref2v → 后处理（音轨/调色）**。

## 何时使用

- 用户给一段视频，要求"换个画风重做"，但保留动作
- 同一段母版要出多个画风版本
- 要求"保留主体结构、换掉背景与材质"

不适用：从零生成（无母版）→ 直接用 txt2img / t2v；纯剪辑或调色 → 用常规视频工具。

## 核心认知（决定成败）

1. **参考视频会把材质和色调一起继承过来。** 母版是米色宣纸，输出就是米色宣纸；
   母版是写实沙滩，输出就是写实沙滩。**提示词改不动这一层。**
   → 必须先用 `scripts/prep_master.py` 做确定性预处理，把母版"染"成目标底色。
2. **参考图决定画风、配色和机位。** 给侧视锚图，输出就是侧视特写；给俯视锚图，输出才俯视。
   → 锚图的姿态要与母版一致。
3. **锚图里有几个主体，成片就有几个。** 锚图必须单主体。
4. **同一套素材换 `seed` 差异极大**（主体数量、机位、饱和度都会变）。要稳定结果就多跑 2–3 条挑。

## 工作流

### 1. 建工作目录

```
<workdir>/
├── in/      # 母版、锚图（LoadImage 只读这里）
└── out/     # 产物
```

### 2. 看母版

```bash
python scripts/vid_utils.py info in/master.mp4
python scripts/vid_utils.py story in/master.mp4 in/_master_story.png 4
```

记下时长、帧数、画幅、有无音轨。**帧数决定生成长度**：H3 要求 17k+5 网格
（73 ≈ 3.0 s、124 ≈ 5.2 s、158 ≈ 6.6 s）。母版比目标长就截，短就按母版长度取最近的网格值。

### 3. 预处理母版

```bash
python scripts/prep_master.py in/master.mp4 in/master_prep.mp4 --preset cool_duotone
```

预设选择见 `references/style_recipes.md` 末尾的对照表。判断原则：
**母版底色与目标底色差得远就先转，差得近就别动**（转多了会丢原画风）。

用 `vid_utils.py frames` 抽一帧确认：目标底色出来了、主体还认得出，才算合格。

### 4. 做风格锚图

用 SDXL（`sd_xl_base_1.0`）出一张"目标画风的静帧"，构图尽量贴近母版首帧。
提示词模板和各画风的具体写法见 `references/style_recipes.md`。

出 2 张候选，**只挑单主体、主体完整、底色正确的那张**。

### 5. 生成

```bash
python scripts/h3_restyle.py \
  --workdir . \
  --video master_prep.mp4 \
  --style anchor.png \
  --prompt @prompt.txt \
  --width 960 --height 544 --frames 73 \
  --seed 20261030 --prefix my_style
```

脚本会自动启动 ComfyUI、按 `17k+5` 吸附帧数、提交并等待，产物落在 `out/`。

提示词按这个结构写（详见 `references/style_recipes.md`）：

```
<Picture 1> is the art style: ...
<Video 1> is the edit master: keep the subject's structure, its path, the direction and length
of the trailing wake, and the original rhythm and timing; keep the same framing.
Restyle it: <背景怎么变>。The subject is <不透明/最亮/最清晰/居中>。
Camera: <推近/环绕幅度>。
ONE single subject, never duplicated, no second one. No text, no watermark.
```

**约束放前面，装饰性描述能删就删**——提示词越长，"单主体/锐利"越容易失效。

### 6. 验收与后处理

```bash
python scripts/vid_utils.py story out/my_style_00001_.mp4 out/story.png 6
python scripts/vid_utils.py probe_motion out/my_style_00001_.mp4   # 数值过小说明没动
```

抽 6 帧逐帧看：主体是否始终单一个、是否清晰、有无崩坏/复制。合格后再处理音频：

- 要静音：`python scripts/vid_utils.py mute out/xxx.mp4`
- 要母版原声：`h3_restyle.py --audio-from master.mp4`（流拷贝，不重编码）
- 要统一色调（黑白等）：用 `prep_master.py` 的预设处理成片，再合并音轨

最后出一张 2×2 分镜 + 首帧，随成片一起交付。

## 常见失败与对策

| 现象 | 原因 | 对策 |
|---|---|---|
| 底色还是母版的老颜色 | 没做预处理 | 换 `prep_master.py` 预设重跑 |
| 主体变成一团糊/剪影 | 预处理把中间调压死了 | 调 `--lo` 到 18 左右，保留中间调 |
| 出现第二个主体 | 锚图里有多个；或黑场抬太高 | 锚图改单主体；别用 `faded_gray` |
| 主体是机械/银白色 | 画风词盖过了主体描述 | 负面词排除 `robot/mechanical/metal/silver/pale` |
| 构图变成装饰盘/画框 | 俯视词诱发对称构图 | 负面词加 `border/frame/ornament/mandala` |
| 主体没动 | 参考视频权重被压过 | 检查 `probe_motion`，换 seed 或加长帧数 |
| `HostBuffer.read_file_slice failed` | 权重流式加载偶发 | 直接重试 |

## 资源

- `scripts/comfy_client.py` — 定位 ComfyUI、无头启动、提交/轮询/取产物、列模型
- `scripts/prep_master.py` — 母版确定性预处理（4 种预设）+ 音轨合并
- `scripts/h3_restyle.py` — 组装并运行 H3 ref2v 工作流
- `scripts/vid_utils.py` — 探测/抽帧/分镜/静音/运动量
- `references/h3_ref2v.md` — 节点图、参数、17k+5 规则、API 坑、性能表
- `references/style_recipes.md` — 水墨/国潮/赛博/黑白手绘/吉卜力 五套完整配方

## 环境

脚本依赖 `av`、`PIL`、`numpy`。**优先用 ComfyUI 自带 venv 的 python 执行**
（`<comfy>/.venv/Scripts/python.exe`），它一定装了 `av`；系统 python 往往没有 ffmpeg 二进制。
