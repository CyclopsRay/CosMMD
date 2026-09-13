# Fitted reference-character recipe

This directory preserves the successful source-preserving workflow from the showcase.
It is **one character's calibration profile**, not a universal preset. Source coordinates,
cut planes, sleeve masks, hair/skirt selections and finger joints must be fitted again
for a different generated mesh. Do not apply it blindly to another Tripo output.

All scripts use the local `COSMMD_RUN` directory. They retain the original imported
source and save stage-specific copies. No assets, API responses, motion keys or
third-party reference-model coordinates are stored here. `feet.json` contains our
fitted ankle/control transforms, not animation data.

Stages:

1. Put your matching source GLB at `source.glb` and auto-rig GLB at `rigged.glb` under a
   private run directory. Set `COSMMD_RUN` to its absolute path.
2. `import_sources.py`: import and pack originals; extract the base-color image locally.
3. `prepare_base.py`: create a lighter weight carrier and hair/skirt controls. Original
   high-resolution source remains intact for the next transfer.
4. `prepare_controls.py`: establish MMD names and foot/toe controls.
5. `restore_surface.py`: transfer weights to the original surface, split verified fused
   inner legs, cap/round only new interior surfaces, and fill missing hidden thighs.
6. `fit_rig.py`: actual joint pivots, 30 fitted finger bones, graph-smoothed hand weights,
   neutral arm calibration and a preferred-bend knee solver. Saves `work/Calibrated_Rig.blend`.
7. Use `src/cosmmd/blender/import_motion.py` on that calibrated file, with
   `work/mmd_mapping_v3.json`, armature `Rig`, and a locally licensed VMD. Save
   `work/Motion_Raw.blend`. Check/restore constant preferred calf bends if the imported
   motion overwrote them; do not discard genuine knee animation.
8. `finish_motion.py`: foot contact, bounded hair/skirt follow-through, following camera
   and editable `output/Dance.blend`.
9. Independently validate limbs, fingers, all animation frames and rendering before delivery.

Run a stage using:

```sh
blender --factory-startup -b --python-exit-code 1 --python recipes/reference_character/fit_rig.py
```

The main package contains the reusable operations. These scripts retain compact numeric
case masks so the original repair decisions remain inspectable. Refactor a repeated
operation into the package when a second character demonstrates the abstraction.

中文：这是展示角色的具体校准配方，不是所有人物都能直接使用的通用模板。
不要把坐标、切面和头发/裙摆范围硬套到新模型。每一步保留前一版，只有确认缺失或
粘连的内侧才补面；手、鞋、袜子的原外表面和 UV 优先保留。动作文件始终由用户本地提供。
