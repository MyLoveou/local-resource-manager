# Mermaid 语法对照

官方：[时序图](https://mermaid.js.org/syntax/sequenceDiagram.html) · [流程图](https://mermaid.js.org/syntax/flowchart.html)。版本差异以所用渲染器为准。

## 时序图箭头

| 写法 | 含义 |
|------|------|
| `->>` | 实线箭头，同步请求 |
| `-->>` | 虚线箭头，响应 |
| `-)` | 实线开口箭头，异步 |
| `--)` | 虚线开口箭头，异步响应 |
| `-x` | 实线叉，失败或销毁类信号 |
| `->` | 实线无箭头，少用 |

半箭头、双向箭头（`<<->>`，v11+）默认不用，除非图意依赖它们。

## 时序图块

```text
sequenceDiagram
    actor U as 用户
    participant S as 服务
    autonumber
    U->>+S: 请求
    alt 条件 A
        S-->>-U: 结果 A
    else 条件 B
        S-->>-U: 结果 B
    end
    opt 可选步骤
        U->>S: 补充
    end
    loop 直到停止条件
        U->>S: 重试
    end
    break 不可恢复
        S-->>U: 错误
    end
```

- `Note right of S: 说明` 或 `Note over U,S: 说明`
- `box rgb(200,220,240) 分组名` … `end`。不要写 `#rrggbb`
- 临时参与者：`create participant X` 在它收到的第一条消息之前；`destroy` 紧跟销毁它的那条消息
- 消息里要出现分号时写成 `#59;`

## 流程图形状

| 写法 | 用于 |
|------|------|
| `A[步骤]` | 动作 |
| `A{判断?}` | 分支 |
| `A([开始])` | 起止 |
| `A[(库)]` | 数据存储 |
| `A[/输入/]` | 输入或输出 |

```text
flowchart TD
    A([开始]) --> B[校验]
    B --> C{通过?}
    C -->|是| D[保存]
    C -->|否| E[返回错误]
```

节点 id 用字母或下划线。显示文字里的括号、引号用引号包住：`A["保存(草稿)"]`。
