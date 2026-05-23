---
name: image-crop-to-png-pipeline
description: 从参考图中切出独立元素到本地，再把每个 crop 的真实图片内容作为参考素材交给 Codex 当前可用的内置图片生成/编辑能力重绘，最后只从 AI 重绘图输出透明 PNG。适用于 UI 还原、贴纸拆解、素材提取、插画资产整理；严禁把本地 crop 抠透明后当最终图交付，也不要向用户索要外部图片生成 API。
---

# Image Crop to PNG Pipeline

## 何时触发

当用户提出以下意图时触发：

- “从图片里把元素切出来”
- “批量抠图成 PNG”
- “切图 -> AI 生图 -> 透明 PNG”
- “把贴纸/图标/插画拆成独立素材”
- “把切好的素材再用 AI/内置生图能力生成一遍”

## 核心目标

对一张或多张参考图执行标准流水线：

1. 切图到本地（按独立元素）
2. 把每个 crop 的真实图片内容作为参考素材交给 Codex 当前可用的内置图片生成/编辑能力重绘
3. 对 AI 生成图做键色抠图（输出透明 PNG）
4. 生成清单与预览

本地 crop、传统抠图、背景透明化都只是中间步骤；最终交付默认必须来自 AI 重绘后的图像。只有当用户明确说“不要 AI 重绘”“只要本地透明化”“不要重新生成”这类排除 AI 重绘的话时，才跳过 AI 重绘。

## 一句话定义

这个 skill 要做的是：`原图 -> 识别可切元素 -> 保存 crop 参考素材 -> 把真实 crop 图片交给内置 AI 重绘 -> 得到带键色背景的新图 -> 抠键色 -> 独立透明 PNG`。

## 运行模式

先判断当前环境是否能把本地 `crops/*.png` 的真实图片内容交给内置图片生成/编辑能力：

- 完整模式：如果可以把 crop 作为图片参考输入，继续执行 `crops/ -> ai_raw/ -> generated/`，最终交付透明 PNG。
- 交接模式：如果不能把本地 crop 作为图片参考输入，不要说任务失败，也不要本地抠图冒充最终 PNG。完成 `crops/`、`crops_manifest.json`、`crops_contact_sheet.*`、参考素材 zip，并告诉用户这些是“AI 重绘前的参考素材包”，下一步需要把 crop 或 contact sheet 作为图片附件重新交给 Codex/当前会话。
- 续跑模式：如果用户已经把某个 crop、contact sheet、或之前导出的参考素材重新作为图片附件提供给当前对话，不要从原图重新切图；直接从 AI 重绘步骤继续，生成 `ai_raw/`，再抠键色输出 `generated/`。

交接模式不是最终完成；它是缺少“本地文件 -> 图片参考输入”通道时的正确中间产物。

## 图片生成能力约定

- 本 skill 中的“AI 重绘”“图片生成”都指 Codex 当前环境已经提供的图片生成/图片编辑能力，不等于要求用户提供 OpenAI API key、图片生成 API、SDK 或环境变量。
- 优先使用当前对话/应用里已经可调用的内置生图工具；不要停下来要求用户配置外部 API。
- 如果存在多个可用工具，选择能把 crop 图像本身作为参考输入的工具。工具名可以是 image generation、image editing、imagegen、内置图片生成等，不要求固定模型名。
- 不要只根据工具参数名判断是否支持参考图。只要能通过当前对话附件、文件引用、图片编辑上下文或工具输入把 crop 作为实际图片上下文传入，就算满足参考图输入要求。
- 只有在当前环境完全没有可用的图片生成/编辑能力，或完全没有任何方式把 crop 作为图片参考传入时，才进入交接模式并说明能力缺口。

## 禁止 API 误判

