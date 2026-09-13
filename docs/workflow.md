# From one image to MMD / 从一张图到 MMD

## Inputs and outputs

Character input: one full-body JPEG/PNG, preferably a clear T/A pose with visible
hands and shoes. Credential: `TRIPO_API_KEY` in the environment. Do not put it in a
prompt saved to the repository. Blender and Python are tools, not extra image inputs.
A licensed motion is a separate reusable animation asset. No extra face image is required.

Outputs stay local: original GLB, auto-rig GLB, calibrated blank rig, animated blend,
PNG masters, video/GIF and validation reports. Keep a pristine source copy.
The public repository contains tools and a rendered demonstration, not these assets.

| Stage | Action | Exit condition |
|---|---|---|
| 1. Generate/reuse | Tripo image task + rig-check + rig, or locally exported Studio assets | Saved task IDs, source and rigged GLB downloaded |
| 2. Inspect | Materials, UVs, connected components, side identity, real fingers | Front/side/oblique views and topology agree |
| 3. Preserve | Transfer proxy weights onto the original high-resolution surface | Original outer coordinates/UVs unchanged |
| 4. Calibrate | Fit shoulder/elbow/wrist/hip/knee/ankle; articulate fingers | Independent limb and finger tests pass |
| 5. Retarget | Match MMD neutral pose and bone names; import VMD | Valid action, correct IK toggles, full motion range |
| 6. Finish | Correct foot contact, stage/camera, restrained secondary motion | Reach-aware IK and scene checks pass |
| 7. Render | Fresh process per frame; keep source PNGs | Correct count/dimensions; every-frame QA and visual review |
| 8. Share | Encode, decode-check, credit, audit staged files and history | Only reviewed media/code enters Git |

## 1. API generation

```sh
cosmmd generate --image private/reference.png --run private/character
cosmmd generate --image private/reference.png --run private/character --execute
```

The first command is a plan. The second submits tasks and can use credits. Read
current provider pricing before executing. Generation and rigging are separate
submissions. No automatic purchase, top-up, regeneration or fall-back paid model is performed.
Rerunning the same command reuses saved task IDs. If a POST timed out before returning
an ID, `tasks.json` records `pending_or_unknown`: recover the existing task from the
provider console rather than submitting again. If a crashed process leaves a lock,
verify that process has ended before removing the lock. Do not run the same directory concurrently.

