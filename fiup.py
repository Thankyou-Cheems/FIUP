#!/usr/bin/env python3
"""
FIUP Tool v3.0 - File Incremental Update Protocol Tool
文件增量更新协议工具

Usage:
    fiup apply [patch] -t <target>     应用补丁
    fiup preview [patch] -t <target>   预览变更（详细diff）
    fiup validate <patch>              验证补丁格式
    fiup extract <file>                从文件/对话中提取FIUP块
    fiup undo -t <target>              从最近备份恢复
    fiup diff <file1> <file2>          比较两个文件

快捷用法:
    fiup -t ./file.py                  从stdin读取并应用到file.py
    fiup -c -t ./project               从剪贴板应用到目录
    cat ai_response.txt | fiup -t .    管道输入，应用到当前目录

v3.0 新特性:
    - 使用 → 可见字符表示缩进（→ = 4空格）
    - 支持 ```fiup 代码块包裹
    - 新增 CREATE 操作（创建新文件）
    - 简化的标记语法
"""

import re
import sys
import shutil
import difflib
import argparse
from pathlib import Path
from datetime import datetime
from dataclasses import dataclass
from typing import Optional
from enum import Enum

__version__ = "3.0.0"

# 缩进配置
INDENT_CHAR = '→'
INDENT_SIZE = 4  # 每个 → 转换为4个空格


# ============== 缩进转换 ==============

def convert_indent_to_spaces(text: str, indent_unit: str = '    ') -> str:
    """将 → 转换为实际缩进（空格）"""
    if not text:
        return text
    lines = []
    for line in text.split('\n'):
        indent_count = 0
        i = 0
        while i < len(line) and line[i] == INDENT_CHAR:
            indent_count += 1
            i += 1
        rest = line[i:]
        # 处理转义的箭头 \→
        unescaped = rest.replace('\\' + INDENT_CHAR, INDENT_CHAR)
        lines.append(indent_unit * indent_count + unescaped)
    return '\n'.join(lines)


def convert_spaces_to_indent(text: str, indent_unit: str = '    ') -> str:
    """将实际缩进转换为 → （用于显示）"""
    if not text:
        return text
    lines = []
    for line in text.split('\n'):
        indent_count = 0
        pos = 0
        # 检测空格缩进
        while pos < len(line):
            if line[pos:pos + len(indent_unit)] == indent_unit:
                indent_count += 1
                pos += len(indent_unit)
            elif line[pos] == '\t':
                indent_count += 1
                pos += 1
            else:
                break
        lines.append(INDENT_CHAR * indent_count + line[pos:])
    return '\n'.join(lines)


# ============== 数据结构 ==============

class Operation(Enum):
    REPLACE = "REPLACE"
    INSERT_AFTER = "INSERT_AFTER"
    INSERT_BEFORE = "INSERT_BEFORE"
    DELETE = "DELETE"
    CREATE = "CREATE"


class MatchResult(Enum):
    EXACT = "exact"
    FUZZY = "fuzzy"
    NOT_FOUND = "not_found"
    MULTIPLE = "multiple"


@dataclass
class Patch:
    """单个补丁的数据结构"""
    file: str
    operation: Operation
    anchor: str           # 原始格式（带 →）
    content: str = ""     # 原始格式（带 →）
    anchor_real: str = "" # 转换后的实际代码
    content_real: str = "" # 转换后的实际代码
    line_number: int = 0
    raw: str = ""         # 原始补丁文本


@dataclass
class ApplyResult:
    """补丁应用结果"""
    success: bool
    patch: Patch
    match_result: MatchResult
    message: str
    match_position: int = -1
    match_line: int = -1
    original_text: str = ""
    new_text: str = ""
    similar_candidates: list = None

    def __post_init__(self):
        if self.similar_candidates is None:
            self.similar_candidates = []


# ============== 解析器 ==============