- 不要检查、要求或提及 `OPENAI_API_KEY`、外部图片生成 API key、SDK 安装状态、命令行图片生成配置。
- `OPENAI_API_KEY` 未配置不影响本 skill；本 skill 默认走 Codex 当前会话/界面里的内置图片能力，不走命令行 API。
- 不要把“命令行没有 API key”“没有外部 API 工具”“没有 generate_assets.py”写成阻塞原因。
- 唯一需要判断的是：当前会话/工具是否能让 AI 重绘步骤看到或引用 crop 的真实图片内容。
- 如果不能，就进入交接模式，输出参考素材包和续跑说明；不要把原因归结为 API key。

## Codex 会话优先路径

当 crop/contact sheet 已经在当前回复中展示、用户把 crop 图片重新发回、或当前界面可以把图片作为附件/上下文继续处理时，优先把这视为可用的参考图输入路径，并继续 AI 重绘。

不要因为本地工具列表里没有命令行生图工具就放弃。Codex 的会话图片上下文优先于命令行/API 路线。

## 参考图交接规则

- 保存到 `crops/` 的文件只是参考素材，不是最终素材。
- AI 重绘时必须交接“图片内容本身”，不能只在 prompt 里写本地路径、文件名、bbox 或文字描述。
- 如果内置生图工具支持附件、图片编辑上下文、文件引用、当前对话图片上下文等方式，优先用这些方式把 crop 传进去。
- 在调用 AI 重绘前，先打开或渲染 crop，确认 agent 看到的图片就是要重绘的元素。
- 生成提示词要明确说明：参考输入就是这张 crop，保留主体形象、风格、颜色和比例，只重绘干净独立主体，并放在纯色键色背景上。
- 如果当前工具只能接收纯文本、无法接收或引用真实 crop 图片，进入交接模式并说明“缺少参考图交接能力”；不要改成只用文字描述生成，也不要要求用户提供外部 API。

## 不可绕过的硬规则

- 最终 `generated/*.png` 的直接来源只能是 `ai_raw/` 中的 AI 重绘图，不能是 `crops/`、原图、截图或本地透明化结果。
- 禁止执行或描述 `crops/ -> generated/` 的直通流程。若发现自己正准备这样做，必须停止并改回 `crops/ -> ai_raw/ -> generated/`。
- `scripts/remove_bg_adaptive.py` 只能用于 `ai_raw/` 里的键色背景图。不要对 `crops/` 运行它来制造最终交付物。
- AI 重绘步骤必须真的把 crop 图像内容作为参考输入。仅写文本提示词、根据文件名想象、或用本地脚本“模拟 AI 生成”都不合格。
- 如果经过实际检查，当前环境完全没有任何方式把 crop 作为图片上下文、附件、文件引用或编辑输入传给可用图片生成工具，必须进入交接模式；不要继续做本地抠图替代，也不要改为索要外部 API。
- 交付前必须能说明每个最终 PNG 的链路：`crop_id -> crop file -> ai_raw file -> generated file`。缺少 `ai_raw` 证据时，任务未完成。

## 高风险误执行场景

最容易犯的错误是：看到本地已有裁剪和抠图脚本，就把源图切成 `crops/*.png`，再直接把这些 crop 改成透明底，保存到 `generated/*.png`，最后告诉用户“PNG 已生成”。这条路径看起来完成了切图和透明化，但它完全跳过了 AI 参考图重绘，因此不是本 skill 的合格输出。

另一个常见错误是：把“AI 重绘”理解成外部 API 要求，于是要求用户提供 API key 或让用户安装 SDK。不要这样做。Codex 环境里若已有内置图片生成/编辑能力，应直接使用该能力完成重绘。

第三个常见错误是：只把 `assets/<task>/crops/crop_001.png` 这个路径写进 prompt，让生图工具“想象”它。这不算把 crop 当素材给到 AI。必须让 AI 重绘步骤能实际看到或引用 crop 的图片内容。

第四个常见错误是：报告“`OPENAI_API_KEY` 未配置，所以不能生成”。不要这样做。除非用户明确要求使用外部 OpenAI API，否则 API key 与本 skill 无关。

遇到“把图片切出来做成透明 PNG”“批量抠图”“生成独立素材”这类请求时，先问自己：

