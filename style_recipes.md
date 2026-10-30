# 五种画风的实操配方

每条都跑通过。结构统一：**母版预处理 → 风格锚图 → H3 提示词 → 后处理**。

---

## 1. 水墨（ink wash）

- 母版预处理：`--preset none`。母版本身就是水墨就不要再转，转了反而丢笔触。
- 锚图（SDXL img2img，denoise 0.78，从母版首帧起）：
  ```
  traditional Chinese ink wash painting, sumi-e, a single vivid vermilion red koi swimming,
  seen from above through shallow water, ink bleeding into rice paper, wet-on-wet brush strokes,
  large empty paper areas, muted grey washes, minimal, no text
  ```
  负面：`photo, photorealistic, 3d, text, watermark, dots, grid, multiple fish`
- H3 提示词骨架：
  ```
  <Picture 1> defines the painting style: Chinese ink-wash on rice paper, soft grey washes,
  one vermilion koi, lots of untouched paper.
  <Video 1> is the motion reference: same top-down framing, same path, same rhythm.
  Exactly one fish. No text, no calligraphy, no seal, no dots, no grid.
  ```
- 坑：提示词里写 `seal stamp` 会生成红蓝点阵伪影，改成否定词。

## 2. 国潮彩绘（guochao，高饱和矿物颜料）

- 母版预处理：`--preset none`（国潮要从头重画，母版只提供运动）。
- 锚图（SDXL txt2img）：朱红 / 金箔黄 / 靛青 / 墨黑，描金鳞片，**必须单鱼**。
  ```
  Chinese guochao illustration, hyper-saturated mineral pigment painting, view from directly above,
  ONE single koi, every scale edged in gold leaf with crisp specular highlights,
  deep indigo to ink-black open water, gold leaf fragments, glowing golden ripple rings,
  thick saturated pigments, poster art, no border, no frame
  ```
  负面必加：`border, frame, ornament, decorative panel, plate, mandala, two fish, second fish`
- 坑：
  - 俯视提示词极易生成"装饰盘/漆盘"构图（圆形水面 + 花边）。负面词压不住，只能多试种子。
  - 锚图里有几条鱼，成片就有几条。锚图必须单鱼。

## 3. 赛博朋克霓虹

- 母版预处理：`--preset none`。
- 锚图：
  ```
  a living organic koi fish with vivid vermilion RED and WHITE body, natural overlapping scales,
  low camera at water level, cyberpunk neon channel, cyan-blue and magenta light bands on wet scales,
  defocused neon city, hexagonal bokeh, teal and magenta grading, bright clean cinematic
  ```
  负面必加：`robot, mechanical, metal, armour, sci-fi fish, silver fish, grey fish, pale fish`
- 坑：
  - 赛博朋克词会把鱼变成**机械鱼**（六边形装甲），必须显式排除。
  - 不加约束时鱼会被霓虹打成**银白色**，红白配色全丢 → 正面写 `red and white body`，负面排除 `silver/grey/pale`。
- 多镜提示词用 `CUT 1:` / `CUT 2 at two and a half seconds:` 分段，模型会做近似转场。

## 4. 1930s 迪士尼黑白手绘

- 母版预处理：`--preset gray_highkey --lo 18 --hi 205`（灰度 + 提亮，**保留中间调**）。
- 锚图：
  ```
  1930s Disney style black and white hand-drawn animation cel, hand-inked black contour lines,
  flat layered greyscale fills, bright white field, subtle film grain, one koi from above
  ```
- 后处理：成片再做一次中性灰 + 轻 S 曲线 + 胶片颗粒（σ≈0.012），去掉模型残留的暖偏。
- 坑：
  - `--lo` 设太高（如 55）会把彩色斑块压成死黑，鱼变一团墨。
  - `--preset faded_gray`（黑场抬到 60）会让白场塌成中灰，并且**会复制出第二条鱼**。慎用。
  - 母版里的大块黑拖痕，提示词改不浅，只能在预处理阶段控制。

## 5. 吉卜力透明水彩

- 母版预处理：`--preset cool_duotone`（亮度映射到 深青绿→近白，redness 遮罩保住暖色主体）。
- 锚图：
  ```
  Studio Ghibli style transparent watercolour, hand-painted animation background, top-down,
  a single koi as an OPAQUE gouache character layer, vivid vermilion head, white body with
  red-orange patches, pale translucent cyan-green water, layered glazing, bleeding edges,
  water marks, pigment granulation, faint water weeds, warm diffused sunlight
  ```
  负面：`lily pads, dark background, deep teal, murky, heavy colour, two fish, second fish`
- 坑：不写 `pale / high key / no lily pads` 就会生成深青绿的荷叶池塘。

---

## 通用提示词结构

```
<Picture 1> is the art style: <画风关键词 + 材质 + 光>。
<Video 1> is the edit master: keep the subject's structure, its path, the direction and length of
the trailing wake, and the original rhythm and timing; keep the same framing and layout.
Restyle it: <背景怎么变>。The subject is <主体处理：不透明/最亮/最清晰/居中>。
Trail: <拖痕怎么变>。
Camera: <推近/环绕幅度>。
ONE single subject, one continuous object, never duplicated, never split, no second one.
No text, no watermark, no logo. <音频要求>
```

要点：

- **提示词越长，对"单主体/锐利"的约束越弱**。核心约束放前面，装饰性描述能删就删。
- 每段都显式写"不要什么"，比只写"要什么"有效。
- 音频要求写进提示词会影响生成，但要精确控制还是靠后处理。

## 母版预处理怎么选

| 母版现状 | 目标画风 | 预设 |
|---|---|---|
| 已经是目标画风 | 同风格微调 | `none` |
| 米色纸 + 黑墨块 | 黑白动画 | `gray_highkey` |
| 米色纸 + 黑墨块 | 冷色水彩 | `cool_duotone` |
| 米色纸 + 黑墨块 | 暖色纸本 | `warm_paper` |
| 写实/3D | 任意插画风 | `none`，靠锚图拉 |

判断标准很简单：**母版的底色如果和目标画风的底色差得远，就先转；差得近就别动。**