class FIUPParser:
    """解析 FIUP v3.0 格式的补丁"""
    
    # 匹配 ```fiup ... ``` 代码块
    CODE_BLOCK_PATTERN = re.compile(r'```(?:fiup)?\s*\n([\s\S]*?)```', re.MULTILINE)
    
    # 匹配单个 FIUP 块
    BLOCK_PATTERN = re.compile(r'<<<FIUP>>>([\s\S]*?)<<<END>>>', re.MULTILINE)
    
    @classmethod
    def _strip_code_blocks(cls, text: str) -> str:
        """移除 ```fiup 代码块包裹，提取内容"""
        extracted = []
        for match in cls.CODE_BLOCK_PATTERN.finditer(text):
            extracted.append(match.group(1))
        
        if extracted:
            return '\n'.join(extracted)
        return text
    
    @classmethod
    def parse(cls, text: str) -> list[Patch]:
        """解析补丁文本，返回补丁列表"""
        # 先移除代码块包裹
        content = cls._strip_code_blocks(text)
        
        patches = []
        
        for match in cls.BLOCK_PATTERN.finditer(content):
            raw = match.group(0)
            inner = match.group(1)
            line_number = text[:match.start()].count('\n') + 1
            
            # 解析 [FILE]:
            file_match = re.search(r'\[FILE\]:\s*(.+?)(?:\n|$)', inner)
            file_path = file_match.group(1).strip() if file_match else ''
            
            # 解析 [OP]:
            op_match = re.search(r'\[OP\]:\s*(REPLACE|INSERT_AFTER|INSERT_BEFORE|DELETE|CREATE)(?:\n|$)', inner, re.IGNORECASE)
            operation_str = op_match.group(1).upper() if op_match else ''
            
            try:
                operation = Operation(operation_str)
            except ValueError:
                continue  # 跳过无效操作
            
            # 解析 [ANCHOR] 部分
            anchor = ''
            anchor_match = re.search(r'\[ANCHOR\]\s*\n([\s\S]*?)(?=\[CONTENT\]|$)', inner)
            if anchor_match:
                anchor = anchor_match.group(1).rstrip('\n')
            
            # 解析 [CONTENT] 部分
            content_text = ''
            content_match = re.search(r'\[CONTENT\]\s*\n([\s\S]*?)$', inner)
            if content_match:
                content_text = content_match.group(1).rstrip('\n')
            
            # 转换缩进
            anchor_real = convert_indent_to_spaces(anchor)
            content_real = convert_indent_to_spaces(content_text)
            
            patches.append(Patch(
                file=file_path,
                operation=operation,
                anchor=anchor,
                content=content_text,
                anchor_real=anchor_real,
                content_real=content_real,
                line_number=line_number,
                raw=raw
            ))
        
        return patches
    
    @classmethod
    def extract_blocks(cls, text: str) -> list[str]:
        """从文本中提取所有FIUP块的原始文本"""
        content = cls._strip_code_blocks(text)
        blocks = []
        for match in cls.BLOCK_PATTERN.finditer(content):
            blocks.append(match.group(0))
        return blocks
    
    @classmethod
    def validate(cls, text: str) -> tuple[bool, list[str]]:
        """验证补丁格式，返回 (是否有效, 错误/警告列表)"""
        errors = []
        warnings = []
        patches = cls.parse(text)
        
        if not patches:
            if "<<<FIUP>>>" in text:
                errors.append("检测到补丁标记但解析失败，请检查格式:")
                if "[FILE]:" not in text:
                    errors.append("  ✗ 缺少 [FILE]: 标记")
                if "[OP]:" not in text:
                    errors.append("  ✗ 缺少 [OP]: 标记")
                if "<<<END>>>" not in text:
                    errors.append("  ✗ 缺少 <<<END>>> 结束标记")
            else:
                errors.append("未检测到有效的 FIUP 补丁块")
                errors.append("提示: v3.0 格式使用 <<<FIUP>>> 和 <<<END>>> 标记")
            return False, errors
        
        for i, patch in enumerate(patches):
            prefix = f"补丁 #{i+1}: "
            
            if not patch.file:
                errors.append(f"{prefix}文件路径为空")
            
            if patch.operation == Operation.CREATE:
                if not patch.content.strip():
                    errors.append(f"{prefix}CREATE 操作但内容为空")
            else:
                if not patch.anchor.strip():
                    errors.append(f"{prefix}锚点内容为空")
                
                anchor_lines = len(patch.anchor.strip().splitlines())
                if anchor_lines < 2:
                    warnings.append(f"{prefix}⚠ 锚点仅 {anchor_lines} 行，建议 3-6 行以确保唯一性")
                
                if patch.operation != Operation.DELETE and not patch.content.strip():
                    errors.append(f"{prefix}非 DELETE/CREATE 操作但内容为空")
            
            if '...' in patch.anchor or '# ...' in patch.anchor:
                warnings.append(f"{prefix}⚠ 锚点中包含 '...'，这可能导致匹配失败")
            
            # 检查是否正确使用了 → 缩进
            if patch.anchor and not any(c == INDENT_CHAR for c in patch.anchor):
                # 检查原始锚点是否有空格缩进
                if any(line.startswith('    ') or line.startswith('\t') for line in patch.anchor.split('\n') if line):
                    warnings.append(f"{prefix}⚠ 锚点使用了空格/制表符缩进，建议使用 → 字符")
        
        return len(errors) == 0, errors + warnings


