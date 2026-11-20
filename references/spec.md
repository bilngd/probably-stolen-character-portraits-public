# 立绘规格：源码依据与原版实测

> **2026-11-19 起立绘只交付 4×（1152×844）。** 本页 288×211 的原版实测只作规格依据与 ×4 换算；1× 不再产出，A/B 也不再做。4× 规格见 `workflow-hires.md` 第 1 节。

## 原版实测（Probably Stolen 0.46D，`sharedassets1.assets`）

| 精灵 | 画布 | 人物 bbox | 颜色数 | alpha 取值 | PPU | pivot |
|---|---|---|---|---|---|---|
| `maleUpper_0` | 288×211 | (72,49)–(218,211) = 146×162 | 23 | 仅 0 / 255 | 100 | (0.5,0.5) |
| `femaleUpper_1` | 288×211 | 140×164 | — | — | 100 | (0.5,0.5) |
| `scavMale_0` | 288×211 | — | — | 仅 0 / 255 | 100 | (0.5,0.5) |

- 轮廓一圈**只有一个颜色**：`(41,34,52)`，即统一描边（1× 1px；4× 2px，仍同一色）。
- 人物**底部贴画布底边**（`211 - bbox.bottom = 0`），水平中心 ≈ 画布中心。
- 纹理是 `TextureFormat` 4（RGBA32），`settingsRaw = 0`（FullRect，非 tight）。

立绘池帧数（同一 assets）：

```
maleUpper 12   femaleUpper 16   maleLower 14   femaleLower 17
scavMale 2     scavFemale 14    maleBM 9       femaleBM 8
```

## SpriteDict：顾客立绘怎么被取用

`Assembly-CSharp.decompiled.cs` 约 178100–178340 行。

```csharp
// 池子按前缀 + 连续编号取，遇到断档即停
public static List<string> GetPool(string prefix, int cap = int.MaxValue)

public static string GetRandomUpperSpriteName()
    => ClientSpriteVariety.PickGendered(GetPool("maleUpper"), GetPool("femaleUpper"));
public static string GetRandomShadySpriteName()
    => ClientSpriteVariety.PickGendered(GetPool("maleBM"), GetPool("femaleBM"));
```

- `spriteEntries / upperMaleEntries / upperFemaleEntries / lowerMaleEntries / ...` 都是序列化的 `List<SpriteEntry>`，`Awake` 时灌进 `public Dictionary<string, Sprite> spriteDictionary`；重复 key 会被跳过。
- **自定义 key 不会进入原版池**（`GetPool` 只认 `prefix1..N`），必须显式注入 `spriteDictionary`。
- `GetSprite(key)` 找不到 key 时 `Debug.LogWarning` 并 fallback 到 `GetRandomScavSpriteName()` → 人物会变成随机的拾荒者立绘，看起来像“画错了”。

性别判定（约 48506 行）：

```csharp
public static LocGender GetGenderFromSpriteName(string spriteName) {
    if (uniqueSpriteGender.TryGetValue(spriteName, out var value)) return value;
    if (spriteName.IndexOf("female", OrdinalIgnoreCase) >= 0) return LocGender.Female;
    if (spriteName.IndexOf("male",   OrdinalIgnoreCase) >= 0) return LocGender.Male;
    return LocGender.Neutral;
}
```

→ key 里带 `male` / `female` 才能拿到正确的对话称呼。

## ModLoader：为什么必须放 `Textures/Items/`

`Assembly-CSharp.decompiled.cs` 约 235588–235652 行：

| 目录 | 产出 | 加载参数 |
|---|---|---|
| `Textures/`（根） | `mod.Textures[key]`（Texture2D） | `pixelArt=false` → mipmap **开**、默认 Bilinear |
| `Textures/Items/` | `mod.Sprites[key]`（Sprite） | `pixelArt=true` → `FilterMode.Point`、`Clamp`、`Apply()` 无 mipmap；**4× 由 MOD 代码在 Rebuild 时改成 Bilinear、mipmap 仍关** |
| `Textures/Paper/` | `mod.PaperSprites[key]` | Bilinear + FullRect |

Items 分支的 Sprite 创建：

```csharp
Sprite.Create(texture2D, new Rect(0,0,w,h), new Vector2(0.5f,0.5f), 100f);
// 未传 meshType → 默认 SpriteMeshType.Tight
```

UI 里要显示完整透明边，建议在代码中重建为 `SpriteMeshType.FullRect`。

## 代码接入

```csharp
// 1) 从 mod.Sprites 取（key = 文件名，不带扩展名）
Sprite sp = mod.Sprites["maleUpperExample4x"];

// 2) 注入 SpriteDict（public 字段，可直接写；或在 OnGameLoadedInit 之后）
SpriteDict.Instance.spriteDictionary["maleUpperExample4x"] = sp;

// 3) 顾客使用
client.spriteName = "maleUpperExample4x";
```

> **4× 不能直接注入 `mod.Sprites[...]`**：它的 PPU 是 100、Filter 是 Point、Mesh 是 Tight，直接挂到 `client.spriteName` 会变成 4 倍大且边缘被裁。必须按 `workflow-integrate.md` 的 `Rebuild`（PPU × 4、FullRect、Bilinear）重建后再注入。

自定义顾客的 key 同时避开 `GetPool("maleUpper")` 的 `1..12` 连续池、并保留 `male` 前缀的性别判定（示例用的是已在项目里的 `maleUpperExample4x`；换成自己的角色时保持 `<gender>...4x` 形状即可）。

## 物品图标 vs 人物立绘

| 项 | 物品图标 | 人物立绘 |
|---|---|---|
| 画布 | 16×格数（16/32/64…） | **4× 1152×844**（1× 288×211 仅历史/换算） |
| 背景 alpha | **1**（占格判定用） | **0** |
| 尺寸约束 | 必须 16 的倍数 | 无（844 不是 16 倍数） |
| PPU / pivot | 100 / (0.5,0.5) | 100（1×）/ **400（4×）**；pivot (0.5,0.5) |
| 过滤 | Point/Clamp/无 mipmap | 4× Bilinear、**mipmap 仍关** |
| 描边 | 按材质剖面 | 4× 统一 **2px `#292234`**（1× 1px 历史） |
