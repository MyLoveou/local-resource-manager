# 15 · 踩坑：Python 文件里未注释的中文段落报语法错误

## 现象

`import app.main` 报：

```
SyntaxError: invalid character '，' (U+FF0C)
```

## 根因

`__init__.py` 里写了**没有 `#` 注释前缀的中文段落**：

```python
# 抓取应用 · 接口适配层

FastAPI 路由，面向 UI/外部契约。薄层：解析请求 → ...   # ❌ 这行没有 #，被当代码解析
```

`FastAPI 路由，...` 不是合法 Python 语句，全角标点触发 `invalid character`。

## 修复

- 每行都加 `#`，或删掉多行描述只留一行注释：

```python
# 抓取应用 · 接口适配层（路由）
```

## 教训

1. Python 包级说明文字在 `__init__.py` 里**要么写 docstring、要么每行 `#`**。
2. 批量创建目录时容易踩——写完统一 `python -c "import ..."` 验证一次。
3. 报错指向全角标点（`，` `：` `）`）时，基本就是"未注释的 prose 被当代码"。

## 扩展阅读

### 站内（本仓）

- [14-踩坑-中文乱码误判](14-踩坑-中文乱码误判.md)
- [25-后端分层与数据访问](25-后端分层与数据访问.md)

### 站外知识

- [Python · Unicode 指南](https://docs.python.org/3/howto/unicode.html)
