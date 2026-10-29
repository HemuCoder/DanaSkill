# 剪映调色技术研究存档

来源：重构前提交 `4cae607`。以下为历史任务记录，保留测试条件、未完成检查及原任务路径；这些路径和参数仅用于追溯。当前能力边界见 [调色执行文档](../../immersive-camping-edit/references/color-grade.md#本机验证边界)。


Mac 剪映专业版 11.6.0 已通过官方 FCPXML 导入验证剪辑结构、裁切和原声音量。颜色路径分别记录如下，后续根据目标版本的新证据更新。

- **FCPXML ColorBoard 表达**：本次三镜小样导入成功；第二镜设置全去饱和后，在 `00:00:02:13` 检查时画面仍有颜色，片段“调整”未勾选。该次 ColorBoard 表达未透传；其他 FCPXML 颜色表达、LUT、锐化等属性仍待分别验证。
- **仅颜色关键帧的旧候选**：三镜工程成功打开，`enable_adjust=true` 对应“调整”已勾选，`KFTypeSaturation=-1` 在面板显示 `-50` 并出现关键帧菱形标记，但画面仍有颜色。该候选只通过界面数值读回，不能作为有效效果绑定或滑块映射。手工亮度 `20` 能使画面变亮，官方保存的调节预设可读取 `adjust` 参数；预设本身的绑定另行验证。
- **早期原生效果材料探针**：按上节模板、bundle 路径及片段引用绑定，在独立三镜小样中使用同一 `C1379` 的源区间 `53–55` 秒，每镜两秒。第二镜 `saturation=-1` 为灰度，第三镜 `brightness=0.4` 变亮；保存、退出并重开后两者画面均保持。选中第三片段后原生基础面板读回亮度 `20`，控件呈可用外观。该探针确认两个测试点；正式工程的后续应用如下。
- **v5 技术历史**：83 个视频片段、498 个六类效果材料已通过写入与保存重开，首片段锐化面板读回 `4`。用户认为视觉上仍是微调；该结果保留为绑定能力证据，后续风格力度按新反馈校准。
- **v6 当前检查范围**：在用户确认剪辑未改的交付基线上，已向主工程的 83 个视频片段配置 747 个独立原生效果材料，类型为 `brightness/saturation/contrast/temperature/tone/sharpen/shadow/highlight/clear`，逐片引用并启用调整，无额外调节轨道；保留 12 条字幕、651.12 秒与 4:3 画幅。已检查日照、阴影、手部肤色、逆光、夜景全景、食物、橙灯、清晨八个代表帧，静态独立复核无明显异常，内部判断比 v5 更清透，用户风格审核待完成。主工程已保存、退出并重新打开；C1370 九项原生面板再次读回亮度 `11`、饱和度 `−8`、对比度 `2`、色温 `8`、色调 `3`、锐化 `8`、阴影 `11`、高光 `−9`、清晰度 `10`，日间实际画面保持。重开后 `187.24` 秒手部同帧仍为调色后状态，面板读回亮度 `6`、饱和度 `−5`、高光 `−7`、阴影 `6`。保存快照已通过 ZIP 完整性检查，主工程留在剪映供用户审核。GUI 手工改值保存、所有镜头面板与完整参数范围未全面验证；本轮未进行 v6 导出、连续全片播放或听审。此方案与 FFmpeg 成片并非逐像素等价。
- **人工修改后回读与回写**：用户保存后的最新草稿为编码内容，当前正式回读入口尚未打通，修改后回写也未验证。此缺口限制后续修订；首次原生草稿参数写入按上一项独立验证。

v6 视觉证据见 [三列同帧对比](assets/color-grade-v6-comparison.jpg) 和 [八组代表画面](assets/color-grade-v6-scenes.jpg)：当前候选、待用户审核，本期数值和素材不作通用预设。

本期实验记录在原任务的 `work/clip-grade-import-probe/research/`：生成脚本 `test_material_binding.py`、完整候选 `material-binding/candidate.json`、结论与范围 `material-binding/result.json` 和 `evidence.md`；重开画面及亮度面板在 `material-binding/captures/` 的 `saturation-reopened.png`、`brightness-reopened.png`、`native-panel-reopened.png`。该实验目录和测试工程身份只用于追溯；新任务按实际安装包和目标工程生成路径与 ID。

v5 历史工程记录在原任务的 `work/jianying-integration/native-color/`，交付在 `outputs/惠州露营1024/原生调色_v5/`。v6 当前记录在 `work/native-color-v6/`：`install/main-v6-saved.zip` 为保存后完整快照，`captures/reopened/day-panel-{basic,tonal,color}.jpg`、`day.jpg` 与 `hands.jpg` 为重开后的面板和画面。当前交付及最终验证记录在 `outputs/惠州露营1024/韩系清透调色_v6/validation.json` 及同目录文件。数量、参数及位置均属本期证据。

本机 `lyra-cli` 内嵌帮助列出了按 segment ID 调色、创建独立调节层及设置区间的命令；当前 Codex shell 实际调用 `--help` 返回 `unauthorized host process`。内部能力存在不等于当前会话具备正式调用入口。保留该边界，后续使用目标版本实际可用、授权且经验证的接口，不伪造宿主或绕过授权。

用户要求独立调节轨道时，另行验证其批量生成、作用范围、实际效果和保存重开；该可选能力的状态与默认原生片段参数分开记录。

## 早期画面

[v3 画面记录](assets/color-grade-reference.jpg) 保留为历史记录。用户曾认为 v5 视觉变化仍然偏轻；当时 v6 的风格审核尚未完成。
