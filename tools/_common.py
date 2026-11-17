#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""_common.py —— 技能包公用：路径、退出码、SUMMARY 输出、payload 装载。"""
import json
import os
import sys
import time

# 统一 UTF-8 输出：AI 侧通常按 UTF-8 解析，Windows 控制台乱码只是显示问题
try:
    sys.stdout.reconfigure(encoding='utf-8', errors='replace')
    sys.stderr.reconfigure(encoding='utf-8', errors='replace')
except Exception:
    pass

# ---------- 退出码 ----------
E_OK = 0
E_PORT = 2       # 找不到串口 / 找不到设备
E_BUSY = 3       # 串口被占用（IDE）
E_REPL = 4       # REPL 无响应 / 超时
E_SCRIPT = 5     # 板端 Traceback
E_DATA = 6       # 输出不符合预期（缺 PAYLOAD_END、零帧、全黑…）
E_PRE = 7        # 前置条件不满足（版本、短接线、文件缺失）

TOOLS = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.dirname(TOOLS)
PAYLOADS = os.path.join(ROOT, 'payloads')
LOGS = os.path.join(ROOT, 'logs')
ACCEPT = os.path.join(LOGS, 'accept')


def ensure_dir(p):
    if p and not os.path.isdir(p):
        os.makedirs(p, exist_ok=True)
    return p


def payload(name):
    p = os.path.join(PAYLOADS, name)
    with open(p, 'r', encoding='utf-8') as f:
        return f.read()


def with_cfg(text, cfg):
    """在 payload 前面注入 CFG 字典；payload 里用 CFG.get(...) 取参数。"""
    return 'CFG = %r\n' % (cfg,) + text


def run_id(prefix=''):
    return (prefix + time.strftime('%Y%m%d_%H%M%S')) if prefix else time.strftime('%Y%m%d_%H%M%S')


def emit(json_mode, status, **kv):
    """打印人读摘要 + 机读块（或单个 JSON）。返回进程退出码。"""
    kv['status'] = status
    kv['ts'] = time.strftime('%Y-%m-%dT%H:%M:%S')
    if json_mode:
        print(json.dumps(kv, ensure_ascii=False, sort_keys=True))
    else:
        print('')
        print('--- SUMMARY ---')
        keys = ['status'] + sorted(k for k in kv if k != 'status')
        for k in keys:
            print('%s=%s' % (k, kv[k]))
    code = E_OK if status == 'ok' else kv.get('_exit', E_DATA)
    return code


def finish(json_mode, status='ok', exit_code=None, **kv):
    if exit_code is not None:
        kv['_exit'] = exit_code
    return emit(json_mode, status, **kv)


def die(json_mode, status, exit_code, msg, **kv):
    print('[X] %s' % msg, file=sys.stderr)
    kv['msg'] = msg
    return finish(json_mode, status, exit_code, **kv)


def add_common_args(ap):
    ap.add_argument('--port', default='auto', help='COM13 / auto')
    ap.add_argument('--timeout', type=float, default=None, help='总超时秒')
    ap.add_argument('--json', action='store_true', help='只输出 JSON')


def parse_kv_lines(text, prefix=''):
    """从板端 stdout 里抽 key=value 行（也容忍 "KEY value" 写法），返回 dict。"""
    out = {}
    for line in text.splitlines():
        line = line.strip()
        if not line or line.startswith('#'):
            continue
        if prefix and not line.startswith(prefix):
            continue
        if prefix:
            line = line[len(prefix):]
        if '=' in line:
            k, v = line.split('=', 1)
        else:
            parts = line.split(None, 1)
            if len(parts) != 2:
                continue
            k, v = parts
        out[k.strip()] = v.strip()
    return out


def read_jsonl(path):
    rows = []
    if not os.path.exists(path):
        return rows
    with open(path, 'r', encoding='utf-8') as f:
        for line in f:
            line = line.strip()
            if not line or line.startswith('#'):
                continue
            try:
                rows.append(json.loads(line))
            except ValueError:
                pass
    return rows


def exec_payload(b, name, cfg, timeout=30):
    """把 payloads/<name> 注入 CFG 后在板端执行，返回 (res, kv, ended)。"""
    code = with_cfg(payload(name), cfg)
    res = b.exec(code, timeout=timeout)
    kv = parse_kv_lines(res.out)
    return res, kv, ('PAYLOAD_END' in res.out)


def write_text(path, text):
    ensure_dir(os.path.dirname(path))
    with open(path, 'w', encoding='utf-8', newline='\n') as f:
        f.write(text)
    return path
