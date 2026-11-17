#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""run_code.py —— 在板子上执行任意脚本（技能 run-code）

用法:
    python tools/run_code.py payloads/probe.py
    python tools/run_code.py --code "import os; print(os.uname())"
    python tools/run_code.py my_test.py --display ide --timeout 60

约定:
    - 执行前会注入 CFG 字典（payload 可用 CFG.get('display') 等）
    - 板端 stdout 原样转发给人；机器读 SUMMARY
退出码: 0 成功 / 2 无端口 / 3 端口占用 / 4 超时 / 5 板端异常
"""
import argparse
import os
import sys
import time

import _common as C
from _mprepl import Board, BoardError


def main():
    ap = argparse.ArgumentParser(description='在 K230 上执行一段脚本')
    ap.add_argument('file', nargs='?', help='本地 .py 文件')
    ap.add_argument('--code', help='直接给一小段代码')
    ap.add_argument('--display', choices=['none', 'ide'], default='none',
                    help="none=不推图(AI) ide=推图到 IDE(人验收)")
    ap.add_argument('--no-cfg', action='store_true', help='不注入 CFG')
    C.add_common_args(ap)
    args = ap.parse_args()

    if args.file:
        if not os.path.exists(args.file):
            return C.die(args.json, 'bad_input', C.E_PRE, '文件不存在: %s' % args.file)
        with open(args.file, 'r', encoding='utf-8') as f:
            code = f.read()
        src = os.path.basename(args.file)
    elif args.code:
        code = args.code
        src = 'inline'
    else:
        ap.error('需要 file 或 --code')

    if not args.no_cfg:
        code = C.with_cfg(code, {'display': args.display})

    t0 = time.time()
    try:
        b = Board(args.port).connect()
    except BoardError as e:
        return C.die(args.json, 'port_error', e.code, e.msg, detail=e.detail, src=src)

    to = args.timeout if args.timeout else max(20.0, 5.0 + len(code) / 200.0)
    try:
        res = b.exec(code, timeout=to)
    except BoardError as e:
        b.close()
        return C.die(args.json, 'repl_error', e.code, e.msg, detail=e.detail, src=src, port=b.port)
    b.close()
    dur = int((time.time() - t0) * 1000)

    print('--- board stdout ---')
    print(res.out.rstrip())
    if res.err.strip():
        print('--- board stderr ---')
        print(res.err.strip())

    kv = {'skill': 'run-code', 'src': src, 'port': getattr(b, 'port', args.port),
          'lines': len(res.out.splitlines()), 'duration_ms': dur, 'display': args.display}
    if not res.ok:
        kv['detail'] = (res.err or '').strip().splitlines()[-1][:200] if res.err else ''
        return C.finish(args.json, 'script_error', C.E_SCRIPT, **kv)
    return C.finish(args.json, 'ok', **kv)


if __name__ == '__main__':
    sys.exit(main())
