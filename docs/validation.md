# Release validation / 发布验证

The release was checked locally with Python 3.12 and Blender 5.2.1. No new paid
Tripo task was submitted during packaging.

- Nano Banana Pro preparation tests check the selected API model/template, one-task
  resume after a failed download, input-change rejection, and decoded-image validation
  with unauthenticated asset downloads. No new paid image task was submitted.
- Unit tests cover ambiguous paid requests, resumed task reuse, a black character
  on a valid background, missing/corrupt frames, staged-versus-working-tree secrets,
  forbidden binary signatures and exact media hashes.
- The skill passes the creator's frontmatter validation and its own metadata/local-link tests.
- The source-preserving case stages were rerun against local source/rigged GLB exports.
  The resulting 104-bone scene was checked across all 5,856 motion frames: no unweighted vertices, non-finite transforms, reversed knee bends or invalid drivers; a new pose render was visually reviewed. Imported motion and scene outputs remain private. Blender workers use
  `--python-exit-code 1` so a Python traceback cannot be mistaken for success.
- All 180 public demo source frames were decoded/scanned and all three contact sheets
  reviewed. The previous silhouette interval is visible and correctly shaded.
- The new three-panel hero uses the owner's original photo, the existing prepared
  T pose, and the same verified dance frames. No dance poses were regenerated.
- Both compressed GIFs were reopened: each has 180 frames and exactly 12,000 ms duration.
- Staged content and reachable Git history are audited before publication. CI repeats
  the checks on source changes; it is not a replacement for the pre-push review.

On this Mac, an editable-install `.pth` file inherited a hidden flag and Python skipped it. Ordinary `pip install .` was used to verify the packaged entry point. Development installations can use `PYTHONPATH=src` if this local condition applies.

Known limits and provenance are documented in [reproducibility](reproducibility.md).
Visual checks do not establish perfect cloth, hair, anatomy, likeness or native PMX support.

中文：代码、技能和演示都做了实际检查。API 部分使用离线契约测试，没有新增付费任务；
绑定配方用已有本地资产重跑。GIF 覆盖完整 12 秒，原黑影区间未删帧或换成相邻姿势。
素材和密钥检查在首次推送前执行，模型、动作和工程始终留在本地。
