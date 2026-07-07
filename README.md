# 🎮 Petdex Pets

自定义 [Petdex](https://petdex.crafter.run) 桌面宠物合集。基于 Plants vs. Zombies 2 原版精灵图制作。

## 📦 已收录宠物

| 宠物 | 预览 | 说明 | 帧源 |
|------|------|------|------|
| **Peashooter** (豌豆射手) | `peashooter/` | 经典豌豆射手，闲置张嘴闭嘴，跳跃吐豌豆 | PvZ2 International 144帧 |
| **Peashooter CN** (豌豆射手中文版) | `cn-peashooter/` | 中文版豌豆射手，射击动画更夸张(140px嘴!) | PvZ2 Chinese 57帧 |

## 🚀 安装

### 方式一：Petdex 官方安装（推荐）

提交到 Petdex Gallery 审核通过后：

```bash
petdex install peashooter
petdex install cn-peashooter
```

### 方式二：手动安装

```bash
# 克隆仓库
git clone https://github.com/YOUR_USERNAME/petdex-pets.git

# 复制到 Petdex 目录
cp -r petdex-pets/peashooter ~/.petdex/pets/
cp -r petdex-pets/cn-peashooter ~/.petdex/pets/

# 切换宠物
petdex select peashooter       # 豌豆射手
petdex select cn-peashooter    # 豌豆射手中文版
```

## 🛠️ 宠物格式

每个宠物文件夹包含两个文件：

```
pet-name/
├── pet.json          # 宠物元信息
└── spritesheet.webp  # 1536×1872 精灵动画 (8列×9行)
```

### pet.json 示例

```json
{
  "id": "peashooter",
  "displayName": "Peashooter",
  "description": "The iconic Peashooter from Plants vs Zombies 2!",
  "spritesheetPath": "spritesheet.webp"
}
```

### Spritesheet 规格

- 尺寸：1536 × 1872 像素
- 网格：8 列 × 9 行
- 每格：192 × 208 像素
- CSS：`background-size: 800% 900%`

| Row | 动画 | 帧数 |
|-----|------|------|
| 0 | idle (闲置) | 6 |
| 1 | running-right (右跑) | 8 |
| 2 | running-left (左跑) | 8 |
| 3 | waving (挥手) | 4 |
| 4 | jumping (跳跃) | 5 |
| 5 | failed (失败) | 8 |
| 6 | waiting (等待) | 6 |
| 7 | running (奔跑) | 6 |
| 8 | review (检查) | 6 |

## 📝 自制宠物

1. 准备精灵图素材（推荐从 [Spriters Resource](https://www.spriters-resource.com/) 下载 PvZ2 的 Assembled Sprites）
2. 参考 `tools/` 目录下的构建脚本
3. 按照上述格式创建 `pet.json` + `spritesheet.webp`
4. 放到 `~/.petdex/pets/你的宠物名/` 即可使用
5. 欢迎 PR 贡献新宠物！

## 📄 License

宠物精灵图版权归原始游戏厂商所有。本仓库仅做粉丝二次创作和收集，仅供个人学习交流使用。