# ============== 文本匹配器 ==============

class TextMatcher:
    """文本匹配器，支持精确和模糊匹配"""
    
    @staticmethod
    def normalize_whitespace(text: str) -> str:
        """规范化空白字符"""
        lines = text.replace('\r\n', '\n').replace('\r', '\n').split('\n')
        return '\n'.join(line.rstrip() for line in lines)
    
    @classmethod
    def find_anchor(cls, content: str, anchor: str, 
                    fuzzy_threshold: float = 0.85,
                    strict: bool = False) -> tuple[MatchResult, int, int, list]:
        """
        在内容中查找锚点
        返回: (匹配类型, 开始位置, 结束位置, 相似候选列表)
        """
        norm_content = cls.normalize_whitespace(content)
        norm_anchor = cls.normalize_whitespace(anchor)
        similar_candidates = []
        
        # 1. 精确匹配
        pos = norm_content.find(norm_anchor)
        if pos != -1:
            second_pos = norm_content.find(norm_anchor, pos + 1)
            if second_pos != -1:
                return MatchResult.MULTIPLE, pos, pos + len(norm_anchor), []
            
            original_pos = cls._map_position_to_original(content, norm_content, pos)
            original_end = cls._map_position_to_original(content, norm_content, pos + len(norm_anchor))
            return MatchResult.EXACT, original_pos, original_end, []
        
        # 2. 模糊匹配
        if strict:
            similar_candidates = cls._find_similar_fragments(norm_content, norm_anchor, top_k=3)
            return MatchResult.NOT_FOUND, -1, -1, similar_candidates
        
        content_lines = norm_content.split('\n')
        anchor_lines = norm_anchor.split('\n')
        
        best_ratio = 0.0
        best_start_line = -1
        candidates = []
        
        for i in range(len(content_lines) - len(anchor_lines) + 1):
            candidate = '\n'.join(content_lines[i:i + len(anchor_lines)])
            ratio = difflib.SequenceMatcher(None, candidate, norm_anchor).ratio()
            
            if ratio > 0.6:
                candidates.append((ratio, i, candidate))
            
            if ratio > best_ratio:
                best_ratio = ratio
                best_start_line = i
        
        candidates.sort(reverse=True, key=lambda x: x[0])
        similar_candidates = [(c[0], c[2], c[1]+1) for c in candidates[:3]]
        
        if best_ratio >= fuzzy_threshold:
            start_pos = sum(len(line) + 1 for line in content_lines[:best_start_line])
            end_pos = start_pos + sum(len(line) + 1 for line in content_lines[best_start_line:best_start_line + len(anchor_lines)]) - 1
            return MatchResult.FUZZY, start_pos, end_pos, similar_candidates
        
        return MatchResult.NOT_FOUND, -1, -1, similar_candidates
    
    @classmethod
    def _find_similar_fragments(cls, content: str, anchor: str, top_k: int = 3) -> list:
        """查找与锚点相似的代码片段"""
        content_lines = content.split('\n')
        anchor_lines = anchor.split('\n')
        anchor_len = len(anchor_lines)
        
        candidates = []
        for i in range(len(content_lines) - anchor_len + 1):
            candidate = '\n'.join(content_lines[i:i + anchor_len])
            ratio = difflib.SequenceMatcher(None, candidate, anchor).ratio()
            if ratio > 0.4:
                candidates.append((ratio, candidate, i + 1))
        
        candidates.sort(reverse=True, key=lambda x: x[0])
        return candidates[:top_k]
    
    @staticmethod
    def _map_position_to_original(original: str, normalized: str, norm_pos: int) -> int:
        """将规范化后的位置映射回原始文本"""
        if len(original) == len(normalized):
            return norm_pos
        
        orig_idx = 0
        norm_idx = 0
        
        while norm_idx < norm_pos and orig_idx < len(original):
            if original[orig_idx] == normalized[norm_idx]:
                orig_idx += 1
                norm_idx += 1
            elif original[orig_idx] in ' \t' and (norm_idx >= len(normalized) or normalized[norm_idx] == '\n'):
                orig_idx += 1
            elif original[orig_idx] == '\r':
                orig_idx += 1
            else:
                orig_idx += 1
                norm_idx += 1
        
        return orig_idx
    
    @staticmethod
    def get_line_number(content: str, position: int) -> int:
        """获取位置对应的行号"""
        return content[:position].count('\n') + 1


