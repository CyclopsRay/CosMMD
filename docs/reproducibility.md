# Provenance and reproducibility / 来源与可复现性

## What was actually demonstrated

The showcase character was generated in Tripo Studio, then exported as both a
high-resolution source GLB and a rigged GLB. The API could not query that Studio
asset ID. The Blender workflow reused these exports; it did not regenerate the
character through the newly packaged API adapter.

The README now starts with the original posed room photo supplied by the owner on
2026-09-14. The previous first-panel image is retained as the **prepared T-pose
intermediate** actually used for the existing model. This corrects the distinction
between the user's input and the modeling image.

The packaged route now includes Nano Banana Pro T-pose preparation through Tripo
v3. The prior T-pose image is reused; an archived API task record establishing its
exact original image-generation route is not included in the local evidence. This
update did not regenerate that image or the model using the new command. Its API
payload, download validation and task-resume behavior were tested offline.
Future `prepare` runs record input/output hashes, model, prompt and task ID privately.

A face close-up was available as a visual reference during development. The packaged
workflow does not require it and does not submit a second user image. We have not
measured how much that extra visual reference affected the original manual judgments.

The character needed mesh inspection, local separation of fused leg interiors,
missing hidden thigh surfaces, joint placement, weight corrections and a calibrated
neutral pose. It is not a zero-touch reconstruction benchmark. The included fixed
reference-character coordinates are not a general landmark detector.

## Verified environment and outputs

- Blender 5.2.1 LTS, Apple Silicon / Metal; external MMD Tools 4.5.14 during import.
- Native Blender armature: 104 bones, including 30 finger bones; packed textures.
- Source motion: 5,856 frames at 30 fps; the showcased interval is source frames 301–660.
- Display GIF: samples 301, 303, …, 659, 180 images across 12 seconds, at approximately 15 fps.
- These public demo frames are freshly rendered at 720×720, 64 samples, one Blender
  process per frame. The standalone GIF is 512×512; the 1440×792 three-stage hero uses a 552×552 dance panel.
- No audio. Camera and small hair/skirt follow-through are locally authored/baked.
- Original full-motion checks found no unweighted vertices, invalid native drivers,
  non-finite bone transforms or reversed knee bends. Excess IK error after accounting
  for leg reach was below 0.001 m. This describes the fitted demo, not other characters.
- The API adapter uses documented v3 contracts and mock lifecycle tests. No new paid
  API generation was performed to validate the open-source release.

## What a new user can reproduce

The CLI plan, task lifecycle tests, staged-file audit and synthetic QA tests run
without an API key or licensed assets. A paid generation run needs a valid Tripo API
key and enough provider credits. A new character needs its own calibrated profile.
A motion import needs a licensed motion and separately installed MMD Tools.
The reference recipe can be adapted to matching source geometry; source models and
motions are intentionally not distributed, so the showcase is not a self-contained
asset benchmark.

## 中文

这次演示复用了 Tripo Studio 的原始/绑定 GLB；网页资产 ID 不能直接当 API 任务 ID。
新的 v3 API 客户端做了离线契约测试，没有为了开源发布再次付费生成角色。
首页第一张图已改为用户于 2026-09-14 提供的原始照片；此前的 T pose 移到中间步骤，
它是现有模型实际使用的建模图片。新流程加入 Tripo API 的 Nano Banana Pro 预处理，
但这次没有重新生成 T pose 或模型。已有 T pose 的原始 API 任务链未被归档验证；
新增调用路径做的是离线契约与恢复测试。原开发过程另有面部特写用于视觉参考，其影响未做控制实验。
因此请把它理解为可复用的 agent 工作流与真实案例，而非“所有图片全自动成功”的证明。

公开仓库不提供有版权限制的模型、动作及包含动作的工程。要复现你自己的结果，
需要自行取得这些输入并完成本角色的骨骼校准。运行单元测试、审核工具和示例计划
不需要 API 付费，也不需要下载动作文件。
