# Image Curve Digitizer

[中文](#中文说明) · [English](#english)

## 中文说明

`image-curve-digitizer` 是一个可复用的 Codex Skill，用于把论文、仪器软件截图或扫描图中的可见曲线与散点近似还原为校准后的 XY 数据，并生成带可编辑样图的 Excel 工作簿。

### 主要功能

- 从 BMP、PNG、JPG 等栅格图像中提取连续曲线。
- 从点阵图、散点图中识别可见标记中心，保留不规则 X 间距。
- 分别处理黑、红、绿、蓝、青、品红和黄色数据系列。
- 支持线性坐标与对数坐标。
- 识别矩形绘图区，必要时允许手动输入像素边界。
- 支持坐标轴倍率校准，例如 `1E-1`、`1E-4`。
- 支持排除图例、彩色文字和注释区域，减少误识别。
- 输出校准后的 CSV、像素审计列和 JSON 元数据。
- 配合 Codex 的 Spreadsheets Skill 创建 Excel 数据表和可编辑 XY 图。
- 报告单像素对应的坐标分辨率，明确图像提取的不确定性。

### 两种提取模式

| 模式 | 适用图像 | 输出特点 |
|---|---|---|
| `curve` | 连续 LSV、光谱、动力学曲线等 | 按像素列或指定 X 步长输出连续 XY 数据 |
| `points` | 散点图、点阵图、实验点叠加拟合线 | 输出检测到的可见标记中心，不自动连线或补点 |

### 在 Codex 中安装

把仓库克隆到 Codex Skills 目录：

```powershell
git clone https://github.com/huangziyi498-sudo/image-curve-digitizer.git "$HOME/.codex/skills/image-curve-digitizer"
```

重新打开 Codex 会话后，可以直接调用：

```text
使用 $image-curve-digitizer 提取这张图里的红色曲线，并生成带样图的 Excel 文件。
```

散点图示例：

```text
使用 $image-curve-digitizer 分别提取图中的黑色、红色、蓝色和品红色散点，排除图例和拟合线，并生成 Excel 散点图。
```

### 命令行脚本

依赖 Python 3、NumPy 和 Pillow。

```powershell
python -m pip install -r requirements.txt
```

连续曲线：

```powershell
python scripts/digitize_curve.py plot.bmp `
  --mode curve `
  --output extracted.csv `
  --metadata extracted.json `
  --x-left-value -0.8 --x-right-value 0.8 `
  --y-top-value 0.0002 --y-bottom-value -0.0001 `
  --x-step 0.005 --curve-color red
```

离散散点：

```powershell
python scripts/digitize_curve.py scatter.png `
  --mode points `
  --output red_points.csv `
  --metadata red_points.json `
  --x-left-value 60 --x-right-value 110 `
  --y-top-value 1 --y-bottom-value 0 `
  --curve-color red `
  --exclude-region 350,20,780,220
```

### 输出内容

- 校准后的 X、Y 数值；
- 原始 `pixel_x`、`pixel_y`，便于复核；
- 散点模式下的局部标记评分；
- 图像尺寸、绘图区边界、坐标端点、颜色和检测参数；
- 单像素对应的 X/Y 数值范围；
- 通过 Codex 工作流生成的 Excel 数据表与样图。

### 精度边界

图像数字化无法无损恢复作图软件的原始数据。线宽、抗锯齿、压缩、截图缩放和散点重叠都会产生误差。散点模式只提取可见中心；被完全遮挡的点无法重建。请把输出视为图像近似值，而不是原始实验记录。

## English

`image-curve-digitizer` is a reusable Codex Skill for recovering approximate calibrated XY data from visible curves or scatter markers in raster plot images. It can then guide Codex to build an Excel workbook containing the extracted data, calibration details, and an editable sample chart.

### Highlights

- Continuous-curve and discrete-marker extraction modes.
- Linear and logarithmic axis calibration.
- Named color-family selection and multi-series workflows.
- Plot-frame auto-detection with explicit pixel-bound overrides.
- Legend and annotation exclusion regions for scatter plots.
- CSV data plus JSON calibration metadata and pixel-resolution estimates.
- Excel-ready output and editable XY chart guidance.
- No automatic synthesis of hidden points, extra experimental series, or physical-model results.

### Limitations

Raster digitization is approximate. Line thickness, antialiasing, compression, resizing, and overlapping markers limit recoverable precision. The tool reports visible pixel-derived positions; it does not recreate unavailable raw measurements.

## License

MIT License. See [LICENSE](LICENSE).