# ============== 补丁应用器 ==============

class FIUPApplier:
    """应用 FIUP 补丁"""
    
    def __init__(self, target_dir: Path, backup: bool = True, 
                 dry_run: bool = False, strict: bool = False,
                 interactive: bool = False):
        self.target_dir = target_dir
        self.backup = backup
        self.dry_run = dry_run
        self.strict = strict
        self.interactive = interactive
        self.backup_dir: Optional[Path] = None
        self.created_files: list[Path] = []  # 新建的文件列表
    
    def apply_all(self, patches: list[Patch]) -> list[ApplyResult]:
        """应用所有补丁"""
        results = []
        
        if self.backup and not self.dry_run:
            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            self.backup_dir = self.target_dir / f".fiup_backup_{timestamp}"
            self.backup_dir.mkdir(parents=True, exist_ok=True)
        
        file_contents: dict[str, str] = {}
        
        for patch in patches:
            # CREATE 操作特殊处理
            if patch.operation == Operation.CREATE:
                result = self._apply_create(patch)
                results.append(result)
                if result.success:
                    file_contents[patch.file] = result.new_text
                continue
            
            file_path = self.target_dir / patch.file
            
            if patch.file not in file_contents:
                if not file_path.exists():
                    results.append(ApplyResult(
                        success=False,
                        patch=patch,
                        match_result=MatchResult.NOT_FOUND,
                        message=f"文件不存在: {file_path}"
                    ))
                    continue
                
                file_contents[patch.file] = file_path.read_text(encoding='utf-8')
                
                if self.backup and not self.dry_run:
                    backup_path = self.backup_dir / patch.file
                    backup_path.parent.mkdir(parents=True, exist_ok=True)
                    shutil.copy2(file_path, backup_path)
            
            content = file_contents[patch.file]
            result = self._apply_patch(content, patch)
            results.append(result)
            
            if result.match_result == MatchResult.FUZZY and self.interactive and not self.dry_run:
                if not self._confirm_fuzzy_match(result):
                    result.success = False
                    result.message = "用户取消模糊匹配"
                    continue
            
            if result.success:
                file_contents[patch.file] = result.new_text
        
        if not self.dry_run:
            for file_rel, content in file_contents.items():
                file_path = self.target_dir / file_rel
                file_results = [r for r in results if r.patch.file == file_rel]
                if all(r.success for r in file_results):
                    file_path.parent.mkdir(parents=True, exist_ok=True)
                    file_path.write_text(content, encoding='utf-8')
        
        return results
    
    def _apply_create(self, patch: Patch) -> ApplyResult:
        """应用 CREATE 操作"""
        file_path = self.target_dir / patch.file
        
        if file_path.exists() and not self.dry_run:
            return ApplyResult(
                success=False,
                patch=patch,
                match_result=MatchResult.MULTIPLE,
                message=f"文件已存在: {file_path}",
                original_text="",
                new_text=patch.content_real
            )
        
        self.created_files.append(file_path)
        
        return ApplyResult(
            success=True,
            patch=patch,
            match_result=MatchResult.EXACT,
            message=f"创建新文件",
            original_text="",
            new_text=patch.content_real
        )
    
    def _apply_patch(self, content: str, patch: Patch) -> ApplyResult:
        """应用单个补丁"""
        # 使用转换后的实际代码进行匹配
        match_result, start, end, similar = TextMatcher.find_anchor(
            content, patch.anchor_real, strict=self.strict
        )
        
        if match_result == MatchResult.NOT_FOUND:
            msg = "锚点未找到"
            if similar:
                msg += "，最相似的代码片段:"
            return ApplyResult(
                success=False,
                patch=patch,
                match_result=match_result,
                message=msg,
                original_text=content,
                similar_candidates=similar
            )
        
        if match_result == MatchResult.MULTIPLE:
            return ApplyResult(
                success=False,
                patch=patch,
                match_result=match_result,
                message="锚点匹配到多处，请扩展锚点使其唯一",
                match_position=start,
                match_line=TextMatcher.get_line_number(content, start),
                original_text=content
            )
        
        new_content = self._construct_new_content(content, patch, start, end)
        match_line = TextMatcher.get_line_number(content, start)
        
        match_type_str = "精确匹配" if match_result == MatchResult.EXACT else "⚠ 模糊匹配"
        
        return ApplyResult(
            success=True,
            patch=patch,
            match_result=match_result,
            message=f"{match_type_str} @ 行 {match_line}",
            match_position=start,
            match_line=match_line,
            original_text=content,
            new_text=new_content,
            similar_candidates=similar
        )
    
    def _construct_new_content(self, content: str, patch: Patch, start: int, end: int) -> str:
        """构造新内容"""
        before = content[:start]
        after = content[end:]
        matched = content[start:end]
        
        # 使用转换后的实际代码
        new_code = patch.content_real
        
        if patch.operation == Operation.REPLACE:
            return before + new_code + after
        elif patch.operation == Operation.INSERT_AFTER:
            separator = '\n' if not matched.endswith('\n') else ''
            return before + matched + separator + new_code + after
        elif patch.operation == Operation.INSERT_BEFORE:
            separator = '\n' if not new_code.endswith('\n') else ''
            return before + new_code + separator + matched + after
        elif patch.operation == Operation.DELETE:
            return before + after
        return content
    
    def _confirm_fuzzy_match(self, result: ApplyResult) -> bool:
        """交互式确认模糊匹配"""
        print_colored(f"\n⚠ 模糊匹配确认 (行 {result.match_line}):", "yellow")
        print("  锚点 (→ 已转换为空格):")
        for line in result.patch.anchor_real.split('\n')[:5]:
            print(f"    {line}")
        print("\n  是否应用此补丁? [y/N] ", end="")
        try:
            response = input().strip().lower()
            return response in ('y', 'yes')
        except (EOFError, KeyboardInterrupt):
            return False


