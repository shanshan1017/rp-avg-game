# Visual Style Bible

适用项目：`心动失控夜` 及后续同画风互动视频项目。

## Style Lock

```text
Original anime cinematic 2.5D illustration, first-person player POV, urban Friday night romantic comedy thriller, polished animated film lighting, clean line art, expressive character acting, 16:9 composition, no male protagonist visible, no UI, no subtitles, no watermark.
```

## Negative Lock

```text
photorealistic, live action, real human face, celebrity likeness, public figure likeness, existing IP character, copyrighted character, explicit adult content, male protagonist visible, male face, male body, male back view, male mirror reflection, male shadow silhouette, male hand close-up, ID photo, social avatar, UI buttons, subtitles, logo, watermark
```

## Visual Direction

- 原创二次元 / 2.5D 动画电影质感。
- 都市周五夜晚，恋爱轻喜剧混合轻悬疑。
- 光线以夜色、霓虹、便利店暖光、写字楼冷白灯、雨后反光为主。
- 镜头是玩家第一视角，女生可以靠近镜头、递物、挡路、直视镜头。
- 前端负责 UI、字幕和选择按钮，画面素材内不要生成文字和按钮。
- 角色脸部尽量放在中上安全区，避免被底部选择框遮挡。

## First-Person Camera Rules

- 摄像机代表男主视角。
- 不出现男主脸、身体、背影、倒影、影子、手部特写或社交头像。
- 必要互动用镜头运动、女生递物、物品落在桌面、手机屏幕边缘等方式表达。
- 不用过强的手持抖动，保持视觉小说式可读性。

## Continuity Rules

- 同一角色跨节点保持发型、发色、眼型、服装主色和标志物。
- 同一地点跨节点保持灯光温度和空间材质。
- Poster 是视频首帧逻辑，不能和视频开头风格断裂。
- 视频结尾要留出 0.5-1 秒相对稳定画面，方便前端弹选择。

## Prompt Assembly

每个图片或视频 prompt 按以下顺序组合：

1. `Style Lock`
2. 节点镜头目标
3. 出镜角色的一致性锚点
4. 8-15 秒 shot plan
5. 音效/台词提示
6. `Negative Lock`

多角色节点额外添加：

```text
Use the approved character references for all visible characters. Keep hairstyle, outfit color family, facial features, age impression, signature accessories, and silhouette consistent with the reference sheets.
```