Current provider documentation: [image generation](https://developers.tripo3d.ai/en/docs/generation-image-to-model/standard),
[file upload](https://developers.tripo3d.ai/en/docs/files),
[rig check](https://developers.tripo3d.ai/en/docs/animations-rig-check),
[rigging](https://developers.tripo3d.ai/en/docs/animations-rig),
[task query](https://developers.tripo3d.ai/en/docs/task-query).
The adapter uses v3 consistently; the original exploration used v2 and Studio exports.

## 2. Inspect before repairing

```sh
cosmmd inspect --blender /path/to/blender --source private/character/rigged.glb   --output private/character/inspection.json --save private/character/imported.blend
```

Look at the actual source mesh, not just the auto-rig. Vertex duplication at UV seams
can inflate connected-component counts; counts alone do not establish whether a hand
is fused. Check side identity anatomically, not from the viewer's left/right.
Use multiple close-up views for fingers, cuff jewelry, knee pivots, heels and soles.

## 3. Preserve and calibrate

Use `cosmmd.blender.rig_ops` inside Blender for weight transfer, finger chains,
weight-only smoothing, neutral-pose baking and knee constraints. Run it on copies.
The `recipes/reference_character/` directory records the complete fitted showcase
recipe. Its coordinates are a case profile: adapt them after inspecting another
character. It is not the default for arbitrary Tripo outputs.

For every repaired joint, identify its position inside the mesh. Keep the original
hand mesh if finger geometry exists. Add three bones per finger; the MMD thumb normally
uses indices 0–2, the other fingers 1–3. Skin, cuff ornaments and sleeves need distinct
weight selections. Graph smoothing should not jump across gaps between fingers.

Only split joined surfaces after proving the connection. Preserve UV/material data,
cap newly exposed interiors, recalculate normals and inspect the caps in several poses.
A dressed surface model may lack hidden thighs; splitting cannot reveal geometry that
was never generated. Limit any new geometry to that missing region.

Bake the target MMD neutral pose into both mesh and rest bones before importing relative
rotations. Merely renaming a T-pose skeleton leaves incorrect arm axes.
Use a knee hinge aligned to the actual local bend axis. A preferred bend prevents a
straight-leg singularity, but its magnitude is model-specific. The showcase needed
25 degrees; that is a tested starting point for this case, not a universal setting.

## 4. Import a licensed motion

Install [MMD Tools](https://github.com/MMD-Blender/blender_mmd_tools) separately.
The author data is neither vendored nor downloaded by this project. A source checkout of MMD Tools may need its OpenCC dependency in Blender; install it locally and pass `--python-deps /path/to/dependencies` when required. Do not vendor those dependencies into this repository.
Provide a JSON mapping of Japanese MMD bone names to the fitted armature names.
`examples/mmd_mapping.json` demonstrates the Tripo-style names used in the case study.

```sh
blender --factory-startup -b --python-exit-code 1 --python src/cosmmd/blender/import_motion.py --   --scene private/character/calibrated.blend   --motion private/motion/dance.vmd --mapping examples/mmd_mapping.json   --addon /path/to/blender_mmd_tools --armature Rig   --output private/character/animated.blend --scale 0.0825 --rights-confirmed
```

The scale above is the showcase's 1.65 m / 20 MMD-unit convention; calculate it for
your model. `--rights-confirmed` records the operator's authorization; it does not
grant rights. Existing permission is reusable within its actual scope.

Check the imported action range and all finger channels. Convert add-on IK toggle
paths to native properties if delivering without the add-on. An imported identity
calf track can overwrite the preferred bend; only replace it after verifying that
it is constant and that IK remains enabled. Do not erase genuine knee animation.

## 5. Verify the movement

Test each leg independently and check that the other side does not follow it.
Check elbow pivot stability, open hands, a fist, and each finger independently.
Evaluate every animation frame for finite bone transforms, reversed knee flexion
and invalid drivers. Count unweighted vertices. Report raw IK error separately from
error beyond bone reach: unreachable motion targets are not all solver defects.

A reusable all-frame check is included (the knee option assumes a calibrated local-X hinge):

```sh
blender --factory-startup -b --python-exit-code 1 --python src/cosmmd/blender/verify_scene.py -- \
  --scene private/character/animated.blend --armature Rig \
  --report private/character/scene-validation.json \
  --knee L_Thigh L_Calf --knee R_Thigh R_Calf
```

For representative poses, evaluate deformed vertices in world space and check the
floor and camera bounds. Foot placement must account for the actual sole/heel,
not only the ankle bone. Hair/skirt bone following is secondary animation, not cloth
physics. Say so. Review large lifts, crouches and turns visually.

## 6. Render and review

```sh
cosmmd render --blender /path/to/blender --scene private/character/animated.blend   --output private/character/frames --start 301 --count 180 --step 2   --size 720 --samples 64 --device CPU
cosmmd qa private/character/frames --expected 180 --step 2   --report private/character/qa.json --contact-sheets private/character/contacts
python -m cosmmd.gif --reference private/reference.png   --frames private/character/frames --output private/character/showcase --fps 15
```

For Apple Silicon use `--device METAL` after a small render check. The fresh-process
path is slower than retaining the renderer across frames but avoids the state reuse
that correlated with black artifacts in the original run. The exact engine subsystem
was not isolated; this is a verified workaround, not an upstream bug diagnosis.

Review every contact sheet, detailed hand/shoe close-ups, flagged frames and the actual
encoded output. Dark-pixel thresholds are heuristics and require interpretation for
dark costumes/backgrounds. File size, resolution and frame count cannot certify image quality.
If encoding already graded PNGs in Blender VSE, use Standard/None/exposure 0 to avoid
applying AgX twice. Keep the original motion's 30 fps; choose output sampling separately.

## 中文要点

角色输入只有一张全身图；Tripo 密钥负责 API 调用，动作是另外取得许可的资源。
顺序是：生成或复用模型 → 检查网格 → 保留原表面 → 校准关节与手指 → 导入动作 →
检查脚底/镜头/穿插 → 逐帧渲染与核验 → 审核后公开展示。

不要凭单张侧视图判定手指粘连，不要因为自动绑定差就重建原本完整的手和鞋。
T pose 到 MMD 参考姿势需要同时校准网格和骨骼。左右按角色身体定义；膝盖旋转轴、
手肘位置、鞋底高度都必须从本模型测量。裙内缺失表面需要局部补齐，已有表面优先保留。

先检查原始 PNG，再判断视频黑块来源。复现时不要改模型与渲染设置两件事后就下结论；
先以相同模型和设置重新载入渲染。每一帧都应扫描，联系表全部检查，最终编码文件也要实际播放。