# ============== 输出工具 ==============

def print_colored(text: str, color: str = "default"):
    """打印带颜色的文本"""
    colors = {
        "red": "\033[91m",
        "green": "\033[92m",
        "yellow": "\033[93m",
        "blue": "\033[94m",
        "magenta": "\033[95m",
        "cyan": "\033[96m",
        "gray": "\033[90m",
        "bold": "\033[1m",
        "default": "\033[0m",
    }
    reset = "\033[0m"
    print(f"{colors.get(color, '')}{text}{reset}")


def print_diff(old_text: str, new_text: str, file_name: str = "", context_lines: int = 3):
    """打印两段文本的差异"""
    old_lines = old_text.splitlines(keepends=True)
    new_lines = new_text.splitlines(keepends=True)
    
    diff = difflib.unified_diff(
        old_lines, new_lines,
        fromfile=f"a/{file_name}" if file_name else "original",
        tofile=f"b/{file_name}" if file_name else "modified",
        lineterm="",
        n=context_lines
    )
    
    for line in diff:
        if line.startswith('+') and not line.startswith('+++'):
            print_colored(line.rstrip(), "green")
        elif line.startswith('-') and not line.startswith('---'):
            print_colored(line.rstrip(), "red")
        elif line.startswith('@@'):
            print_colored(line.rstrip(), "cyan")
        else:
            print(line.rstrip())


def print_similar_candidates(candidates: list):
    """打印相似代码片段"""
    for i, (ratio, code, line) in enumerate(candidates[:3]):
        print_colored(f"\n  候选 {i+1} (相似度 {ratio:.0%}, 行 {line}):", "gray")
        lines = code.split('\n')
        for l in lines[:4]:
            print_colored(f"    {l}", "gray")
        if len(lines) > 4:
            print_colored(f"    ... (+{len(lines)-4} 行)", "gray")


# ============== 命令处理 ==============

