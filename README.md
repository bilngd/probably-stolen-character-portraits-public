# Probably Stolen 角色立绘 Skill（4× 单轨 · 公开版）

为像素风游戏《深空当铺 / Probably Stolen》制作 **4× 胸像立绘（1152×844）** 的 Agent Skill：参考图 → 一次生图 → 抠图 → 28–30 色量化 → 2px 描边 → SpriteDict 接入，一条流程走完。

> 这是社区整理的方法论，不是游戏官方项目。使用前请确认你拥有《深空当铺 / Probably Stolen》本体，并遵守游戏 EULA。

## 生图模型要求（重要）

**必须使用支持“参考图生图 / 多图参考”的模型**：

- 推荐 **豆包 Seedream 5.5（模型名 `seedream_5.5`）**，一次请求出 2–3 版候选；
- 也可以用其他支持多参考图的图像模型，但必须满足：
  1. 能同时接收 5–6 张参考图（3 张原版同性别胸像 + 2–3 张原作设定）；
  2. 一次请求能出 2–3 版；
  3. 能稳定输出 1152×844 以上、人物完整的胸像构图。

**硬约束：每个角色只生成一次。** 生成前先查 `ref/<角色>_gen.log`；不存在才允许调用 1 次，生成后立即写 `batches=1`。之后任何理由（构图太宽、头太大、想换脸）都不得再次生成，只能在首批 2–3 版里换一版，或改裁切 / 转换参数。

## 4× 硬规格

| 项 | 值 |
|---|---|
| 画布 | 1152×844 |
| PPU / pivot | 400 / (0.5, 0.5) |
| 过滤 | Bilinear、mipmap 关 |
| alpha | 只有 0 / 255 |
| 颜色数 | 28–30 色 |
| 描边 | 2px `#292234`（thin + 1 圈） |
| 水平位置 | 人物中心 ≈ x=576，bottom_gap 0 |
| 存放 | `<MOD>/Textures/Items/<key>4x.png` |

体型档位与宽度口径见 [`references/workflow-hires.md` §8](references/workflow-hires.md)。

## 环境要求

- Windows（文档命令按 PowerShell / cmd 写；纯 Python 脚本在 macOS、Linux 也能跑）
- Python 3.10+
- `pip install pillow numpy`
- 需要从游戏里导原版参考图时：`pip install UnityPy`
- 游戏 **Probably Stolen 0.46D**（仅 `extract_portraits.py` 需要）

## 安装

把仓库文件夹放进豆包客户端的用户技能目录（不同版本路径可能不同，常见位置）：

```text
%LOCALAPPDATA%\Doubao\User Data\Default\.doubao\agent_mode\workspace\.user_skills\
```

最终应是：

```text
...\.user_skills\probably-stolen-character-portraits-public\SKILL.md
```

只支持 zip 导入的客户端，把整个文件夹压成 zip 后导入即可。

## 配置

脚本优先读环境变量，命令行参数优先于环境变量：

| 变量 | 含义 | 示例 |
|---|---|---|
| `PS_GAME_DIR` | 游戏根目录 | `D:\SteamLibrary\steamapps\common\Probably Stolen` |
| `PS_MANAGED_DIR` | 游戏的 `Managed` 目录（编译 MOD 时才需要） | `...\Probably Stolen_Data\Managed` |

PowerShell 临时设置：

```powershell
$env:PS_GAME_DIR = "D:\SteamLibrary\steamapps\common\Probably Stolen"
$env:PS_MANAGED_DIR = "$env:PS_GAME_DIR\Probably Stolen_Data\Managed"
```

## 快速开始

```bash
# 1. 导原版立绘（可选，做参考图时用）
python scripts/extract_portraits.py --out ref --base femaleUpper maleUpper

# 2. 量头占比 / 肩线宽
python scripts/measure_head.py assets/example_deepseek_4x.png
python scripts/measure_body_width.py assets/example_deepseek_4x.png

# 3. 色板预检
python scripts/palette_preflight.py --palette references/palettes/female_deepseek_4x.json --src raw_matted.png

# 4. 4× 转换
python scripts/convert_character.py --src raw_matted.png --out out/xxx4x.png --key femaleUpperXxx4x --palette references/palettes/xxx_4x.json --height 640 --canvas 1152x844 --outline-mode thin --despeckle 7

# 5. 补到 2px 描边
python scripts/add_outline_rings.py out/xxx4x.png out/xxx4x_final.png 1
```

完整 8 步流程、prompt 模板与验收口径见 [`SKILL.md`](SKILL.md) 与 [`references/workflow-hires.md`](references/workflow-hires.md)。

## 平台工具对应

技能里的工具名是占位名，按你所用客户端替换：

| 占位名 | 实际能力 | 豆包客户端对应 |
|---|---|---|
| `image_gen` | 支持参考图的生图，一次出 2–3 版 | 豆包生图（推荐 Seedream 5.5） |
| `upload_reference` | 本地参考图 → 可读 URL / file id | 文件上传接口 |
| `image CLI` / `matting tool` | 通用抠图（非纯色背景） | `mediakit-cli image remove-image-background --scene general` |

## 目录

```text
SKILL.md                  技能入口（frontmatter + 流程路由）
assets/                   示例：DeepSeek 4× / 1× 对照
references/
  workflow-hires.md       4× 唯一标准流程（§1.5 八步、§8 体型表）
  workflow-fan-character.md
  workflow-petite-character.md
  workflow-extract.md
  workflow-integrate.md
  spec.md                 SpriteDict / ModLoader 源码依据
  palettes/               4× 色板（28–30 色）
scripts/                  提取、测量、色板预检、转换、补描边
```

## 许可

代码与文档采用 **MIT License**，见 [`LICENSE`](LICENSE)。

示例立绘 `assets/example_deepseek_*.png` **不在 MIT 范围内**：DeepSeek 名称与形象归其所有者，示例仅用于演示流程，不得商用，详见 [`NOTICE.md`](NOTICE.md)。

---

整理自 Probably Stolen Skillkit；《深空当铺 / Probably Stolen》及相关商标归各自所有者，本项目与游戏官方无关。
