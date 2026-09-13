# Part-based character pipeline / 分件角色路线

Status: **architecture decision and local asset inspection, 2026-09-14**.
Segmentation, regional retexturing and cloth adapters below are proposed extensions;
this investigation exported an existing Studio asset and rendered diagnostics. It did
not submit paid generation, replace the dance character, or implement cloth physics.
See [the broader roadmap](technical-roadmap.md) and [current capabilities](reproducibility.md).

## 决策 / Decision

采用 **完整角色基准 → 共同空间中的部件 → 共享骨架 → 独立模拟代理**。
部件来源有两条可比较的路径：已有整体模型后分件；以及从统一 T pose 生成专用部件参考图，
分别建模，再按明确的比例、姿态与接缝约束组装。后者是项目方澄清后的方案，
应作为有约束的生成路线验证，不能简单等同于直接裁图后拼接。
两条路径均保留现有舞蹈工程作为外观与运动基准；尚未证明哪条在本角色上效果更好。

短期先验证 **脸部对齐 + 单一裙摆区域**。若这份分件模型的轮廓、花纹和连接处通过对照，
将其适配到现有骨架；若退化，只把它作为分区参考，继续从原模型拆出显示表面。
旧骨架与动作可以复用，顶点权重和代理绑定不能不加检查地跨模型复用。

```mermaid
flowchart TD
    P[One original photo / 一张原图] --> T[Reviewed T pose]
    T --> W[Whole-character reference / 全身比例基准]
    W --> S[Semantic parts in a common space / 共同坐标中的分件]
    S --> Q[Geometry, UV and seam inspection]
    Q --> R[One fitted skeleton / 一套校准骨架]
    Q --> F[Optional face texture repair or local generation]
    F --> A[Align and validate against whole character]
    A --> R
    R --> V[Preserved visible surfaces / 保留显示表面]
    R --> C[Body colliders and garment proxies]
    C --> B[Sequential physics bake]
    B --> V
    V --> D[Same-motion comparison and render]
```

## 当前模型的实际检查 / Observed asset

来源是用户确认的当前 Tripo Studio 分件页面；导出已有 GLB，未执行重生成。
导出文件、哈希、解析报告和 Blender 诊断图留在被忽略的私有运行目录中。

| 项目 | 观察 |
|---|---|
| 网格 / 材质 / 内嵌贴图 | 各 30 个 |
| 三角面 / 导出顶点 | 1,955,536 / 1,019,541 |
| 骨骼蒙皮 | glTF `skins` 为 0，尚未绑定 |
| 坐标 | 部件已处于共同坐标，导出没有保留网页的爆炸分开展示变换 |
| UV | 每个网格都有 UV；30 张 JPEG 贴图，分辨率从 128² 到 2048² |
| 脸部 | 独立部件，26,206 个三角面，对应贴图为 512² |
| 分件边界 | 分析时合并完全同坐标的顶点后，30 件仍都有开放边界 |
| 与旧舞蹈源模型比较 | 旧源为 1,922,921 面；两者原始坐标、顶点集合和贴图像素哈希不同 |

顶点对比以模型单位 `1e-6` 量化；两个文件没有相同的量化位置。这个结果只排除了
“按原坐标原封不动拆开旧源模型”的假设，**不证明发生了肉眼可见的细节损失**。
尚未完成两表面的配准距离测量；生成版本、缩放、重网格化或导出流程都可能造成差异。
贴图哈希不同也不能证明贴图损坏，分件裁切/重打包就会改变哈希。

导出菜单显示的 4K 设置不代表每一个部件都有一张 4K 贴图；局部裁切后的 512²
可能仍保持原始像素密度。要测脸部有效像素密度、投影清晰度和 UV 拉伸，不能只看文件尺寸。

开放边界可能是正常的领口、袖口、裙口或部件切口，并不都需要封口。
另有三个部件在完全同坐标合并的诊断中出现边被两个以上三角面共享，共四条；
重合的独立表面也可能触发此标记，尚未逐处判定，不能据此自动删除几何。
上述检查不构成完整的自交、内衬、隐藏身体或可模拟拓扑验收。