def read_patch_input(args) -> Optional[str]:
    """统一读取补丁输入"""
    if getattr(args, 'clipboard', False):
        try:
            import pyperclip
            return pyperclip.paste()
        except ImportError:
            print_colored("错误: --clipboard 需要安装 pyperclip: pip install pyperclip", "red")
            return None
    
    patch_file = getattr(args, 'patch_file', '-')
    if patch_file == '-':
        if sys.stdin.isatty():
            print_colored("等待输入补丁内容 (Ctrl+D 结束):", "cyan")
            print_colored("提示: v3.0 使用 → 表示缩进，<<<FIUP>>>...<<<END>>> 包裹补丁", "gray")
        return sys.stdin.read()
    else:
        patch_path = Path(patch_file)
        if not patch_path.exists():
            print_colored(f"错误: 文件不存在: {patch_path}", "red")
            return None
        return patch_path.read_text(encoding='utf-8')


def resolve_target(args, patches: list[Patch]) -> Optional[Path]:
    """解析目标路径"""
    target_path = Path(args.target).resolve()
    
    # CREATE 操作可以创建不存在的目录
    create_patches = [p for p in patches if p.operation == Operation.CREATE]
    non_create_patches = [p for p in patches if p.operation != Operation.CREATE]
    
    if not target_path.exists():
        if create_patches and not non_create_patches:
            # 全部是 CREATE 操作，可以创建目录
            target_path.mkdir(parents=True, exist_ok=True)
            return target_path
        print_colored(f"错误: 目标路径不存在: {target_path}", "red")
        return None
    
    if target_path.is_file():
        target_dir = target_path.parent
        target_filename = target_path.name
        
        patch_files = set(p.file for p in non_create_patches)
        if len(patch_files) == 1:
            patch_file = list(patch_files)[0]
            if patch_file != target_filename and Path(patch_file).name != target_filename:
                print_colored(f"映射: {patch_file} → {target_filename}", "cyan")
                for p in patches:
                    if p.operation != Operation.CREATE:
                        p.file = target_filename
        
        return target_dir
    
    return target_path


def cmd_apply(args):
    """apply 命令"""
    patch_text = read_patch_input(args)
    if patch_text is None:
        return 1
    
    patches = FIUPParser.parse(patch_text)
    if not patches:
        print_colored("错误: 未解析出有效补丁", "red")
        valid, errors = FIUPParser.validate(patch_text)
        for err in errors:
            print_colored(f"  {err}", "yellow")
        return 1
    
    # 统计操作类型
    op_counts = {}
    for p in patches:
        op_counts[p.operation.value] = op_counts.get(p.operation.value, 0) + 1
    op_summary = ", ".join(f"{v} {k}" for k, v in op_counts.items())
    print_colored(f"解析到 {len(patches)} 个补丁 ({op_summary})", "cyan")
    
    target_dir = resolve_target(args, patches)
    if target_dir is None:
        return 1
    
    applier = FIUPApplier(
        target_dir=target_dir,
        backup=args.backup,
        dry_run=args.dry_run,
        strict=args.strict,
        interactive=args.interactive
    )
    
    results = applier.apply_all(patches)
    
    success_count = sum(1 for r in results if r.success)
    print()
    
    status_text = f"{'[预览] ' if args.dry_run else ''}结果: {success_count}/{len(results)} 成功"
    print_colored(status_text, "green" if success_count == len(results) else "yellow")
    print()
    
    for i, result in enumerate(results):
        status = "✓" if result.success else "✗"
        color = "green" if result.success else "red"
        
        op_str = result.patch.operation.value
        if result.patch.operation == Operation.CREATE:
            op_str = "CREATE (新建)"
        
        print_colored(f"{status} #{i+1} [{op_str}] {result.patch.file}", color)
        print(f"   {result.message}")
        
        if not result.success and result.similar_candidates:
            print_similar_candidates(result.similar_candidates)
        
        if result.success and args.verbose:
            print()
            print_diff(result.original_text, result.new_text, result.patch.file)
        print()
    
    if applier.backup_dir and not args.dry_run:
        print_colored(f"备份: {applier.backup_dir}", "blue")
    
    if applier.created_files and not args.dry_run:
        print_colored(f"新建: {len(applier.created_files)} 个文件", "magenta")
    
    return 0 if success_count == len(results) else 1


def cmd_preview(args):
    """preview 命令"""
    args.dry_run = True
    args.verbose = True
    args.backup = False
    return cmd_apply(args)


