# 测试：每集封面与字幕

> 每条一行，可在实现后逐条勾选；自动化项标注命令。

## 字幕发现

- [ ] 同目录 `xx.ass` 被识别 → 单元：`pytest tests/test_subtitles.py -k discover`
- [ ] `Subs/`、`字幕/` 子目录被扫描到 → 单元：同上 `-k subdir`
- [ ] `.srt/.vtt/.ass/.ssa` 四种后缀都识别 → 单元：`-k suffix`
- [ ] 非字幕后缀（`.txt`、`.mkv`）不误识别 → 单元：`-k ignore`

## 字幕匹配

- [ ] 集号相同则命中（视频 03 + 字幕 03）→ 单元：`-k episode_number`
- [ ] 无集号但主干相似（≥0.8）→ 单元：`-k similarity`
- [ ] 相似度不足不挂载（宁缺勿错）→ 单元：`-k no_match`
- [ ] 单视频资源无匹配字幕时挂资源级 → 单元：`-k resource_level`

## 字幕接口

- [ ] 列表按集分组，`renderable` 对 srt/vtt 为真、ass/ssa 为假 → 接口
- [ ] 新增字幕复制进库并建关联，重复调用幂等 → 接口
- [ ] 删除只解关联，不删文件 → 接口
- [ ] 返回的 `url` 带签名（`exp`/`sig`）→ 接口

## 每集封面

- [ ] 有 ffmpeg：抽帧成功并回填 `cover_file_id` → 单元 + 手工 A7
- [ ] 无 ffmpeg：返回 None，导入不失败 → 单元（mock 无二进制）
- [ ] 抽帧失败（坏文件）：同样回退 → 单元
- [ ] 列表接口 `coverUrl` 无封面时指向作品封面 → 接口
- [ ] 手动换封面持久化 → 手工 A9

## 播放器（手工）

- [ ] A2：srt 字幕可选中且中文正常 → 手工
- [ ] A3：vtt 字幕可选中 → 手工
- [ ] A4：ass 字幕标注不支持，选择后明确提示 → 手工
- [ ] A5：无字幕的集没有字幕入口 → 手工
- [ ] A6：单文件视频可选同名字幕 → 手工

## 回归

- [ ] A10：删除一集后 `subtitle_tracks` 与封面引用无孤儿 → 单元（`-k cascade`）
- [ ] `pytest apps/backend/tests` 全绿
- [ ] `pnpm --filter desktop typecheck && lint && build` 通过
- [ ] `pnpm check:file-size` 不超过基线（InfoPanel 已拆分后仍在基线内）