### 脸部错位：已定位到外观与几何的不一致

使用 Blender 5.2.1、同一静态导入模型和相机，分别渲染：

- 原材质加中性灯光；
- 去掉所有原贴图/材质细节的灰色素模；
- base color 接到 Emission，只看纹理外观，排除实时光照阴影。

素模上的鼻底、嘴唇与纯颜色中的对应位置不同；加灯光后出现两组五官轮廓。
**这份资产的问题在绑定与动作之前已经存在。** 尚不能判断错位究竟在生成、纹理投影、
分件或导出哪一步产生，也不能由一个样例推断所有 Tripo 模型必然如此。
关闭灯光只便于诊断，不能作为可重新打光的最终修复。

修复顺序：

1. 对照审核后的 T pose，分别判断几何五官和纹理五官哪个更接近目标。
   保存相同相机的素模、纯颜色、正常材质以及侧面视图。
2. 若几何可用，固定几何，尝试脸部局部纹理重投影/UV 变形，或局部重新贴图；
   以眼角、鼻翼、唇线定位，约束脸部边界，检查侧面拉伸和发际线接缝。
3. 若纹理更接近目标而几何明显错误，先局部拟合几何，再烘焙贴图；
   不把全部误差强行压进 UV，也不全局平移整张人脸纹理。
4. 前述方案不足时，才试高分辨率头部生成，并与全身基准对齐、处理脖颈与发际线。
   只把被验证更好的局部替换进去。一次换头仍不等于完成表情或口腔结构。

## 三条路线的取舍 / Alternatives

| 路线 | 收益 | 主要代价 | 决策 |
|---|---|---|---|
| 在现有舞蹈模型上划分衣服，保留显示表面 | 外观基准、骨架与动作最容易延续 | 需要处理粘连、服装面集、缺失的隐藏面 | 稳妥基线，也是候选失败时的回退 |
| 使用已有 30 件模型，适配同一骨架 | 脸/发/衣/鞋已有可编辑入口；无须立即重新生成 | 必须配准、重新转移权重；分件语义与物理结构不一致 | 优先做局部小样，达标再迁移 |
| T pose 裁成头、身体、腿鞋，独立生成三次或更多 | 可给局部更多生成与纹理预算，便于单独替换 | 独立尺度、比例、姿态、脖颈/袖口接缝、材质色差与重复/缺失表面 | 可选增强分支，先只试头部 |

上表最后一行记录最初理解。项目方随后明确：先以 T pose 为共同参考，调用图像编辑模型
生成各部位专用参考图，再逐张交给 Tripo 建模，组装后重新绑骨；细分到什么程度可以后定。
这个步骤可改善局部可见性和建模输入，具体设计见下节。

更多调用不自动带来更多真实细节。裁切能增加该区域在生成输入中的占比，不能从原图中
恢复本不存在的像素；超分辨率和补全会加入推断。三次生成也没有共享人体、关节或边界约束：
即使各自漂亮，头颈粗细、腿长、腰线、手臂方向与皮肤颜色仍可能不一致。

若以后试独立局部生成：保留完整角色作为尺度与轮廓基准；裁图带上邻接区域而非紧贴切断；
记录裁图到 T pose 的二维变换、局部到全身的三维变换、接缝地标与固定边界。
身体、手臂和手不能因为“三段式”名称而遗漏。优先选领口、袖口等遮挡处作为连接位置。
局部模型不单独自动绑成人形骨架，最终统一适配同一骨架。

## 专用部件参考图 → 独立建模 → 约束组装 / Regional-reference branch

