# Credits, rights and publication / 致谢、授权与发布边界

## Code and documentation

Original CosMMD code and documentation are MIT licensed. Tripo, Blender and MMD Tools
are independent projects; this repository is not an official product or endorsement
from those teams. MMD Tools is an external GPL-3.0 dependency, installed separately;
its implementation, bundled reference models and sample assets are not vendored.

## Showcase

The repository owner authorized publication of the displayed input reference and
rendered workflow examples. The demonstration is non-monetized. That authorization
is not a general license to redistribute the character, the source motion or any
other creator's work. `docs/media/` is excluded from the code license; its rights
remain with the respective owners. Ask the relevant rights holders before reuse.
The media manifest records exact reviewed files and their provenance. The current
original room photo was supplied and authorized for the input panel by the owner;
the existing prepared T-pose reference is shown as an intermediate. This does not
license incidental characters, artwork or brands visible in the room. The original
T-pose API task trace is not part of the evidence; see [provenance](reproducibility.md).

| Contribution | Credit and original source |
|---|---|
| Motion — 君色に染まる | つん · https://www.nicovideo.jp/watch/sm28422307 |
| Motion download | https://bowlroll.net/file/96407 |
| Choreography | 足太ぺんた · https://www.nicovideo.jp/watch/sm27753880 |
| Original song | TOKOTOKO（西沢さんP） · https://www.nicovideo.jp/watch/sm27529228 |
| Motion terms | https://privatter.net/p/7867947 |
| Image preparation workflow | Nano Banana Pro via [Tripo image-to-image API](https://developers.tripo3d.ai/en/docs/generation-image-to-image) |
| 3D generation | https://www.tripo3d.ai/ |
| Rendering and rigging | https://www.blender.org/ |
| Motion importer | https://github.com/MMD-Blender/blender_mmd_tools |

The showcase owner confirmed permission for use of this motion in Blender. The
online terms were accessible and checked on 2026-09-13. They restrict redistribution
of original or modified motion data and monetary/commercial uses; other-tool usage
requires consultation. Each future user must obtain whatever permission their own
use needs. Links are supplied instead of rehosting source files or access passwords.
No song audio is included in the GIF.

## What must stay out of Git

Source VMD/VPD/PMX/PMD, motion archives, FBX/GLB/OBJ exports, `.blend` scenes/backups,
baked action curves in any format, original texture maps, audio, signed asset URLs,
provider responses, account identifiers, keys, local logs and unreviewed images.
Changing the extension or putting these inside a JSON/ZIP does not make them public.

`.gitignore` excludes common formats and working directories. `cosmmd audit` checks
staged bytes, content signatures, secret patterns, media hashes and Git history.
It is a focused guard, not a proof that every possible copyrighted or sensitive
payload can be recognized automatically. Human review remains necessary.

## 中文

代码与原创文档使用 MIT；展示媒体和第三方素材不因此获得 MIT 授权。
原作者的动作、编舞、音乐均在上表注明来源。用户已确认取得 Blender 使用许可；
后续使用者仍需满足自己的用途所需的许可。演示不带音乐、不收费、不附打赏或广告。
仓库只保留经过审核的展示图片/GIF，绝不上传 VMD、模型、工程、烘焙动作数据、
贴图、音频、密钥或私有日志。请到作者原始链接下载动作并阅读条款。
