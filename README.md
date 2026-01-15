# FIUP - File Incremental Update Protocol v3.0

**让 AI 修改代码不再抓狂的补丁协议**

[English](#english) | [中文](#中文) | [在线工具](https://thankyou-cheems.github.io/FIUP/)

---

## 中文

### 为什么需要 FIUP？

当你让 ChatGPT/Claude 修改代码时，是否遇到过这些问题：

- 🤯 AI 给出的行号完全对不上
- 📋 不得不手动复制粘贴一大段代码
- 🔄 AI 输出完整文件，浪费 token 还容易遗漏
- 😵 用 `git apply` 应用 diff 总是失败
- 💔 **Web 聊天界面把缩进空格吞掉了**

**根本原因**：LLM 处理的是 token 流，无法准确计算行号；Web 界面会压缩多余空格。

**FIUP v3.0 的解决方案**：
1. 用**唯一文本锚点**代替行号定位
2. 用**可见字符 `→`** 代替空格缩进（不怕被 Web 吞掉）
3. 用 **` ```fiup ` 代码块**包裹（双重保险）

### 快速开始

```bash
# 克隆仓库
git clone https://github.com/Thankyou-Cheems/FIUP.git
cd FIUP

# 直接使用（无需安装依赖）
python fiup.py apply patch.fiup -t ./your_project

# 或从剪贴板应用（需要 pyperclip）
pip install pyperclip
python fiup.py -c -t ./your_project

# 或使用在线工具（无需安装）
# https://thankyou-cheems.github.io/FIUP/
```

### 使用流程

#### 1. 让 AI 输出 FIUP 格式

在对话中告诉 AI：

```
修改代码时请使用 FIUP v3.0 格式：
- 用 <<<FIUP>>> 和 <<<END>>> 包裹
- 用 → 表示缩进（→ = 4空格）
- 锚点 3-6 行确保唯一性
```

或上传 `FIUP.md` 协议文档作为上下文。

#### 2. AI 输出示例

````
```fiup
<<<FIUP>>>
[FILE]: src/main.py
[OP]: REPLACE
[ANCHOR]
def hello():
→print("Hello")
→return None
[CONTENT]
def hello(name: str = "World"):
→"""Say hello to someone."""
→print(f"Hello, {name}!")
→return {"greeted": name}
<<<END>>>
```
````

**缩进规则**：`→` = 4 空格，`→→` = 8 空格，以此类推。不需要计数，直接视觉映射。

#### 3. 应用补丁

```bash
# 预览变更
python fiup.py preview patch.fiup -t ./project

# 应用（自动备份）
python fiup.py apply patch.fiup -t ./project

# 从剪贴板直接应用
python fiup.py -c -t ./project

# 出错了？一键恢复
python fiup.py undo -t ./project
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
| `fiup diff <file1> <file2>` | 比较两个文件 |

### 操作类型

| 操作 | 用途 | ANCHOR | CONTENT |
|:---|:---|:---|:---|
| `REPLACE` | 替换代码 | 旧代码 | 新代码 |
| `INSERT_AFTER` | 在锚点后插入 | 定位点（保留） | 新增代码 |
| `INSERT_BEFORE` | 在锚点前插入 | 定位点（保留） | 新增代码 |
| `DELETE` | 删除代码 | 要删除的代码 | 省略 |
| `CREATE` | 新建文件 | 省略 | 完整文件内容 |

### v3.0 格式说明

```
```fiup                    ← 外层代码块（可选但推荐）
<<<FIUP>>>                 ← 补丁开始
[FILE]: path/to/file.py    ← 文件路径
[OP]: REPLACE              ← 操作类型
[ANCHOR]                   ← 锚点区域开始
def old_func():
→pass                      ← → 表示缩进
[CONTENT]                  ← 内容区域开始
def new_func():
→return True
<<<END>>>                  ← 补丁结束
```                        ← 外层代码块结束
```

### 为什么用 `→` 表示缩进？

| 问题 | 传统方案 | FIUP v3.0 |
|:---|:---|:---|
| Web 界面吞空格 | ❌ 缩进丢失 | ✅ `→` 可见不丢失 |
| Markdown 嵌套 | ❌ 解析混乱 | ✅ 单层代码块 |
| LLM 计数错误 | ❌ `\|2\|` 需要计算 | ✅ `→→` 直接映射 |

### 文件说明

```
FIUP/
├── fiup.py           # 命令行工具（Python 3.10+）
├── FIUP.md           # 协议文档（给 AI 看）
├── site/
│   └── index.html    # 在线 Web 工具
└── README.md
```

### 常见问题

**Q: 锚点找不到怎么办？**

工具会显示最相似的代码片段，检查是否：
- 文件已被修改
- AI 产生了"幻觉"
- `→` 数量不对（检查缩进层级）

**Q: 锚点匹配到多处？**

让 AI 扩展锚点，包含更多上下文（如函数签名、注释、更多行）。

**Q: 支持哪些语言？**

所有文本文件都支持，与编程语言无关。

**Q: 旧版 v2.0 格式还能用吗？**

v3.0 工具不兼容旧格式。如需使用旧格式，请使用 v2.0 版本的工具。

---

## English

### Why FIUP?

Problems when asking AI to modify code:

- 🤯 Line numbers are always wrong
- 📋 Manual copy-paste of large code blocks
- 🔄 AI outputs entire files, wasting tokens
- 😵 `git apply` fails on AI-generated diffs
- 💔 **Web chat interfaces collapse indentation spaces**

**Root cause**: LLMs process token streams, not line-numbered files; Web UIs compress whitespace.

**FIUP v3.0 solution**:
1. Use **unique text anchors** instead of line numbers
2. Use **visible `→` character** instead of space indentation
3. Wrap in **` ```fiup ` code block** for double protection

### Quick Start

```bash
git clone https://github.com/Thankyou-Cheems/FIUP.git
cd FIUP

# Apply patch
python fiup.py apply patch.fiup -t ./your_project

# From clipboard
pip install pyperclip
python fiup.py -c -t ./your_project

# Or use the online tool (no installation)
# https://thankyou-cheems.github.io/FIUP/
```

### Usage

#### 1. Instruct AI to use FIUP

```
Use FIUP v3.0 format for code changes:
- Wrap in <<<FIUP>>> and <<<END>>>
- Use → for indentation (→ = 4 spaces)
- Use 3-6 line anchors for uniqueness
```

Or upload `FIUP.md` as context.

#### 2. AI Output Example

````
```fiup
<<<FIUP>>>
[FILE]: src/main.py
[OP]: REPLACE
[ANCHOR]
def hello():
→print("Hello")
→return None
[CONTENT]
def hello(name: str = "World"):
→"""Say hello to someone."""
→print(f"Hello, {name}!")
→return {"greeted": name}
<<<END>>>
```
````

**Indentation**: `→` = 4 spaces, `→→` = 8 spaces, etc. No counting needed.

#### 3. Apply the patch

```bash
# Preview
python fiup.py preview patch.fiup -t ./project

# Apply
python fiup.py apply patch.fiup -t ./project

# Undo if needed
python fiup.py undo -t ./project
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

| Op | ANCHOR | CONTENT |
|:---|:---|:---|
| `REPLACE` | Old code | New code |
| `INSERT_AFTER` | Code before insertion (kept) | New code |
| `INSERT_BEFORE` | Code after insertion (kept) | New code |
| `DELETE` | Code to delete | Omit |
| `CREATE` | Omit | Full file content |

### v3.0 Format

```
```fiup                    ← Outer code block (optional but recommended)
<<<FIUP>>>                 ← Patch start
[FILE]: path/to/file.py    ← File path
[OP]: REPLACE              ← Operation type
[ANCHOR]                   ← Anchor section
def old_func():
→pass                      ← → means indentation
[CONTENT]                  ← Content section
def new_func():
→return True
<<<END>>>                  ← Patch end
```                        ← Outer code block end
```

### Why `→` for Indentation?

| Problem | Traditional | FIUP v3.0 |
|:---|:---|:---|
| Web UI eats spaces | ❌ Lost | ✅ `→` visible |
| Markdown nesting | ❌ Broken | ✅ Single block |
| LLM counting errors | ❌ `\|2\|` needs math | ✅ `→→` direct mapping |

---

## Changelog

### v3.0 (2025)
- 🆕 Visible indentation with `→` character
- 🆕 ` ```fiup ` code block wrapper
- 🆕 `CREATE` operation for new files
- 🆕 Simplified syntax: `<<<FIUP>>>`, `[FILE]:`, `[OP]:`
- 🆕 Online web tool
- ⚠️ Breaking change: Not compatible with v2.0 format

### v2.0
- Anchor-based positioning
- REPLACE, INSERT_AFTER, INSERT_BEFORE, DELETE operations
- Backup and undo support

### v1.x
- Initial prototype

---

## License

[MIT](LICENSE) - Use freely, keep the copyright notice.

## Contributing

Issues and PRs welcome!

## Credits

Inspired by the pain of AI-assisted coding. 🤖💔➡️😊

Made by [猹Cheems](https://github.com/Thankyou-Cheems)
