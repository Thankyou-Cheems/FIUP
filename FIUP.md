# FIUP 文件增量更新协议 v2.0

基于文本锚点的代码修改协议。**核心原则：使用唯一文本定位，禁止依赖行号。**

---

## 补丁格式

<<<FIUP_PATCH file="路径/文件名.ext">>>
[OPERATION]: REPLACE | INSERT_AFTER | INSERT_BEFORE | DELETE

<<<ANCHOR>>>
<从原文件精确复制的唯一代码片段，建议3-6行>
<<<END_ANCHOR>>>

<<<CONTENT>>>
<新代码，DELETE操作可省略整个CONTENT块>
<<<END_CONTENT>>>
<<<END_FIUP_PATCH>>>

---

## 操作类型详解

| 操作 | 场景 | 锚点要求 | 内容要求 |
|:---|:---|:---|:---|
| **REPLACE** | 修改现有代码 | 要被替换的旧代码 | 替换后的新代码 |
| **INSERT_AFTER** | 在某位置后添加 | 插入点之前的代码（会保留） | 仅新增代码，不重复锚点 |
| **INSERT_BEFORE** | 在某位置前添加 | 插入点之后的代码（会保留） | 仅新增代码，不重复锚点 |
| **DELETE** | 删除代码块 | 要删除的代码 | 省略CONTENT块 |

**选择建议：**
- 修改逻辑 → REPLACE
- 添加 import/新函数 → INSERT_AFTER
- 添加装饰器/注释 → INSERT_BEFORE
- 移除废弃代码 → DELETE

---

## 锚点选择原则 (S.U.R.E)

### S - Significant (显著性)
锚点必须包含有特征的代码，禁止仅含通用语句。

### U - Unique (唯一性)
锚点在目标文件中**必须只出现一次**。若不确定，扩展上下文。

### R - Robust (鲁棒性)
包含 3-6 行代码，含函数签名、类名、特殊注释等特征文本。

### E - Exact (精确性)
从原文件逐字复制，保持缩进，禁止使用 ... 或 # ... 等占位符。

---

## 锚点示例

### ❌ 错误示范

太短，可能不唯一：
<<<ANCHOR>>>
return True
<<<END_ANCHOR>>>

纯通用代码：
<<<ANCHOR>>>
def __init__(self):
    pass
<<<END_ANCHOR>>>

含占位符（工具无法识别）：
<<<ANCHOR>>>
def process():
    ...
    return result
<<<END_ANCHOR>>>

纯符号行：
<<<ANCHOR>>>
    }
<<<END_ANCHOR>>>

### ✅ 正确示范

含函数签名 + docstring + 开头逻辑：
<<<ANCHOR>>>
def calculate_price(item, quantity, discount=0):
    """Calculate the final price with discount."""
    base_price = item.price * quantity
<<<END_ANCHOR>>>

含类名上下文：
<<<ANCHOR>>>
class OrderProcessor:
    def __init__(self, db_connection):
        self.db = db_connection
        self.cache = {}
<<<END_ANCHOR>>>

含特殊注释/标识：
<<<ANCHOR>>>
# === AUTHENTICATION LOGIC ===
def verify_token(token: str) -> bool:
    if not token:
        return False
<<<END_ANCHOR>>>

---

## 完整示例

### 示例1：添加 import（INSERT_AFTER）

<<<FIUP_PATCH file="main.py">>>
[OPERATION]: INSERT_AFTER

<<<ANCHOR>>>
import os
import sys
from pathlib import Path
<<<END_ANCHOR>>>

<<<CONTENT>>>
import logging
import json
from typing import Optional
<<<END_CONTENT>>>
<<<END_FIUP_PATCH>>>

### 示例2：修改函数（REPLACE）

<<<FIUP_PATCH file="utils.py">>>
[OPERATION]: REPLACE

<<<ANCHOR>>>
def process_data(data):
    """Process raw data."""
    result = data.strip()
    return result
<<<END_ANCHOR>>>

<<<CONTENT>>>
def process_data(data: str, validate: bool = True) -> dict:
    """Process raw data with optional validation."""
    if validate and not data:
        raise ValueError("Empty data")
    result = data.strip()
    return {"data": result, "length": len(result)}
<<<END_CONTENT>>>
<<<END_FIUP_PATCH>>>

### 示例3：删除代码（DELETE）

<<<FIUP_PATCH file="legacy.py">>>
[OPERATION]: DELETE

<<<ANCHOR>>>
# DEPRECATED: Remove after v2.0
def old_handler(request):
    """This function is deprecated."""
    return legacy_process(request)
<<<END_ANCHOR>>>
<<<END_FIUP_PATCH>>>

### 示例4：多补丁同文件

<<<FIUP_PATCH file="service.py">>>
[OPERATION]: INSERT_AFTER

<<<ANCHOR>>>
import requests
from config import API_URL
<<<END_ANCHOR>>>

<<<CONTENT>>>
from utils import retry_decorator
<<<END_CONTENT>>>
<<<END_FIUP_PATCH>>>

<<<FIUP_PATCH file="service.py">>>
[OPERATION]: REPLACE

<<<ANCHOR>>>
def fetch_data(endpoint):
    response = requests.get(f"{API_URL}/{endpoint}")
    return response.json()
<<<END_ANCHOR>>>

<<<CONTENT>>>
@retry_decorator(max_attempts=3)
def fetch_data(endpoint: str) -> dict:
    """Fetch data from API with retry logic."""
    response = requests.get(f"{API_URL}/{endpoint}")
    response.raise_for_status()
    return response.json()
<<<END_CONTENT>>>
<<<END_FIUP_PATCH>>>

---

## 生成前检查清单

1. **定位**：确认要修改的确切代码位置
2. **唯一性验证**：自问"这个锚点在文件中只出现一次吗？"
3. **扩展检查**：若锚点可能不唯一，向上/下扩展几行
4. **缩进核对**：确保锚点和内容的缩进与原文件一致
5. **格式检查**：确认使用了正确的标记

---

### 对于 ChatGPT / Gemini

【强制要求】代码修改必须使用 FIUP 格式，不可简化或省略任何部分：
1. <<<ANCHOR>>> 必须包含从原文件精确复制的 3-6 行代码（非位置描述）
2. 每个标记（<<<FIUP_PATCH>>>, [OPERATION], <<<ANCHOR>>>, <<<CONTENT>>> 等）必须完整输出
3. 输出前自检：包含完整结构且 <<<ANCHOR>>> 内是可执行代码

---

## 关键注意事项

1. **缩进敏感**：Python/YAML 等语言的缩进必须精确匹配
2. **不要重复锚点**：INSERT_AFTER/BEFORE 的内容中不包含锚点代码
3. **顺序依赖**：多补丁按顺序应用，后续锚点应基于已修改的文件状态
4. **直接输出**：FIUP 块直接输出，不要嵌套在其他 markdown 代码围栏内
5. **完整复制**：锚点必须是原文件的精确子串，不可自行修改或"美化"
6. **禁止省略格式标记**：每个补丁必须包含完整的 <<<FIUP_PATCH>>>, [OPERATION], <<<ANCHOR>>>, <<<END_ANCHOR>>>, <<<CONTENT>>>, <<<END_CONTENT>>>, <<<END_FIUP_PATCH>>> 结构（DELETE 操作可省略 CONTENT 块）
7. **锚点必须是代码**：<<<ANCHOR>>> 块内必须是从原文件复制的实际代码，不可用自然语言描述（如"在函数 X 处"）