Status: **proposed experiment, not executed**. The image editor is configurable.
The owner's label `image2.5` has not yet been resolved to a callable provider/model ID.
The current [Tripo image editing list](https://developers.tripo3d.ai/en/docs/generation-image-to-image)
does not list that exact identifier; verify the intended endpoint before execution,
without substituting another model or claiming that a call has been made.

这条路线的关键工作是建立组装约束，并在生成后测量、校正。图像编辑可以帮助统一外观和姿态，
但不能作为精确几何约束求解器；提示词、相同 seed 或相同画布都不保证 3D 接口一致。

### A. 先确定共同的尺子与静止姿态

- 以审核后的完整 T pose 保存头顶、下巴、肩、肘、腕、髋、膝、踝与鞋底等地标，
  按角色身高归一化。遮挡关节需要估计并标记置信度；不能把蓬裙轮廓当作髋关节宽度。
- 用现有全身模型或简易人体代理提供三维厚度、关节位置和统一相机假设；不必额外付费
  生成一个高精度全身模型。基准不是不可修改的真值，先审核其中明显错误的比例。
- 单张正面 T pose 不能给出真实的前后深度与米制身高。记录选择的尺度、投影模型与
  推断厚度；在共同空间中使用同一个身高与地面。
- 先定义用于测量的目标关节位置/轴向，正式蒙皮放在组装后。新部件围绕同一静止姿态
  对齐，再一起完成到 MMD neutral pose 的校准，不让各部分采用不同的 rest pose。

### B. 每张部件图保留共享参考和连接余量

首轮可以使用三组：头＋头发＋颈部；躯干＋衣服＋双臂/手；双腿＋袜鞋＋被衣服遮挡的
上端连接区域。各组保留相邻区域作为定位余量，连接区域由同一个基准定义。
生成分组不预先决定最后的语义分件、材料分区或物理网格。

每次部件图生成都参考同一完整 T pose，并提供该部位局部图或蒙版（具体接口支持待核实）。
明确保持角色左右差异、手掌朝向、腿部伸展、脚朝向、印花和邻接部位关系。
补全不可见表面是推断，需要检查；侧面或背面新视图也是推断，不能当额外观测。

分别保存两类产物：带框/地标的检查图与独立干净的建模输入。尺子、文字、骨架线、
拼图边框不送入 Tripo，避免被重建成几何或贴图。各张建模图可按部件提高占画面比例，
真实尺寸来自元数据，不能用它们各自的画布大小决定身体比例。

编辑生成可能改变构图与形状，因此原裁图矩阵只作为来源记录；生成后重新检测/审核
地标和轮廓。只有确认没发生非刚性变化时，才可继续使用原二维对应关系。
明显变脸、印花重绘、手掌翻面或关节位置偏离的图先修正，不直接送入三维付费阶段。

### C. 先统一比例，再修连接带

1. 以躯干为组装基准，或明确选定另一个根部件。将每个 GLB 的单位、朝向与对象变换
   转换到共同空间；独立生成的自动尺度只能作为初值。
2. 用部件三维地标与目标三维地标拟合旋转、平移和统一缩放。NumPy SVD 可实现加权
   相似变换；地标不能全重合或共线。二维目标只约束投影，深度需三维基准/先验。
3. 用同一相机检查头身比、肩宽、腰线、腿长与鞋底高度，再在语义对应的重叠区域细化。
   若使用 ICP，先有可靠初始对齐，并限制对应区域、法线与距离，避免把袖子吸到手臂或
   左腿匹配到右腿。禁止通过未检查的镜像变换交换左右服装。
4. 比例正确而接缝局部不吻合时，仅在颈根、腰部、袖口等连接带做平滑变形；
   面部、手型、鞋面和印花主体保持固定。Blender 网格/笼形变可先实现原型，
   必要时再增加带固定区的 Laplacian/ARAP 求解。
5. 若为了拼接必须明显拉长脸、压扁头发或扭曲整件衣服，判为候选不适配，回到局部图
   或基准校准阶段；不以接缝闭合掩盖比例与身份损失。

### D. 连接需要同时通过几何、外观和运动检查

| 接口类型 | 处理方式 |
|---|---|
| 连续皮肤，例如裸露脖颈 | 去掉重复的连接余量；建立对应边界环与过渡带，桥接/局部重拓扑，约束位置和表面切向；补齐该小区域 UV |
| 领口、袜口、鞋口等覆盖关系 | 可以保留独立对象；共享连接位置与合理重叠，保证动作时覆盖仍成立，避免重叠面闪烁 |
| 头发、衣服与身体 | 保持分层；用骨骼/固定区/代理附件连接，不为了合并对象而焊成同一表面 |

Blender 的 [Bridge Edge Loops](https://docs.blender.org/manual/en/3.6/modeling/meshes/editing/edge/bridge_edge_loops.html)
可用于已整理的边界环；[Shrinkwrap](https://docs.blender.org/manual/en/4.2/modeling/modifiers/deform/shrinkwrap.html)
可辅助连接带贴合。它们提供局部操作，不自动解决跨模型的语义对应与正确拓扑。
先用目标 Blender 版本验证小样；避免全身 voxel remesh 或全局重贴图破坏已经满意的细节。

皮肤接缝除位置连续，还需平滑的表面方向、颜色/粗糙度过渡与一致的变形权重。
把新过渡带烘焙到局部 UV；保留其余部件贴图。颜色校正只针对接缝对应区域，避免全局
调色改变衣服印花。各部件仍须分别通过素模/纯颜色/正常材质的脸部与细节检查。

组装后建立一套正式骨架并转移/修正权重；骨架结构可延用已验证版本，但关节位置重新拟合。
共用皮肤边界应焊接，或在重合点使用一致的相关骨骼权重；层叠衣物按各自附件规则处理。
随后测试转头、抬臂、弯肘、抬腿、屈膝、踝部旋转与深蹲。静态接上不代表动作不会裂开。
通过身体与连接验收后，才细分发束、衣片并建立物理代理。

### E. 保存可复用的组装契约

规划新增 `assembly` 字段组，和已有 `parts.json` 草案对应；不引入已实现命令的假象。

| 字段 | 用途 |
|---|---|
| reference image, camera, height, target joints | 全身参考、投影、尺度与共同静止姿态 |
| per-part reference provenance and landmarks | 图像编辑的来源、提示词/模型版本、输出地标及置信度 |
| region ownership and context-only masks | 该部件最终保留什么；哪些重叠区域只用于对齐 |
| attachment frames and target cross-sections | 接口中心、朝向、截面形状/尺寸；由全身基准定义 |
| source-to-canonical transform and local deformation | 每件的旋转/平移/尺度和连接带修正，可复现组装 |
| protected regions and seam topology/UV/weights | 防止细节被全局拉伸；记录接缝的几何、外观与运动约束 |
| measured errors and acceptance thresholds | 头身比、地标误差、接口缝隙、法线差、接缝颜色与动作裂缝；阈值按样例和输出分辨率校准 |

最小验证先覆盖一个真实接口：**头/颈与现有躯干**。走完“专用部件图 → Tripo →
比例拟合 → 接缝 → 同骨架运动”的链条，记录图像阶段与三维阶段的误差和人工时间。
若局部细节相对旧模型有收益，且连接区在转头/抬臂时保持稳定，再扩到三组独立生成。
这是一项新的装配路线试验，与上一轮固定几何的人脸贴图修复对照分别记录。

English: the clarified route edits dedicated regional references from the same T pose,
generates each regional mesh, assembles them under a shared scale/rest-pose/attachment
contract, and rigs the assembled character. Preserve overlapping context but assign
ownership before joining. Fit similarity transforms first, deform only seam bands,
and validate appearance plus motion continuity. A common image is useful conditioning,
not an exact 3D constraint. A head-to-torso pilot tests this branch before a full rebuild.

## 相关方法如何做 / Primary-source research

这些工作说明可借鉴的结构，不构成已经解决本项目复杂 cosplay、准确印花与舞蹈物理的证据。

| 方法 | 实际做法 | 对 CosMMD 的启发与限制 |
|---|---|---|
| [PartCrafter](https://arxiv.org/html/2506.05573v1) | 分部件潜变量结合局部/全局注意力，联合生成；所有部件处于同一个规范坐标空间 | “分部件生成”依靠共享上下文，不等于三次无约束独立调用；未在本角色上验证 |
| [HoloPart](https://github.com/VAST-AI-Research/HoloPart) | 从已有网格及粗分件出发，通过局部与上下文信息补全完整部件 | 区分几何切分与遮挡部分生成；补全可能改变可见形状，不能默认保留原 UV/花纹 |
| [Hunyuan3D-Part](https://github.com/Tencent-Hunyuan/Hunyuan3D-Part) | P3-SAM 从整体网格得到语义特征、分区和包围盒，X-Part 生成完整部件 | 保留全局空间约束再细化局部；公开实现并非本 Mac 上已验证的依赖 |
| [GALA](https://arxiv.org/html/2401.12979v1) | 从单层穿衣人体 3D 扫描出发，将多视图分割提升到表面，并在规范/姿态空间中补全分层几何与外观 | 与现有穿衣网格拆层更接近；输入是 3D 扫描，不能直接当单张照片方案。作者也报告宽松裙装换姿态的腿间伪影，未解决布料动力学 |
| [JIFF](https://arxiv.org/abs/2204.10549) | 用对齐的人脸三维先验与二维图像特征细化全身重建中的脸部 | 局部脸部预算应结合几何/外观对齐；单纯裁大脸图不保证五官对齐 |

我们的工程判断是：**分层/局部细化值得做，但保留全局约束与显示表面比一次拆成多少件更关键**。
不把这些研究的结果拼接成未经验证的质量承诺，也不在本阶段安装新的重型推理环境。

## Tripo API 中可以接入什么 / Provider adapters

核查日期：2026-09-14。以下均是 API 契约调查，CosMMD 当前还没有 `segment` 或 `retexture` CLI。

- **已有模型后分件：** `POST /v3/mesh/segment` 接受任务、上传模型或 URL。
  `v2.0-20260430` Beta 支持语义分件；提供 `ref_image` 时，粒度和连通性拆分参数会被忽略。
  优先测试“已有带贴图整体模型 → 分件”，并验证外观保持。
  [官方分件文档](https://developers.tripo3d.ai/en/docs/mesh-segment)。
- **直接生成 parts 有参数冲突：** 当前生成路径启用 texture/PBR，而 `generate_parts: true`
  要求 `texture: false`、`pbr: false`，也不能同时依赖 quad/smart-low-poly。
  因此不能给现有请求加一个布尔值就声称支持带纹理分件生成。
  [官方 image-to-model 文档](https://developers.tripo3d.ai/en/docs/generation-image-to-model/standard)。
- **局部重新贴图：** `POST /v3/models/texture` 提供 `part_names`（先前分件任务的部件名）
  和 `texture_alignment: geometry`；默认 `original_image` 更偏向原图颜色。
  可用它设计“固定几何，仅脸部”的对照任务，但应先确认上传模型能否保留所需分件标识。
  对比前后几何哈希、五官位置、肤色、接缝和参考相似度；优先几何对齐不保证同时保住肖像细节。
  [官方 texture 文档](https://developers.tripo3d.ai/en/docs/models-texture)。

本地 UV/投影修正使用 Blender Python，必要时配合 OpenCV，保留无需新增付费服务的路径。
API 调用预算记录为完整角色生成、分件、纹理、局部生成、失败重试分别记账，
费用使用实际任务返回与当时计费规则；不把文档响应中的示例 credits 当报价。

## 布料需要的分组，与网页分件不同

建议建立如下语义角色；一个角色可以对应多个显示对象，并不强制合并它们的 UV：

- **头/脸**：跟随头骨；人脸纹理与几何对齐独立验收。
- **头发**：发根约束到头，长发用少量成束代理或骨链；保留卷发显示细节，先检查肩部碰撞。
- **上身、袖子**：按紧身/宽松结构设置约束；需要时单独处理袖子物理。
- **裙身、外层衣摆、装饰**：根据真实连接关系分组；印花边界不是缝合线。
  多块显示网格可以由一张连续裙摆代理驱动，或对应实际连接的衣片代理。
- **腿、袜子、鞋**：默认跟随身体/脚部骨架；袜子色带按同一衣物管理，不作为各自飘动的环。
- **隐藏身体与内衬**：只为碰撞和必要可见区域补齐；标记为推断，避免改动已满意的鞋和外轮廓。

约 196 万面的显示表面不直接用于 Cloth。先制作裙腰固定、拓扑可用且维持蓬裙体积的轻量代理，
再把位移传到原表面。显示分件数、材质数、物理代理数和骨骼数是四个不同的量。
具体代理顺序、碰撞、缓存与黑帧验收沿用 [技术路线](technical-roadmap.md)。

## 让以后更换生成策略不牵动下游 / Stable interface

新增的 `parts.json` 应描述统一的中间资产，而不是依赖某个供应商的零件编号。
以下是字段规划，**不是已经实现或被 CLI 读取的格式**：

| 字段组 | 保存内容 |
|---|---|
| `canonical` | 单位、朝向、全身比例基准、统一静止姿态、参考模型哈希 |
| `source` | 输入图片/裁图哈希、来源任务、生成策略、源到统一空间变换 |
| `parts` | 稳定语义 ID、显示对象、材料/UV、源面映射（存在时）、表面保持策略 |
| `attachments` | 连接部件、共同边界、固定区、接缝地标、刚性/骨骼/模拟驱动类型 |
| `assembly` | 专用部件图、目标比例与姿态、接口坐标框架/截面、对齐变换、连接带及验收误差 |
| `rig` | 同一骨架版本、关节拟合、权重来源、归一化与独立肢体验证 |
| `simulation` | 代理、碰撞器、绑定静止帧、支撑结构、缓存依赖 |
| `evidence` | 对照渲染、原始/推断/人工修改区域、成本、耗时、未解决问题 |

生成策略可以从整体后分件换成约束下的局部生成，但后续只读取这个统一契约。
拓扑或静止形状改变会使权重对应、代理绑定和相关物理缓存失效；只改颜色通常只使渲染失效。
始终保留版本化源文件，不覆盖当前已验证工程。

## 已有资产路线的最小试验 / Existing-asset experiment

以下验证现有资产的修复与布料适配。上节的专用部件图/组装试验独立记录，
不要求先证明所有贴图修复手段失败，才允许评价局部生成的收益。

1. **脸部固定几何对照。** 以当前静态诊断为基线，尝试一次可回退的局部对齐修正。
   先判断是否必须重建头；通过条件是五官与参考、几何一致，无侧面/发际线新缺陷。
2. **一个裙摆区域。** 从已分件候选建立物理语义分组，与旧模型同姿态、同机位比较。
   通过后才转移这一区域所需的骨架约束、补碰撞器并建立代理。
3. **短动作验收，再完整 12 秒。** 静止、单腿抬起、转身验证固定区、裙型与穿插；
   连续烘焙后再跑原 12 秒片段。比较所有展示帧与近景，确认贴图、鞋、手没有无关变化。
4. **按证据迁移。** 候选通过后适配其余部件；失败则保留旧表面，复用分区经验。
   若现有脸部修复不足，可采用局部生成替换；专用部件图路线则先独立验证头颈接口，
   再依据细节收益、组装稳定性和修正成本决定是否扩到全身三组生成。

## English brief

Use a whole-character anchor, semantic parts, one fitted rig, optional regional
refinement and separate simulation proxies. The inspected Studio export has 30
textured meshes, 1,955,536 triangles and no skin. It is not a coordinate-preserving
split of the old dance source; that finding alone does not establish visible loss.
The face's geometry and base-color features disagree in static diagnostic renders,
so rigging cannot fix this artifact. Diagnose and align them before regenerating a head.

Test the existing segmented asset on the face and one skirt region before migrating
the character. Retain the current dance as the baseline. Regional image editing followed
by head/body/leg generation may improve the modeling inputs, but scale, seams and rest
pose still require an explicit assembly contract. Keep this branch behind the common
part interface and first test a head-to-torso joint.
Semantic parts are not physical panels: merge sock-band roles and use appropriately
connected skirt proxies without discarding the detailed visible surface or its UVs.
The proposed adapters, shared schema and cloth pipeline remain unimplemented.
