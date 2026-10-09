import re

# 全局配置
_show_token_saved = True
_compress_mode = "default"
_protected_prefix = ["系统:", "指令:", "技能:", "skill:", "config:", "set_tip"]

def set_tip_status(show: bool):
    global _show_token_saved
    _show_token_saved = show

def set_compress_mode(mode: str):
    global _compress_mode
    if mode in ["light", "default", "strict"]:
        _compress_mode = mode

def detect_user_command(text: str):
    t = text.strip().lower()
    if any(k in t for k in ["关闭省token提示", "关闭token提示", "关闭提示", "关掉省token"]):
        return "close_tip"
    elif any(k in t for k in ["打开省token提示", "打开token提示", "打开提示", "显示省token"]):
        return "open_tip"
    elif any(k in t for k in ["严格模式", "最强压缩", "极度省token"]):
        return "mode_strict"
    elif any(k in t for k in ["轻度模式", "轻度压缩", "轻微省token"]):
        return "mode_light"
    elif any(k in t for k in ["默认模式", "正常模式", "标准模式"]):
        return "mode_default"
    return None

def is_protected(text: str) -> bool:
    """保护系统指令不压缩"""
    for p in _protected_prefix:
        if text.strip().startswith(p):
            return True
    return False

def detect_content_type(text: str) -> str:
    code_pattern = re.compile(
        r'(def |class |import |# |// |{|}|if\s*\(|for\s*\(|while\s*\(|print\(|'
        r'function |const |let |var |return |console\.log|<?php|<!DOCTYPE|</.*?>)'
    )
    code_block = re.search(r'```.*?```|`[^`]+`', text, re.DOTALL)
    has_code = bool(code_pattern.search(text) or code_block)
    if not has_code:
        return "pure_text"
    code_lines = [ln for ln in text.splitlines() if code_pattern.search(ln) or ln.strip().startswith(('#', '//', '{', '}'))]
    code_ratio = len('\n'.join(code_lines)) / len(text) if text else 0
    return "code" if code_ratio > 0.3 else "mixed"

def estimate_token_accurate(s: str, content_type: str) -> int:
    """精准Token估算（接近官方）"""
    if content_type == "code":
        return len(s) // 4
    chinese = len(re.findall(r'[\u4e00-\u9fff]', s))
    english = len(re.findall(r'[a-zA-Z0-9_]+', s))
    return int(chinese * 1.0 + english * 0.5 + 5)

def simplify_sentence(text: str) -> str:
    """长句智能简化（稳健版，不破坏语义）"""
    rules = [
        ("我想请问一下你能不能帮我", ""),
        ("我需要你帮我", ""),
        ("你可以帮我", ""),
        ("我想让你帮我", ""),
        ("请问一下", ""),
        ("我想问一下", ""),
        ("帮我一下", ""),
        ("有没有办法", "如何")
    ]
    for a, b in rules:
        text = text.replace(a, b)
    return text

def remove_duplicate_phrases(text: str) -> str:
    """移除冗余短句"""
    duplicates = ["谢谢", "好的", "我知道了", "明白了", "辛苦了", "你真棒"]
    for w in duplicates:
        text = text.replace(w, "")
    return text

def compress_code_comments(code: str, mode: str) -> str:
    """代码注释分级压缩（稳健）"""
    if mode == "default":
        code = re.sub(r'#.*', '', code)
    elif mode == "strict":
        code = re.sub(r'#.*', '', code)
        code = re.sub(r'//.*', '', code)
        code = re.sub(r'/\*.*?\*/', '', code, flags=re.DOTALL)
    lines = [ln.rstrip() for ln in code.splitlines() if ln.strip()]
    return '\n'.join(lines)

def compress_text(text: str, mode: str = None):
    global _compress_mode
    mode = mode or _compress_mode

    if not text or not isinstance(text, str):
        return {"status": "error", "msg": "输入不能为空"}
    if is_protected(text):
        return {"status": "success", "compressed_text": text, "tip": "系统指令已保护"}

    original = text.strip()
    content_type = detect_content_type(original)
    t = original

    if content_type == "code":
        t = compress_code_comments(t, mode)
        t = re.sub(r' {2,}', ' ', t)
    else:
        t = re.sub(r'\s+', ' ', t)
        t = simplify_sentence(t)
        t = remove_duplicate_phrases(t)

        fillers = ["我想", "我需要", "请问", "你好", "您好", "谢谢", "帮我"]
        for w in fillers:
            t = t.replace(w, "")

        if mode == "strict":
            strict_words = ["然后", "并且", "而且", "其实", "实际上", "就是", "这个", "那个", "我", "吧", "呢", "啊"]
            for w in strict_words:
                t = t.replace(w, "")

    compressed = t.strip()
    token_before = estimate_token_accurate(original, content_type)
    token_after = estimate_token_accurate(compressed, content_type)
    saved = max(0, token_before - token_after)

    res = {
        "status": "success",
        "content_type": content_type,
        "current_mode": mode,
        "original_token": token_before,
        "compressed_token": token_after,
        "token_saved": saved,
        "compressed_text": compressed
    }

    if _show_token_saved and saved > 0:
        res["tip"] = f"已节省 {saved} Token（{mode}模式）"
    return res

# QClaw 入口函数
def run(params: dict) -> dict:
    text = params.get("text", "")
    cmd = detect_user_command(text)

    if cmd == "close_tip":
        set_tip_status(False)
        return {"status": "success", "msg": "已关闭省Token提示", "compressed_text": text}
    if cmd == "open_tip":
        set_tip_status(True)
        return {"status": "success", "msg": "已打开省Token提示", "compressed_text": text}
    if cmd == "mode_strict":
        set_compress_mode("strict")
        return {"status": "success", "msg": "已进入严格模式", "compressed_text": text}
    if cmd == "mode_light":
        set_compress_mode("light")
        return {"status": "success", "msg": "已进入轻度模式", "compressed_text": text}
    if cmd == "mode_default":
        set_compress_mode("default")
        return {"status": "success", "msg": "已进入默认模式", "compressed_text": text}

    return compress_text(text)