def cmd_validate(args):
    """validate 命令"""
    patch_path = Path(args.patch_file)
    if not patch_path.exists():
        print_colored(f"错误: 文件不存在: {patch_path}", "red")
        return 1
    
    patch_text = patch_path.read_text(encoding='utf-8')
    valid, messages = FIUPParser.validate(patch_text)
    
    if valid:
        patches = FIUPParser.parse(patch_text)
        print_colored(f"✓ 格式有效，共 {len(patches)} 个补丁", "green")
        for i, patch in enumerate(patches):
            anchor_preview = patch.anchor.split('\n')[0][:50] if patch.anchor else "(无锚点)"
            print(f"   #{i+1}: {patch.operation.value} @ {patch.file}")
            if patch.operation != Operation.CREATE:
                print_colored(f"        锚点: {anchor_preview}...", "gray")
            else:
                content_lines = len(patch.content.split('\n'))
                print_colored(f"        内容: {content_lines} 行", "gray")
    
    for msg in messages:
        if msg.startswith("⚠"):
            print_colored(msg, "yellow")
        elif "✗" in msg or "错误" in msg:
            print_colored(msg, "red")
        else:
            print(msg)
    
    return 0 if valid else 1


def cmd_extract(args):
    """extract 命令"""
    input_path = Path(args.input_file)
    if not input_path.exists():
        print_colored(f"错误: 文件不存在: {input_path}", "red")
        return 1
    
    text = input_path.read_text(encoding='utf-8')
    blocks = FIUPParser.extract_blocks(text)
    
    if not blocks:
        print_colored("未找到 FIUP 补丁块", "yellow")
        print_colored("提示: v3.0 格式使用 <<<FIUP>>> 和 <<<END>>> 标记", "gray")
        return 1
    
    print_colored(f"提取到 {len(blocks)} 个补丁块", "green")
    
    if args.output:
        output_path = Path(args.output)
        output_path.write_text('\n\n'.join(blocks), encoding='utf-8')
        print_colored(f"已保存至: {output_path}", "blue")
    else:
        print("\n" + "="*50 + "\n")
        print('\n\n'.join(blocks))
    
    return 0


def cmd_undo(args):
    """undo 命令"""
    target_dir = Path(args.target).resolve()
    if not target_dir.exists():
        print_colored(f"错误: 目标路径不存在: {target_dir}", "red")
        return 1
    
    if target_dir.is_file():
        target_dir = target_dir.parent
    
    backups = sorted(target_dir.glob(".fiup_backup_*"), reverse=True)
    if not backups:
        print_colored("未找到备份目录", "yellow")
        return 1
    
    if args.list:
        print_colored("可用备份:", "cyan")
        for i, backup in enumerate(backups[:10]):
            timestamp = backup.name.replace(".fiup_backup_", "")
            files = list(backup.rglob("*"))
            file_count = len([f for f in files if f.is_file()])
            print(f"  {i+1}. {backup.name} ({file_count} 个文件)")
        return 0
    
    backup_dir = backups[0]
    if args.backup_name:
        matching = [b for b in backups if args.backup_name in b.name]
        if not matching:
            print_colored(f"未找到匹配的备份: {args.backup_name}", "red")
            return 1
        backup_dir = matching[0]
    
    print_colored(f"从备份恢复: {backup_dir.name}", "cyan")
    
    restored = 0
    for backup_file in backup_dir.rglob("*"):
        if backup_file.is_file():
            rel_path = backup_file.relative_to(backup_dir)
            target_file = target_dir / rel_path
            
            if args.dry_run:
                print(f"  [预览] {rel_path}")
            else:
                target_file.parent.mkdir(parents=True, exist_ok=True)
                shutil.copy2(backup_file, target_file)
                print(f"  ✓ {rel_path}")
            restored += 1
    
    status = "[预览] " if args.dry_run else ""
    print_colored(f"\n{status}恢复了 {restored} 个文件", "green")
    return 0


def cmd_diff(args):
    """diff 命令"""
    file1 = Path(args.file1)
    file2 = Path(args.file2)
    
    if not file1.exists():
        print_colored(f"错误: 文件不存在: {file1}", "red")
        return 1
    if not file2.exists():
        print_colored(f"错误: 文件不存在: {file2}", "red")
        return 1
    
    text1 = file1.read_text(encoding='utf-8')
    text2 = file2.read_text(encoding='utf-8')
    
    print_diff(text1, text2, file1.name)
    return 0


# ============== 主入口 ==============

