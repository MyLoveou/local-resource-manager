# 36 · 技术：CLIP 在本仓的两种用法

> 来源：分类建议的向量兜底、AI 新词的同义映射。同一份模型，一个编码图片，一个编码文本。

## 存储格式

```sql
-- ai_vectors
resource_id, model_id, dim, vector BLOB
```

读写都用原始 float32：

```python
np.frombuffer(bytes(row), dtype="<f4").astype("float32")
```

向量在写入时已归一化，所以**点积即余弦**：

```python
matrix = np.stack(vectors)
scores = matrix @ matrix[target_pos]
```

`dim` 必须校验：换了模型维度会变，长度不一致的向量要跳过，否则矩阵拼接直接抛错。

## 用法一：图→图（向量近邻）

分类兜底就是用它：

```python
scores = matrix @ matrix[pos]
for neighbour in np.argsort(-scores):
    if similarity < 0.82: break        # 低于门槛不投票
    for cid, _ in categories_of(neighbour):
        weighted[cid] += similarity     # 越像票越重
    if taken >= 8: break
```

两个参数是可调的经验值：**邻居数 8、相似度 0.82**。太低会引入噪声票，太高在冷启动（库里图少）时永远不触发。

## 用法二：文→文（标签同义）

`runtime.encode_text([...])` 可以把标签名编码成同一空间的向量，于是「AI 说的猫耳」和「你的兽耳」可以算相似度：

```python
match = closest_vocabulary_tag(vector, vocabulary)   # 门槛 0.86
if match: item["similar_to"] = match[0]
```

文本侧门槛比图像侧高（0.86 vs 0.82）：标签是短词，随便两个词都可能有中等相似度，放宽会乱配。

## 缓存与降级

- 词表向量做**进程级缓存**（`_vocab_vectors`），打标/删标签时失效
- 模型缺失、未安装、加载失败 → 返回空字典，**调用方退回纯列表**，不抛错

```python
try:
    vectors = await asyncio.to_thread(runtime.encode_text, names)
except Exception:
    return {}          # 降级：没有模型也能用，只是没有归并
```

编码是 CPU 密集操作，必须 `asyncio.to_thread`，否则会卡住整个事件循环（单进程单循环，`/health` 也会跟着卡）。

## 教训

1. 一个模型两种编码，**分别解决"找相似图"和"归一近义词"**，不要为后者的需求引入第二个模型。
2. 阈值要按数据类型分别定：图-图可以松，词-词必须紧。
3. 任何依赖模型的功能都要有"模型不在"的路径，且默认降级而不是报错。
4. 向量计算放线程里；这个仓有过「async 里同步 IO 拖垮 /health」的先例。
