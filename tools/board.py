#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""board.py —— 板子在线判定 + 事实采集（技能 board-online）

用法:
    python tools/board.py
    python tools/board.py --port COM13 --json

退出码: 0 在线 / 2 无端口 / 3 端口被占 / 4 REPL 无响应 / 6 输出不完整
"""
import argparse
import sys

import _common as C
from _mprepl import Board, BoardError


def main():
    ap = argparse.ArgumentParser(description='CanMV K230 在线判定')
    C.add_common_args(ap)
    ap.add_argument('--raw', action='store_true', help='同时打印板端原始输出')
    args = ap.parse_args()

    try:
        b = Board(args.port).connect()
    except BoardError as e:
        return C.die(args.json, 'port_error', e.code, e.msg, detail=e.detail, port=args.port)

    try:
        code = C.payload('probe.py')
    except (IOError, OSError) as e:
        b.close()
        return C.die(args.json, 'missing_payload', C.E_PRE, 'payload 缺失: %s' % e)

    try:
        res = b.exec(code, timeout=args.timeout or 12)
    except BoardError as e:
        b.close()
        return C.die(args.json, 'repl_error', e.code, e.msg, detail=e.detail, port=b.port)
    b.close()

    if args.raw:
        print('--- board raw ---')
        print(res.out)
        if res.err:
            print('--- board stderr ---')
            print(res.err)

    if not res.ok:
        return C.die(args.json, 'script_error', C.E_SCRIPT,
                     '板端脚本异常', detail=(res.err or '').strip()[:400], port=b.port)
    if 'PAYLOAD_END' not in res.out:
        return C.die(args.json, 'incomplete', C.E_DATA,
                     '输出缺少 PAYLOAD_END（脚本未跑完）',
                     detail=res.out[-300:], port=b.port)

    kv = C.parse_kv_lines(res.out)
    print('[+] %s 在线' % (b.port or ''))
    print('    固件   : %s' % kv.get('fw_version', '?'))
    print('    机型   : %s' % kv.get('fw_machine', '?'))
    print('    芯片ID : %s' % kv.get('chipid', '?'))
    print('    温度   : %s C' % kv.get('temp_c', '?'))
    print('    空闲内存: %s B' % kv.get('mem_free', '?'))
    print('    卡容量 : %s KB 可用 %s KB' % (kv.get('fs_total_kb', '?'), kv.get('fs_free_kb', '?')))
    mods = [k[4:] for k, v in kv.items() if k.startswith('mod_') and v == '1']
    print('    可用模块: %s' % (', '.join(mods) or 'none'))

    out = dict(kv)
    out['port'] = b.port
    out['skill'] = 'board-online'
    return C.finish(args.json, 'ok', **out)


if __name__ == '__main__':
    sys.exit(main())