def main():
    parser = argparse.ArgumentParser(
        prog='fiup',
        description="FIUP Tool v3.0 - 文件增量更新协议工具",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog=f"""
快捷用法:
  fiup -t ./file.py                   从stdin应用补丁
  fiup -c -t ./project                从剪贴板应用
  fiup preview patch.fiup -t .        预览变更
  fiup undo -t ./project              恢复备份
  fiup undo -t ./project --list       列出所有备份

示例:
  cat response.txt | fiup -t ./src
  fiup apply patch.fiup -t ./project -v
  fiup extract chat.md -o patches.fiup

v3.0 格式:
  - 使用 {INDENT_CHAR} 表示缩进（{INDENT_CHAR} = {INDENT_SIZE}空格）
  - 支持 ```fiup 代码块包裹
  - 操作: REPLACE, INSERT_AFTER, INSERT_BEFORE, DELETE, CREATE
        """
    )
    
    parser.add_argument('--version', '-V', action='version', version=f'%(prog)s {__version__}')
    parser.add_argument('--target', '-t', help='目标目录或文件')
    parser.add_argument('--clipboard', '-c', action='store_true', help='从剪贴板读取')
    parser.add_argument('--dry-run', '-n', action='store_true', help='预览模式')
    parser.add_argument('--verbose', '-v', action='store_true', help='显示详细差异')
    parser.add_argument('--strict', '-s', action='store_true', help='严格模式（禁用模糊匹配）')
    parser.add_argument('--interactive', '-i', action='store_true', help='交互式确认模糊匹配')
    parser.add_argument('--backup', '-b', action='store_true', default=True, help='备份原文件')
    parser.add_argument('--no-backup', action='store_false', dest='backup', help='不备份')
    
    subparsers = parser.add_subparsers(dest='command', help='命令')
    
    apply_p = subparsers.add_parser('apply', help='应用补丁')
    apply_p.add_argument('patch_file', nargs='?', default='-', help='补丁文件（- 表示stdin）')
    apply_p.add_argument('--target', '-t', required=True, help='目标目录或文件')
    apply_p.add_argument('--backup', '-b', action='store_true', default=True)
    apply_p.add_argument('--no-backup', action='store_false', dest='backup')
    apply_p.add_argument('--dry-run', '-n', action='store_true')
    apply_p.add_argument('--verbose', '-v', action='store_true')
    apply_p.add_argument('--strict', '-s', action='store_true')
    apply_p.add_argument('--interactive', '-i', action='store_true')
    apply_p.add_argument('--clipboard', '-c', action='store_true')
    
    preview_p = subparsers.add_parser('preview', help='预览变更（等同于 apply --dry-run -v）')
    preview_p.add_argument('patch_file', nargs='?', default='-')
    preview_p.add_argument('--target', '-t', required=True)
    preview_p.add_argument('--strict', '-s', action='store_true')
    preview_p.add_argument('--interactive', '-i', action='store_true')
    preview_p.add_argument('--clipboard', '-c', action='store_true')
    
    validate_p = subparsers.add_parser('validate', help='验证补丁格式')
    validate_p.add_argument('patch_file', help='补丁文件')
    
    extract_p = subparsers.add_parser('extract', help='从文件中提取FIUP块')
    extract_p.add_argument('input_file', help='输入文件（如AI对话记录）')
    extract_p.add_argument('--output', '-o', help='输出文件')
    
    undo_p = subparsers.add_parser('undo', help='从备份恢复')
    undo_p.add_argument('--target', '-t', required=True, help='目标目录')
    undo_p.add_argument('--list', '-l', action='store_true', help='列出所有备份')
    undo_p.add_argument('--backup-name', help='指定备份名称')
    undo_p.add_argument('--dry-run', '-n', action='store_true')
    
    diff_p = subparsers.add_parser('diff', help='比较两个文件')
    diff_p.add_argument('file1', help='原始文件')
    diff_p.add_argument('file2', help='修改后文件')
    
    args = parser.parse_args()
    
    if args.command is None and args.target:
        args.command = 'apply'
        args.patch_file = '-'
        return cmd_apply(args)
    
    if args.command == 'apply':
        return cmd_apply(args)
    elif args.command == 'preview':
        return cmd_preview(args)
    elif args.command == 'validate':
        return cmd_validate(args)
    elif args.command == 'extract':
        return cmd_extract(args)
    elif args.command == 'undo':
        return cmd_undo(args)
    elif args.command == 'diff':
        return cmd_diff(args)
    else:
        parser.print_help()
        return 0


if __name__ == '__main__':
    sys.exit(main())
