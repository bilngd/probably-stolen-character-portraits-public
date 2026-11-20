# 落位与代码接入

已有合格 **4× PNG（1152×844）** 时只读这一篇。1×（288×211）只作历史对照，不再产出。

## 文件放哪

```
<MOD>/
├── Textures/Items/<key>4x.png   ← 唯一交付（pixelArt Sprite，4× 画布）
├── Textures/Items/<key>.png     ← 可选：旧 1×，仅作对照/回退
├── manifest.xml
└── <Name>.dll
```

- `build.cmd` 会把整个 `Textures/` 同步到 `dist/<MOD>/Textures/`
- 不要放 `Textures/` 根：那里是 `pixelArt=false` 的 Texture2D（bilinear + **mipmap 开**），像素会糊；**4× 也不要放这里**（4× 要的是 Bilinear、mipmap 关，由代码在 Items 加载后改）
- 不要放 `Textures/Paper/`：PaperSprites 是给纸张 UI 用的（bilinear）

## 命名

- key = 文件名（不带扩展名），**必须含 `male` 或 `female`**：`LocGender.GetGenderFromSpriteName` 靠子串判性别，影响对话称呼
- 建议格式 `<gender><阶层><角色>`：`femaleUpperExample`、`maleUpperExample`
- 避免 `maleUpper1..12` / `femaleUpper1..16` 这种纯编号：会和原版池撞名

### 高清后缀：`4x`（`2x` 仅过渡档）

文件名末尾带 `2x`–`9x` 时，加载侧会把它当成“高分辨率但世界尺寸不变”的立绘：

| 文件 | 画布 | PPU | 世界尺寸 |
|---|---|---|---|
| `maleUpperExample.png`（旧 1×，不再产出） | 288×211 | 100 | 2.88×2.11 |
| `maleUpperExample2x.png` | 576×422 | 200 | 2.88×2.11（F8 过渡档，不作交付） |
| `maleUpperExample4x.png` | 1152×844 | 400 | 2.88×2.11 |

- MOD 的 `Textures/Items` 分支固定 `PPU 100`，**必须**按 key 后缀乘上去，否则 4× 图会变成 4 倍大的巨人。
- 重建 Sprite 用 `Sprite.Create(tex, new Rect(0,0,w,h), new Vector2(0.5f,0.5f), 100f * N, 0, SpriteMeshType.FullRect)`，pivot 抄原版。
- 4x 纹理在 Rebuild 时设 `FilterMode.Bilinear`、**mipmap 关**（4× 是像素画，缩小要保硬边；mipmap 会糊成插画）。1x 仍是 Point / 无 mipmap。
- 4× 的 PNG **仍放 `Textures/Items/`**，这样才进 `mod.Sprites` 被重建；不要为了“要 Bilinear”把图丢到 `Textures/` 根（那里的 mipmap 是开的，只会更糊）。
- **4× 是唯一交付**：`<key>4x.png` 放 `Textures/Items/`，由加载器按后缀给 PPU 400。
- 旧 1×（不带后缀）若已存在可留作对照，但不再为新角色产出；不要为了“回退”再转一版 1×。
- 完整流程与验收见 `workflow-hires.md`。

## 阶级 → 立绘池 / faction

| 角色定位 | faction | 立绘池 |
|---|---|---|
| 上等客人 | `StoreClient.FACTION_UPPER` | `maleUpper` / `femaleUpper` |
| 中层 / 拾荒者 | `StoreClient.FACTION_MIDDLE` | `maleBM` / `femaleBM`、`scavMale` / `scavFemale` |
| 下等客人 | `StoreClient.FACTION_LOWER` | `maleLower` / `femaleLower` |

自定义角色虽然挂在 upper 池的“风格”里，但 key 不进池，必须显式指定。

## C# 接入

```csharp
// mod.Sprites 由 ModLoader 从 Textures/Items 加载（key = 文件名，含 4x 后缀）
Sprite sp = mod.Sprites["femaleUpperExample4x"];

// SpriteDict.spriteDictionary 是 public 字段，直接注入
SpriteDict.Instance.spriteDictionary["femaleUpperExample4x"] = sp;

// 顾客使用
client.spriteName = "femaleUpperExample4x";
client.clientFaction = StoreClient.FACTION_UPPER;
```

- 注入时机：`ModHook.OnGameLoadedInit` 之后、`GenerateClient` 之前
- `SpriteDict.GetSprite(key)` 找不到 key 会 warning 并 fallback 到随机 scav 立绘 → 人物变成脏兮兮的拾荒者；4× 的 key 带 `4x` 后缀，别只注册 1× 的名字。
- `GetPool("femaleUpper")` 只认 `femaleUpper1..N` 连续编号，不会自动收自定义 key

## 重建（4× 必须，不能直接注入 `mod.Sprites`）

ModLoader 的 Items 分支固定 **PPU 100、Point、Tight**。4× 图如果直接注入，会变成 4 倍大的巨人，发丝/披肩的透明边还可能被裁掉。重建时三件事一起做：**PPU 按后缀乘、FullRect、pivot 抄原版**；4× 再设 Bilinear（不创建 mipmap 就是关）。

```csharp
static Sprite Rebuild(Sprite src, string key, SpriteDict dict)
{
    // 基准 pivot / PPU 从原版立绘抄（femaleUpper1 / maleUpper1 等）
    Vector2 pivot = new Vector2(0.5f, 0.5f);
    float basePpu = 100f;
    if (dict.spriteDictionary.TryGetValue("femaleUpper1", out var r) && r != null)
    {
        pivot = new Vector2(r.pivot.x / r.rect.width, r.pivot.y / r.rect.height);
        basePpu = r.pixelsPerUnit;
    }

    float scale = key.EndsWith("4x") ? 4f : key.EndsWith("2x") ? 2f : 1f;
    if (scale > 1f) src.texture.filterMode = FilterMode.Bilinear; // mipmap 不创建

    var sp = Sprite.Create(src.texture, src.rect, pivot, basePpu * scale,
                           0, SpriteMeshType.FullRect);
    sp.name = key;
    return sp;
}
```

用法：

```csharp
string key = "femaleUpperExample4x";
Sprite built = Rebuild(mod.Sprites[key], key, SpriteDict.Instance);
SpriteDict.Instance.spriteDictionary[key] = built;
```

- `SpriteDict` 每次场景重建字典，所以注入放在「排队 / 生成顾客时」而不是启动时；幂等（已有 key 就跳过）。
- 2× / 4× 纹理改 Bilinear 后，mipmap 仍是关闭的（`Apply()` 没生成 mip 链）；不要为了“更清晰”手动开 mipmap。
- `SpriteDict.Instance` 可能还没准备好；取不到就跳过这次生成，别在启动阶段硬等。

## 进游戏验证

1. 店门打开，把该顾客拉到柜台前 → 立绘是否正常显示、有没有紫边或白边
2. 对话窗口 → 称呼是否按性别正确（他/她），不出现“它/他们”
3. 与同屏其他顾客并排 → 尺寸是否一致、有没有明显比原版胖/瘦
4. 日志搜 `Sprite Value not found for key` → 有说明注入失败，正在用 fallback
5. 立绘糊成马赛克 → 放错目录（跑到 `Textures/` 根了）