- 我有没有把每个 crop 的真实图片内容传给可用的内置图片生成/编辑工具作为参考？
- 我有没有得到新的 AI 重绘图，并保存到 `ai_raw/`？
- `generated/` 里的透明 PNG 是否只来自 `ai_raw/`，而不是来自 `crops/`？
- `generated_manifest.json` 是否能证明 `reference_image_used: true`？

如果任何答案是否定的，不能交付最终 PNG。此时应进入交接模式并说明：已完成本地 crop，但尚未完成 AI 参考图重绘。

## 关键教训

- 先确认源图文件名。若目录里有相似图片，不要猜；优先使用用户明确给出的路径。
- 不要把原始 crop 透明化后当成最终资产。这个 skill 的核心价值是“crop 作为参考图 -> AI 重绘 -> 透明 PNG”。
- 如果本地脚本缺少 AI 生成实现，直接说明由 Codex 的图片生成能力执行该步骤，不要声称脚本能批量完成。
- 如果当前图片生成工具不能接收本地 crop/附件作为参考图，必须进入交接模式说明限制；不能用纯文本描述生成来冒充“参考图重绘”。
- 不要让用户提供外部图片生成 API；除非用户明确要求用外部 API，否则使用 Codex 已有的内置生图能力。
- 对大量元素先做 1 个小样。小样必须通过“风格、主体完整、颜色、透明边缘”检查后再继续批量。
- 若用户纠正流程，立即停止当前错误路径，重新对齐流程和产物目录。

## 强制流程

1. 输入分析
   - 识别来源图片路径
   - 若有多个候选图片，列出差异并使用用户指定文件
   - 判断是“自动分割”还是“半自动人工框选”

2. 本地切图
   - 输出到 `assets/<task>/crops/`
   - 记录 `crops_manifest.json`
   - 生成切图预览 `preview/crops_contact_sheet.*`
   - 这一步只产出 AI 参考素材，不能作为最终交付
   - 截图边缘露出的残缺元素不要默认进入 AI 队列；剔除或先让用户确认

3. AI 重绘
   - 使用 Codex 当前可用的内置图片生成/编辑能力，而不是本地脚本假装生成
   - 不要要求用户提供外部图片生成 API key；外部 API 不是本 skill 的默认依赖
   - 在调用前检查工具是否支持图像参考输入；不要只看参数名，当前对话附件、文件引用、图片编辑上下文都可以作为可用路径
   - 如果完全无法把 crop 作为图片参考传入，进入交接模式，不能进入最终 PNG 生成
   - 必须把 crop 的真实图片内容作为参考输入；如果做不到，进入交接模式并报告缺口
   - 默认逐个 crop 生成；数量很多时可先做 contact sheet 小批量验证，但必须能拆回独立素材并保持顺序
   - 提示词必须要求：参考输入 crop、保持原风格和原配色、只生成主体、主体完整居中、无文字水印、纯色键色背景
   - AI 生成原图先保存到 `assets/<task>/ai_raw/`

4. 抠图与透明 PNG
   - 输入必须来自 `assets/<task>/ai_raw/`；若只有 `crops/`，说明 AI 重绘尚未完成
   - 自适应键色策略：
     - 主体含绿色 -> 用洋红 `#FF00FF`
     - 主体含洋红/粉紫 -> 用绿色 `#00FF00`
     - 不确定 -> 优先 `#FF00FF`
   - 只能移除“从画布边缘连通的键色背景”，不要全图按颜色替换，避免误伤腮红、花朵、衣服等主体颜色
   - 输出到 `assets/<task>/generated/*.png`
   - 必须验证 alpha 通道有效

5. 产物归档
   - 生成 `generated_manifest.json`
   - 生成 `preview/generated_contact_sheet.png`
   - `generated_manifest.json` 中每个 item 必须包含 `crop_file`、`ai_raw_file`、`generated_file`、`generation_tool`、`reference_image_used: true`

`generated_manifest.json` 最小结构示例：

