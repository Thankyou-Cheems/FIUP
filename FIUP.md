# FIUP - File Incremental Update Protocol v3.0

## Overview

FIUP (File Incremental Update Protocol) is a text-based patch format designed for LLM code modification. It uses **unique text anchors** instead of line numbers, and wraps patches in **` ```fiup ` code blocks** to preserve formatting.

## Core Principles

1. **Anchor-based positioning**: Use unique code snippets (3-6 lines) to locate modification points
2. **Code block wrapper**: Wrap entire patch in ` ```fiup ` block to preserve indentation
3. **Original indentation**: Keep original spaces/tabs as-is (no conversion needed)
4. **Flat structure**: No nested code blocks inside patches
5. **One patch per block**: Each `<<<FIUP>>>...<<<END>>>` contains exactly one operation

## Syntax Specification

### Patch Block Structure

IMPORTANT: Always wrap the entire patch in a `fiup` code block to preserve indentation:

````
```fiup
<<<FIUP>>>
[FILE]: <filepath>
[OP]: <operation_type>
[ANCHOR]
original code line 1
    indented line 2
        more indented line 3
[CONTENT]
new code line 1
    indented line 2
        more indented line 3
<<<END>>>
```
````

### Key Rules

1. **Wrap in ` ```fiup `**: This preserves whitespace in markdown renderers
2. **Copy code exactly**: Anchor and content should match the original file's indentation
3. **No format conversion**: Use actual spaces/tabs, not special markers
4. **Unique anchors**: 3-6 lines of code that appear only once in the file

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
    result = a + b
    return result
[CONTENT]
def calculate_sum(numbers: list[int]) -> int:
    """Calculate sum of a list of numbers."""
    if not numbers:
        return 0
    return sum(numbers)
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
    def get_name(self):
        return self.name
[CONTENT]

    def get_email(self):
        """Return user email."""
        return self.email
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
    def __init__(self):
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
    """This function is no longer needed."""
    pass
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
    def __init__(self, data: List[str]):
        self.data = data

    def process(self) -> List[str]:
        return [item.strip() for item in self.data]
<<<END>>>
```
````

### Example 6: Deeply Nested Code

For deeply nested code, just copy the original indentation:

````
```fiup
<<<FIUP>>>
[FILE]: src/parser.py
[OP]: REPLACE
[ANCHOR]
            if token.type == "STRING":
                value = token.value
                return StringNode(value)
[CONTENT]
            if token.type == "STRING":
                value = self.parse_string(token.value)
                node = StringNode(value)
                node.line = token.line
                return node
<<<END>>>
```
````

### Example 7: Multiple Patches

When multiple modifications are needed, use separate code blocks:

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

Or combine in one block:

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

```
[ANCHOR]
def process_user_data(user_id: str, options: dict):
    """Process user data with given options."""
    logger.info(f"Processing user {user_id}")
```

```
[ANCHOR]
    # SECTION: Database Configuration
    DB_HOST = "localhost"
    DB_PORT = 5432
```

### Bad Anchor Examples

```
[ANCHOR]
    return result
```
(Too generic, likely appears multiple times)

```
[ANCHOR]
import os
```
(Common import, may not be unique)

## Special Cases

### Blank Lines

Blank lines are written as empty lines:

```
[CONTENT]
def func_a():
    pass


def func_b():
    pass
```

### Mixed Indentation

The tool preserves whatever indentation style the original file uses:
- If file uses tabs: keep tabs
- If file uses spaces: keep spaces

## For LLMs: Quick Rules

1. **Wrap in ` ```fiup `** code block
2. **Start with `<<<FIUP>>>`**, end with **`<<<END>>>`**
3. **[FILE]:** specify the file path
4. **[OP]:** use REPLACE, INSERT_AFTER, INSERT_BEFORE, DELETE, or CREATE
5. **[ANCHOR]:** copy the target code **exactly as it appears** (same indentation)
6. **[CONTENT]:** write new code with **correct indentation for that location**
7. **No special markers**: just use normal spaces/tabs


**Remember**: 
- Always wrap in ` ```fiup ` code block
- Copy code exactly as-is, including indentation
- No special markers or conversions needed
