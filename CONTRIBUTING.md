# Contributing / 参与贡献

Small, reproducible improvements are welcome: better anatomy calibration, garment
separation, safer retries, meaningful QA, or clearer examples. Include a before/after
comparison and the exact software versions when reporting a Blender issue.

```sh
python -m pip install -e .
python -m unittest discover -s tests -v
git add src tests docs
cosmmd audit .
```

Keep models, source motion, textures, audio, `.blend` scenes, API responses and
credentials in an ignored local run directory. A baked action inside a scene is
still motion data. Do not attach it to an issue unless its license permits that
distribution. Link to the author's download page instead.

Presentation images require an explicit entry in `docs/media/manifest.json`,
including SHA-256 and a rights/provenance note. Updating a hash is not a substitute
for reviewing the content. CI scans the Git index and history; also inspect staged
files before the first push, since a failing public CI job cannot undo disclosure.
When replacing approved media, keep each reviewed historical hash in that entry's
`previous_sha256` list and explain the old/new roles. Never allow unknown old hashes
just to silence the history audit.

欢迎提交可复现的改进，尤其是骨骼校准、头发/裙摆绑定、原型保留与逐帧检查。
请提供软件版本和对比图。原始模型、动作、音频及包含动作的工程仅保存在本地；
GitHub 中引用原作者链接。提交前运行测试和 `cosmmd audit .`。

After replacing an embedded image, update its README URL version query and check the
live page. GitHub/raw image caches can temporarily display the previous composition.
