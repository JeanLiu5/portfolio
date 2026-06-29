# Jean Photography · 个人摄影作品集

一个纯静态的摄影作品集网页，照片信息（标题 + 相机参数）由脚本自动从图片 EXIF 中读取生成。

## 目录结构

```
portfolio/
├── index.html        # 网页（双击即可在浏览器打开）
├── scan.py           # 扫描脚本：读取 EXIF、生成缩略图与 photos.js
├── update.bat        # Windows 双击运行 scan.py 的快捷方式
├── photos.js         # 自动生成的照片数据（请勿手动编辑）
├── captions.json     # 照片标题（可手动修改，运行 scan.py 时保留）
├── images/           # 你的原图，按分类放入子目录
│   ├── landscape/    # 风光
│   ├── portrait/     # 人像
│   ├── animal/       # 动物
│   ├── still-life/   # 静物
│   └── street/       # 街拍
└── thumbs/           # 自动生成的缩略图（用于网页快速加载）
```

## 如何更新照片（自动扫描）

1. 在对应分类目录里**增、删或替换**照片，例如 `images/landscape/`。
2. 运行扫描脚本（任选其一）：
   - 双击 **`update.bat`**；或
   - 命令行执行 `python scan.py`
3. 刷新浏览器中的 `index.html`，照片即自动同步。

> 你只需要管 `images/` 目录，`thumbs/` 缩略图完全由脚本自动维护，不用手动碰。

脚本会自动：
- 扫描各分类目录下的图片；
- 读取 EXIF（相机型号 / ISO / 光圈 / 曝光时间 / 焦距）；
- 生成缩略图（最长边 1100px，加快网页加载，原图用于灯箱大图）；
- **删除照片后，自动清理 `thumbs/` 中对应的缩略图和 `captions.json` 中的失效标题**（不留孤儿文件）；
- 写出 `photos.js` 供网页读取。

> 部分经过后期导出的 JPG 可能已丢失 EXIF，此类照片网页上会显示「参数信息暂缺」。

## 自定义照片标题

标题默认按「分类 + 序号」自动生成（如 `风光 01`）。
如需自定义，编辑 **`captions.json`** 中对应文件的标题后重新运行 `scan.py`——
你的修改会被保留，新照片会自动补充默认标题。

## 环境要求

- Python 3.8+
- Pillow：`pip install Pillow`

## 本地预览

直接双击 `index.html` 即可（无需服务器）。照片数据通过 `photos.js` 以 `<script>` 方式加载，可在 `file://` 下正常工作。
