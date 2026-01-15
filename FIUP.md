# FIUP - File Incremental Update Protocol v3.0

## Overview

FIUP (File Incremental Update Protocol) is a text-based patch format designed for LLM code modification. It uses **unique text anchors** instead of line numbers, and **visible indentation characters** instead of whitespace.

## Core Principles

1. **Anchor-based positioning**: Use unique code snippets (3-6 lines) to locate modification points
2. **Visible indentation**: Use `→` character to represent indentation units (no counting required)
3. **Code block wrapper**: Wrap entire patch in ` ```fiup ` block for format preservation
4. **Flat structure**: No nested code blocks inside patches
5. **One patch per block**: Each `<<<FIUP>>>...<<<END>>>` contains exactly one operation

## Syntax Specification

### Patch Block Structure

IMPORTANT: Always wrap the entire patch in a `fiup` code block:

````
```fiup
<<<FIUP>>>
[FILE]: <filepath>
[OP]: <operation_type>
[ANCHOR]
line1
→indented_line2
→→more_indented_line3
[CONTENT]
line1
→indented_line2
→→more_indented_line3
<<<END>>>
```
````

### Indentation Marker

Use `→` at the start of each line to indicate indentation:

- No `→` = no indentation (column 0)
- `→` = 1 indent unit (4 spaces or 1 tab)
- `→→` = 2 indent units (8 spaces)
- `→→→` = 3 indent units (12 spaces)
- `→→→→` = 4 indent units (16 spaces)

**Rules**:
- One `→` equals one indentation unit (typically 4 spaces)
- Place `→` only at the START of lines, not within code
- Lines with no indentation have no `→` prefix
- Copy the indentation structure from original code, replacing spaces/tabs with `→`

### Operation Types

| Operation | Description | ANCHOR | CONTENT |
|-----------|-------------|--------|---------|
| `REPLACE` | Replace anchor with content | Code to replace | New code |
| `INSERT_AFTER` | Insert after anchor | Locator (preserved) | New code to insert |
| `INSERT_BEFORE` | Insert before anchor | Locator (preserved) | New code to insert |
| `DELETE` | Delete anchor | Code to delete | Omit entirely |
| `CREATE` | Create new file | Omit entirely | Full file content |

### Section Markers

- `[FILE]:` - Target file path (relative to project root)
- `[OP]:` - Operation type
- `[ANCHOR]` - Start of anchor section (code to locate)
- `[CONTENT]` - Start of content section (new code)

## Examples

### Example 1: REPLACE

Replace a function implementation:

````
```fiup
<<<FIUP>>>
[FILE]: src/utils.py
[OP]: REPLACE
[ANCHOR]
def calculate_sum(a, b):
→result = a + b
→return result
[CONTENT]
def calculate_sum(numbers: list[int]) -> int:
→"""Calculate sum of a list of numbers."""
→if not numbers:
→→return 0
→return sum(numbers)
<<<END>>>
```
````

### Example 2: INSERT_AFTER

Add a new method after an existing one:

````
```fiup
<<<FIUP>>>
[FILE]: src/user.py
[OP]: INSERT_AFTER
[ANCHOR]
→def get_name(self):
→→return self.name
[CONTENT]

→def get_email(self):
→→"""Return user email."""
→→return self.email
<<<END>>>
```
````

### Example 3: INSERT_BEFORE

Add imports before existing code:

````
```fiup
<<<FIUP>>>
[FILE]: main.py
[OP]: INSERT_BEFORE
[ANCHOR]
class Application:
→def __init__(self):
[CONTENT]
from typing import Optional
from dataclasses import dataclass

<<<END>>>
```
````

### Example 4: DELETE

Remove a function:

````
```fiup
<<<FIUP>>>
[FILE]: legacy.py
[OP]: DELETE
[ANCHOR]
def deprecated_function():
→"""This function is no longer needed."""
→pass
<<<END>>>
```
````

### Example 5: CREATE

Create a new file:

````
```fiup
<<<FIUP>>>
[FILE]: src/new_module.py
[OP]: CREATE
[CONTENT]
"""New module for handling data processing."""

from typing import List


class DataProcessor:
→def __init__(self, data: List[str]):
→→self.data = data

