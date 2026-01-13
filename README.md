# FIUP - File Incremental Update Protocol

**让 AI 修改代码不再抓狂的补丁协议**

[English](#english) | [中文](#中文)

---

## 中文

### 为什么需要 FIUP？

当你让 ChatGPT/Claude 修改代码时，是否遇到过这些问题：

- 🤯 AI 给出的行号完全对不上
- 📋 不得不手动复制粘贴一大段代码
- 🔄 AI 输出完整文件，浪费 token 还容易遗漏
- 😵 用 `git apply` 应用 diff 总是失败

**根本原因**：LLM 处理的是 token 流，无法准确计算行号。

**FIUP 的解决方案**：用**唯一文本锚点**代替行号定位，让 AI "看到什么写什么"。

### 快速开始

```bash
# 克隆仓库
git clone https://github.com/Thankyou-Cheems/FIUP.git
cd FIUP

# 直接使用（无需安装依赖）
python fiup_tool.py apply patch.fiup -t ./your_project

# 或从剪贴板应用（需要 pyperclip）
pip install pyperclip
python fiup_tool.py -c -t ./your_project
```

### 使用流程

#### 1. 让 AI 输出 FIUP 格式

在对话中告诉 AI：

```
修改代码时，使用 FIUP 格式输出，用唯一代码锚点定位（禁止行号），锚点3-6行确保唯一性。
```

或上传 `FIUP_PROTOCOL.md` 作为上下文。

#### 2. AI 输出示例

```
<<<FIUP_PATCH file="main.py">>>
[OPERATION]: REPLACE

[ANCHOR]:
```anchor
def hello():
    print("Hello")
    return None
```

[CONTENT]:
```content
def hello(name: str = "World"):
    """Say hello to someone."""
    print(f"Hello, {name}!")
    return {"greeted": name}
```
<<<END_FIUP_PATCH>>>
```

#### 3. 应用补丁

```bash
# 预览变更
python fiup_tool.py preview patch.fiup -t ./project

# 应用（自动备份）
python fiup_tool.py apply patch.fiup -t ./project

# 从剪贴板直接应用
python fiup_tool.py -c -t ./project

# 出错了？一键恢复
python fiup_tool.py undo -t ./project
```

### 命令速查

| 命令 | 说明 |
|:---|:---|
| `fiup apply <patch> -t <dir>` | 应用补丁 |
| `fiup preview <patch> -t <dir>` | 预览变更（详细 diff） |
| `fiup validate <patch>` | 验证补丁格式 |
| `fiup extract <file> -o out.fiup` | 从 AI 对话中提取补丁 |
| `fiup undo -t <dir>` | 从最近备份恢复 |
| `fiup undo -t <dir> --list` | 列出所有备份 |
| `fiup -c -t <dir>` | 从剪贴板应用 |

### 操作类型

| 操作 | 用途 | 锚点 | 内容 |
|:---|:---|:---|:---|
| `REPLACE` | 替换代码 | 旧代码 | 新代码 |
| `INSERT_AFTER` | 在锚点后插入 | 定位点（保留） | 新增代码 |
| `INSERT_BEFORE` | 在锚点前插入 | 定位点（保留） | 新增代码 |
| `DELETE` | 删除代码 | 要删除的代码 | 省略 |

### 文件说明

```
FIUP/
├── fiup_tool.py        # 主工具（Python 3.10+）
├── FIUP_PROTOCOL.md    # 协议文档（给 AI 看）
├── FIUP_PROMPTS.md     # 提示词模板
└── README.md
```

### 常见问题

**Q: 锚点找不到怎么办？**

工具会显示最相似的代码片段，检查是否：
- 文件已被修改
- AI 产生了"幻觉"
- 缩进不一致

**Q: 锚点匹配到多处？**

让 AI 扩展锚点，包含更多上下文（如函数签名、注释）。

**Q: 支持哪些语言？**

所有文本文件都支持，与语言无关。

---

## English

### Why FIUP?

Problems when asking AI to modify code:

- 🤯 Line numbers are always wrong
- 📋 Manual copy-paste of large code blocks
- 🔄 AI outputs entire files, wasting tokens
- 😵 `git apply` fails on AI-generated diffs

**Root cause**: LLMs process token streams, not line-numbered files.

**FIUP solution**: Use **unique text anchors** instead of line numbers.

### Quick Start

```bash
git clone https://github.com/Thankyou-Cheems/FIUP.git
cd FIUP

# Apply patch
python fiup_tool.py apply patch.fiup -t ./your_project

# From clipboard
pip install pyperclip
python fiup_tool.py -c -t ./your_project
```

### Usage

#### 1. Instruct AI to use FIUP

```
Output code changes in FIUP format: use unique 3-6 line code anchors (no line numbers).
```

Or upload `FIUP_PROTOCOL.md` as context.

#### 2. Apply the patch

```bash
# Preview
python fiup_tool.py preview patch.fiup -t ./project

# Apply
python fiup_tool.py apply patch.fiup -t ./project

# Undo if needed
python fiup_tool.py undo -t ./project
```

### Commands

| Command | Description |
|:---|:---|
| `apply <patch> -t <dir>` | Apply patch |
| `preview <patch> -t <dir>` | Preview changes |
| `validate <patch>` | Validate format |
| `extract <file>` | Extract patches from AI chat |
| `undo -t <dir>` | Restore from backup |
| `-c -t <dir>` | Apply from clipboard |

### Operations

| Op | Anchor | Content |
|:---|:---|:---|
| `REPLACE` | Old code | New code |
| `INSERT_AFTER` | Code before insertion (kept) | New code |
| `INSERT_BEFORE` | Code after insertion (kept) | New code |
| `DELETE` | Code to delete | Omit |

---

## License

[MIT](LICENSE) - Use freely, keep the copyright notice.

## Contributing

Issues and PRs welcome!

## Credits

Inspired by the pain of AI-assisted coding. 🤖💔➡️😊
