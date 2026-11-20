# 提取原版立绘作参考

只在**首次做角色**或**要换参考图**时读。已经有合适参考图就直接去 `workflow-hires.md` §1.5（4× 唯一流程）。

## 命令

```powershell
cd <项目>\tools            # 或用绝对路径
& .\pyenv\Scripts\python.exe <skill>\scripts\extract_portraits.py `
    --out ref --base femaleUpper maleUpper
```

- 默认读 `C:/Path/To/Probably Stolen/Probably Stolen_Data`
- 依次扫 `sharedassets1.assets` / `sharedassets0.assets` / `resources.assets`
- 每帧输出两份：`<base>_<i>_full.png`（288×211 原画布）和 `<base>_<i>_trim.png`（裁掉透明边）
- 打印 `canvas / bbox / trim`，用来判断原版人物的宽高与位置

## 可用的立绘池

| base | 帧数 | 用途 |
|---|---|---|
| `maleUpper` / `femaleUpper` | 12 / 16 | **upper 阶层**（礼服、首饰、斗篷，体面甚至奢华） |
| `scavMale` / `scavFemale` | 2 / 14 | **middle 阶层**（拾荒者，破旧、脏、补丁） |
| `maleLower` / `femaleLower` | 14 / 17 | **lower 阶层**（工装、旧衣） |
| `maleBM` / `femaleBM` | 9 / 8 | 黑市 / 可疑人物 |

`maleLower` 与 `femaleLower` 是**下半身**部件，做胸像不要拿它们当主参考。

## 挑参考图的规则

配 3 张：

1. **2 张同性别、同阶层的原版立绘** —— 定画风、构图、色板（例：做上层女 → `femaleUpper_2` + `femaleUpper_1`）
2. **1 张已完成的同系列角色** —— 定服装语言，避免每个角色像不同游戏（例：已做好的酒客 / 名媛）

选帧时优先：正面、服装层次清楚、脸没有被面罩/头饰遮挡。`femaleUpper_7` 戴面纱、`femaleUpper_0` 头饰很重，不适合做“素净角色”的主参考。

## 阶级对应到服装

| 阶级 | 视觉语言 |
|---|---|
| upper | 丝绒/缎面、露肩或高领礼服、金饰、皮草、盘发 |
| middle（scav） | 旧夹克、围巾、护目镜、乱发、补丁 |
| lower | 工装、粗布、简单束发 |

用户说“上层人”就用 upper 池的立绘做参考，并在 `workflow-integrate.md` 里把 `clientFaction` 设成 `FACTION_UPPER`。

## 提取后检查

- `bbox` 宽度 120–150、高度 150–165 属于正常胸像
- `bottom` 总是等于画布高 211（人物贴底）
- 如果某帧 `trim` 特别宽（>170），说明那张是双臂张开的姿势，不适合做正面参考