→def process(self) -> List[str]:
→→return [item.strip() for item in self.data]
<<<END>>>
```
````

### Example 6: Deeply Nested Code

For deeply nested code, simply add more `→`:

````
```fiup
<<<FIUP>>>
[FILE]: src/parser.py
[OP]: REPLACE
[ANCHOR]
→→→if token.type == "STRING":
→→→→value = token.value
→→→→return StringNode(value)
[CONTENT]
→→→if token.type == "STRING":
→→→→value = self.parse_string(token.value)
→→→→node = StringNode(value)
→→→→node.line = token.line
→→→→return node
<<<END>>>
```
````

### Example 7: Multiple Patches

When multiple modifications are needed, you can use separate code blocks or combine in one:

**Option A: Separate blocks (recommended for clarity)**

````
```fiup
<<<FIUP>>>
[FILE]: config.py
[OP]: REPLACE
[ANCHOR]
DEBUG = True
[CONTENT]
DEBUG = False
<<<END>>>
```
````

````
```fiup
<<<FIUP>>>
[FILE]: config.py
[OP]: INSERT_AFTER
[ANCHOR]
DEBUG = False
[CONTENT]
LOG_LEVEL = "INFO"
<<<END>>>
```
````

**Option B: Combined in one block**

````
```fiup
<<<FIUP>>>
[FILE]: config.py
[OP]: REPLACE
[ANCHOR]
DEBUG = True
[CONTENT]
DEBUG = False
<<<END>>>

<<<FIUP>>>
[FILE]: config.py
[OP]: INSERT_AFTER
[ANCHOR]
DEBUG = False
[CONTENT]
LOG_LEVEL = "INFO"
<<<END>>>
```
````

## Anchor Guidelines

### Anchor Selection Rules

1. **Uniqueness**: Anchor must appear exactly ONCE in the target file
2. **Length**: 3-6 lines recommended for reliable matching
3. **Context**: Include distinctive elements (function signatures, unique comments, specific variable names)
4. **Avoid**: Generic code that may repeat (bare `return`, `pass`, `}`, etc.)

### Good Anchor Examples

````
```fiup
[ANCHOR]
def process_user_data(user_id: str, options: dict):
→"""Process user data with given options."""
→logger.info(f"Processing user {user_id}")
```
````

````
```fiup
[ANCHOR]
→# SECTION: Database Configuration
→DB_HOST = "localhost"
→DB_PORT = 5432
```
````

### Bad Anchor Examples

```
[ANCHOR]
→return result
```
(Too generic, likely appears multiple times)

```
[ANCHOR]
import os
```
(Common import, may not be unique)

## Special Cases

### Blank Lines

Blank lines are written as empty lines (no `→` needed):

````
```fiup
[CONTENT]
def func_a():
→pass


def func_b():
→pass
```
````

### Code Containing → Character

If the actual code contains `→` character, escape it as `\→`:

````
```fiup
[CONTENT]
→print("Arrow: \→")
```
````

### Mixed Indentation Detection

The tool automatically detects whether the target file uses tabs or spaces:
- If file uses tabs: each `→` becomes 1 tab
- If file uses spaces: each `→` becomes 4 spaces (configurable)

## For LLMs: Quick Rules

1. **Wrap in code block**: Always use ` ```fiup ` and ` ``` `
2. **Start with `<<<FIUP>>>`**, end with **`<<<END>>>`**
3. **[FILE]:** specify the file path
4. **[OP]:** use REPLACE, INSERT_AFTER, INSERT_BEFORE, DELETE, or CREATE
5. **[ANCHOR]:** copy the target code exactly, replacing leading spaces with `→`
6. **[CONTENT]:** write new code, using `→` for each indentation level
7. **One `→` = one indent level** (don't count, just match the visual nesting)

## Why This Format?

### Problem with Plain Indentation
Web chat interfaces collapse multiple spaces into one, breaking indentation-based formats.

### Problem with Nested Code Blocks
Using ` ``` ` inside ` ``` ` causes parsing issues and confuses many LLMs.

### FIUP v3.0 Solution
- **Outer ` ```fiup ` block**: Preserves formatting in markdown-enabled interfaces
- **`→` markers**: Visible indentation that survives even if code block fails
- **Flat structure**: No nesting, easy for all LLMs to generate correctly

## Protocol Metadata

- **Version**: 3.0
- **Created**: 2025
- **License**: MIT
- **Repository**: https://github.com/Thankyou-Cheems/FIUP

## Quick Reference Card

````
```fiup
<<<FIUP>>>
[FILE]: path/to/file.ext
[OP]: REPLACE | INSERT_AFTER | INSERT_BEFORE | DELETE | CREATE
[ANCHOR]
code_at_column_0
→indented_once
→→indented_twice
[CONTENT]
new_code_at_column_0
→new_indented_once
→→new_indented_twice
→→→new_indented_three_times
<<<END>>>
```
````

**Remember**: 
- Always wrap in ` ```fiup ` code block
- `→` = one indentation level
- No `→` = no indentation
- Just match the visual structure, no counting needed
