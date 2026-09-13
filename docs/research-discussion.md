# Research discussion archive / 论文讨论存档

Status: **parked at the project owner's request, 2026-09-14**.
This is a record of a design discussion, not a paper, novelty claim, benchmark or
publication plan. Development has returned to [parts and cloth](part-pipeline.md).

## 讨论经过

1. 最初的问题是：从一张场景 cosplay 照片，到在近似原场景中跳舞的 3D 角色，
   若主要组合已有技术，是否可能形成 conference paper？初步判断是完整演示有展示价值，
   但工具集成与画面冲击力本身不足以证明研究贡献。
2. 当时列举 LHM、DeClotH、Dress-1-to-3 作为相关工作。项目方指出：普通人体或简单服装
   的成功案例不能证明复杂 cosplay 的问题已解决；关心的是脸和装饰细节、印花位置、
   蓬裙结构，以及运动中的稳定性，而不只是生成一个能动的人体。
3. 修正后的判断：不能用“相近任务已有工作”来否定更高保真目标；也不能仅凭项目演示
   宣称现有方法都无法处理 cosplay。项目方对 LHM 细节/抖动的评价是定性观察，
   本项目还没有相同输入、动作与预算下的直接实验。
4. 讨论收敛到一个可能的问题：复杂服装的可辨识细节能否在分层、绑定与运动后被保留？
   候选方向包括语义分件、附件约束、外观保持修复、局部增强和失败诊断。
   单独使用低模布料代理驱动高模是已有技术，不能直接作为创新点。
5. 原场景还原仍是单图条件下的近似重建；不可见表面、绝对尺度和真实材质/灯光不能
   被当作已测得的 ground truth。场景和衣服问题需要分别评估。
6. **当前决定：暂停论文路线，只记录讨论，先改善真实角色与布料效果。**

## 当时核对过的限制

- [Dress-1-to-3](https://arxiv.org/html/2502.03449v2) 的限制讨论涉及多层衣服融合、
  初始结构以外的新衣片、高频几何过平滑与纹理差距。这支持认真评估复杂服装，
  但不是“该方法完全无法生成纹理”的证据。
- [DeClotH](https://arxiv.org/html/2503.19373v1) 补充材料 S6 讨论模板表达能力与穿插等限制。
  它包含纹理优化，不能将其简化成“只有基本布料、完全不能重构纹理”。
- 这些来源的局限，以及项目方的观察，均不能代替在本案例上的公平对照。
  当前演示仍有裙腿穿插和头发变形，尚无动力学验证。

## 若将来恢复研究，需要补充什么

- 明确算法/表示/优化目标上的贡献，区分供应商生成质量和我们新增模块的贡献。
- 以相同初始角色模型比较后续处理方法，同时报告独立端到端结果，避免混淆来源。
- 多种复杂服装、固定输入信息、匹配的人工/时间预算、消融、失败案例与可重复结果。
- 分别评估肖像、印花与饰品保持、轮廓、接缝、穿插、时间稳定性和人工修正成本。
- 保留原始输入与推断区域的区别；公开数据前另行核对实际授权和资源许可。

尚未证明新颖性、性能优势或可发表性；未开展论文撰写、数据集构建或投稿。

## English record

We discussed whether a single cosplay photograph could lead to a paper about an
animated character in an approximately reconstructed original scene. The initial
integration-focused assessment was revised after the owner challenged the relevance
of ordinary-human and simple-garment examples to ornate cosplay. Detailed appearance,
structured garments and motion stability deserve explicit evaluation; related tasks
do not establish that this quality target is solved.

The earlier blanket characterization of texture limitations was too broad: the cited
methods do model appearance, while reporting specific structural and reconstruction
limits. No matched comparison has been run here. Preserve these distinctions if the
research question is resumed. Paper work is paused; the current priority is a reliable,
appearance-preserving parts and cloth pipeline.