```json
{
  "items": [
    {
      "crop_id": "crop_001",
      "crop_file": "assets/<task>/crops/crop_001.png",
      "ai_raw_file": "assets/<task>/ai_raw/crop_001_raw.png",
      "generated_file": "assets/<task>/generated/crop_001.png",
      "generation_tool": "Codex built-in image generation/editing",
      "reference_image_used": true
    }
  ]
}
```

## 交接模式产物

当无法自动执行 AI 重绘时，必须输出这些中间产物，方便用户继续：

- `assets/<task>/crops/`：独立 crop 参考素材
- `assets/<task>/manifests/crops_manifest.json`：crop 顺序、来源框、状态
- `assets/<task>/preview/crops_contact_sheet.*`：总览预览图
- `<task>_crops_reference_png.zip`：可重新上传的参考素材包

交接模式回复用户时必须明确：

- 这些文件不是最终透明 PNG。
- 当前停在 `crop -> AI 重绘` 之间。
- 下一步请把需要重绘的 crop PNG，或整个 contact sheet/zip，作为图片附件重新发回当前对话；收到图片附件后直接从 AI 重绘继续，不要重新切图。
- 不要把 `OPENAI_API_KEY`、外部 API、SDK 或命令行工具配置写成阻塞原因。

## 质量门禁

每个输出 PNG 必须满足：

- `generated_manifest.json` 证明其来自 AI 重绘图，而不是原始 crop
- 有透明通道（alpha）
- 边缘无明显锯齿与彩边
- 主体无误扣（尤其绿色叶子/植物）
- 无额外背景块、无脏像素、无水印
- 文件名和 manifest 顺序可追溯到原始 crop

小样不合格时先修策略，不要继续批量：

- 颜色偏离：加强“严格保留原配色”，或改为更小批次/逐张生成。
- 背景去除伤主体：换键色，或改用边缘连通键色算法。
- 多个主体粘连：回到切图步骤，手动拆分 crop。
- 边缘残缺元素被切出：重新切图并跳过 touches_edge 组件，或让用户确认是否需要保留。
- AI 漏主体/改姿态：重跑该 crop，并在提示词中描述关键形状和动作。

## 推荐目录规范

```text
assets/<task>/
  crops/
  ai_raw/
  generated/
  manifests/
    crops_manifest.json
    generated_manifest.json
  preview/
    crops_contact_sheet.jpg
    generated_contact_sheet.png
```

## 脚本约定

- `scripts/extract_crops.py`
  - 输入：source image、可选框选参数
  - 输出：`crops/` + `crops_manifest.json`

- `scripts/generate_assets.py`
  - 当前仓库可能没有该脚本；不要依赖它完成 AI 生成
  - 若存在，仍需确认它真的调用可用的图片生成/编辑能力并保存 `ai_raw/`
  - 若不存在，由 Codex 使用图片生成工具逐张或小批量执行

- `scripts/remove_bg_adaptive.py`
  - 输入：`ai_raw/` 中的 AI 原图、可选 key color/subject hint
  - 输出：透明 PNG 到 `generated/`
  - 必须使用边缘连通背景去除，不能全图替换键色
  - 禁止将 `crops/` 作为输入来生成最终资产

- `scripts/build_contact_sheet.py`
  - 输入：`crops/` 或 `generated/`
  - 输出：预览图

## AI 重绘提示词模板

对每个 crop 使用类似提示词，并按具体主体补充：

```text
Use the provided crop as the exact visual reference. Regenerate a clean standalone sticker/icon of only the main subject. Preserve the original character design, pose, proportions, line weight, colors, and cute rounded style. Center the subject with a small safe margin. Do not add text, watermark, shadows, border frames, or extra objects. Put the subject on a flat solid KEY_COLOR background only.
```

其中 `KEY_COLOR` 根据主体颜色替换为 `#FF00FF` 或 `#00FF00`。

## 执行原则

- 先小样验证，再批量执行。
- 抠图失败时优先换键色，其次调阈值和收边参数。
- 不直接把原始截图 crop 当最终资产。
- 没有 `ai_raw/` 就没有最终交付。
- 交付前展示 `generated_contact_sheet.png`，并说明最终 PNG 来自 AI 重绘后的透明化结果。
