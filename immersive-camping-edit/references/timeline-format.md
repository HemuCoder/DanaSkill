# 可复现时间线格式

用 `scripts/render.py` 将明确选择的片段渲染为 SDR H.264/AAC MP4。JSON 是可编辑、可复现的剪辑清单；它不是剪映、Premiere 或 Resolve 原生工程。复杂调色、J/L cut、独立环境声铺底、交叉叠化和关键帧裁切应在支持这些功能的工具里完成，并保留工程与出入点记录。

## 调用

```bash
python "$SKILL_DIR/scripts/render.py" timeline.json --output outputs/episode.mp4 --check
python "$SKILL_DIR/scripts/render.py" timeline.json --output outputs/episode.mp4 --work work/render
```

`--check` 校验字段、素材、源时间区间和 FFmpeg 能力，不渲染。默认寻找 `FFMPEG_BIN`、PATH 中的完整 FFmpeg、当前 Python 的 `imageio-ffmpeg`；也可用 `--ffmpeg /absolute/path/to/ffmpeg` 指定。输出文件及同名 `.render.json` 必须尚不存在。

## 最小样例

```json
{
  "version": 1,
  "sources": {
    "setup": "../raw/搭桌子.mov",
    "enjoy": "../raw/坐下休息.mov",
    "song": "../music/用户提供的音乐.wav"
  },
  "output": {"width": 1440, "height": 1080, "fps": 30},
  "clips": [
    {
      "source": "setup", "in": 12.4, "out": 19.6,
      "fit": "contain", "gain_db": 0,
      "caption": {"text": "桌子搭好了", "style": "diary", "position": "bottom"}
    },
    {"black": true, "duration": 0.5},
    {
      "source": "enjoy", "in": 4, "out": 12,
      "fade_in": 0.3, "fade_out": 0.5
    }
  ],
  "music": [
    {
      "source": "song", "in": 0, "out": 7,
      "at": 8.7, "gain_db": -18, "fade_in": 0.5, "fade_out": 1
    }
  ]
}
```

样例仅展示结构；先从真实素材里验证出入点和字幕内容。可不提供 `music`。所有未列出的字段都会报错，避免忽略尚未实现的效果。

## 字段

顶层必填 `version`、`sources`、`output`、`clips`；可选 `music`。`version` 固定为整数 `1`。

- `sources` 是 ID 到文件路径的映射。相对路径以 JSON 所在目录为基准；可使用绝对路径。列出实际使用的素材。原文件保持只读。
- `output.width/height` 是 16–7680 范围内的偶数；`fps` 支持 `30` 或 `"30000/1001"` 等帧率，范围 1–120。遵守用户指定的画幅，默认参考画幅 4:3；根据源清晰度选择输出分辨率。
- `output.font` 可指定支持中文的字体文件。相对路径同样以 JSON 所在目录为基准；未指定时寻找系统黑体或 Noto CJK。缺少字体时明确失败。
- `clips` 按成片顺序排列，至少一段。视频段必填 `source/in/out`；黑场段必填 `black: true` 和正数 `duration`。
- `in/out` 单位为秒，区间左闭右开。视频片段以该源视频流的播放起点为零；音乐以源音频流的播放起点为零。不要把文件中的绝对 PTS 当作出入点。非零起始 PTS 会被换算，源内音视频起点差通过补静音保持。
- 视频段的 `speed` 默认 `1`，支持 `0.125–8`；镜头时长为 `(out-in)/speed`，再量化到成片帧数。使用 `atempo` 同步变速音频并保持音高，极端变速仍需听审。需要移除该段原声时显式设 `mute: true`。
- 视频段的 `gain_db` 默认 `0`，允许 `-96–24` dB。它调整原声；不自动根据“声音类型”删掉声音。
- `fit` 默认 `contain`，完整保留画面并留黑边；`cover` 填满并裁切。视频段可设 `crop_x`，范围 `0–1`、默认 `0.5`，在 `cover` 时按 `(iw-ow)*crop_x` 定位水平裁切窗口，`0/0.5/1` 分别为左/中/右对齐，垂直居中。这是逐镜静态构图；使用前后均需检查手、器具与动作结果是否保留。需要动态重构图时另用关键帧工具。
- `fade_in/fade_out` 单位是成片秒数，同时作用于该段画面和原声，包含已叠字幕。淡变区间不能重叠。每段原声另有首尾各 10ms 的音频淡化，短于 20ms 的片段缩短为半段时长，以降低切音边缘的不连续；它不改变画面，也不代替相邻镜头交叉混音或听审。黑场可放在两个完整动作段之间。
- `caption` 支持 `text`、`position`、`style`；默认底部 `bottom`、日记 `diary`。位置可为 `top/center/bottom`，样式可为 `diary/label`。日记字幕白字深色半透明底，标签白字透明底。最多自动换行 3 行。文字在整个片段出现，若需局部出现，将连续源区间拆成相邻片段。
- `music` 是可选数组。每段必填 `source/in/out/at/gain_db`；`at` 是成片入点，其他时间单位均为秒，可选音频 `fade_in/fade_out`。音乐必须完全落在成片内；不会自动循环或自动选曲。只有显式列出的音源被混入。

## 颜色、方向和音轨

当前渲染器用于已确认的 SDR BT.709、方形像素素材。另支持原色/传递函数/矩阵元数据精确为 `[1,11,1]` 的 IEC61966-2-4 素材，逐镜缩放后使用完整 `colorspace` 转换到 BT.709：`ispace=bt709:iprimaries=bt709:itrc=iec61966-2-4:irange=tv:space=bt709:primaries=bt709:trc=bt709:range=tv:format=yuv420p:fast=0`。该路径按有限范围输入处理，使用前核对来源和样片。转换会改变像素，不只改标签。

其他已标明非 BT.709 的颜色、HDR、宽色域、旋转/镜像矩阵和非方形像素仍会报错。先明确进行方向转换、色彩转换或 HDR→SDR 映射，另存预处理素材并在清单中保留原文件映射，再渲染。

未标色彩的素材允许进入基础渲染，但必须先由操作者检查摄影来源与画面；未知元数据不代表已确认 BT.709。渲染报告记录原元数据供复核。不要把 LUT 名称、相机或伽马曲线猜成事实。

每段音频统一为 48 kHz 双声道，无音轨源补静音。原声和显式音乐按给定增益相加。最终混音有 0.95 线性幅度峰值保护，保留原有音量，不自动归一化到某个 LUFS。此保护不是编码后 true peak 保证；AAC 导出仍需量测与听审。

## 输出与复核

每次在 `--work` 内建立唯一 `camping-render-*` 目录，保存片段、字幕 PNG 和 FFmpeg 日志。失败保留这些诊断文件；只清理该次目录。不会改写原素材或已有输出。

成功输出 MP4 和同名 `.render.json`，后者记录时间线与两份渲染脚本 SHA-256、源路径和元数据、应用的色彩转换与源列表、期望/实际时长、耗时与工作目录。画面采用 Lanczos 缩放和 H.264 CRF18/fast，复杂滤镜和视频编码各使用 2 线程。片段量化可能与小数秒请求相差不到一帧。把该 JSON 与源文件相对路径、字幕信息一起交付，才能重新渲染。

脚本只确认技术渲染和基本时长，不评价镜头选择。完成后按 `review.md` 检查动作衔接、裁切、字幕、声音和章节；能直接听审时实际听审，能力不足时如实标记。
