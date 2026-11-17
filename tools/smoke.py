#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""smoke.py —— 一次跑完所有前置检查，输出 PASS/FAIL 表（技能 env-doctor）

用法:
    python tools/smoke.py
    python tools/smoke.py --json

退出码: 0 全 PASS / 2 串口相关失败 / 6 其它失败
"""
import argparse
import ctypes
import os
import shutil
import sys
import time

import _common as C
import _wincom

CHECKS = []


def add(name, ok, detail='', skill=''):
    CHECKS.append({'check': name, 'ok': bool(ok), 'detail': detail, 'skill': skill})
    return ok


def main():
    ap = argparse.ArgumentParser(description='K230 技能包环境冒烟')
    ap.add_argument('--port', default='auto')
    ap.add_argument('--json', action='store_true')
    args = ap.parse_args()

    # 1. Python
    add('python_present', sys.version_info >= (3, 8), 'python %d.%d' % sys.version_info[:2])

    # 2. 工作区可写
    probe = os.path.join(C.ROOT, '_smoke_write.tmp')
    try:
        with open(probe, 'w') as f:
            f.write('x')
        os.remove(probe)
        add('workspace_writable', True, C.ROOT)
    except Exception as e:
        add('workspace_writable', False, str(e), 'env-doctor')

    # 3. 盘空间
    try:
        free_gb = shutil.disk_usage(C.ROOT).free / float(1 << 30)
        add('disk_free', free_gb > 0.5, '%.1f GB' % free_gb)
    except Exception as e:
        add('disk_free', False, str(e))

    # 4. 串口枚举
    ports = _wincom.find_ports()
    add('serial_port_found', bool(ports),
        ','.join('%s(%s)' % (k, v.split('\\')[-1]) for k, v in sorted(ports.items())),
        'recover-board')

    # 5~8. 打开 / DTR / 提示符 / raw REPL
    board = None
    if ports:
        from _mprepl import Board, BoardError
        try:
            board = Board(args.port).connect()
            add('port_openable', True, board.port)
            add('dtr_rts_ok', True, 'prompt received (DTR/RTS asserted)')
            add('repl_prompt', True, '>>> after Ctrl-C')
            try:
                board.enter_raw()
                add('raw_repl', True, 'Ctrl-A ok')
            except BoardError as e:
                add('raw_repl', False, e.msg, 'recover-board')
        except BoardError as e:
            add('port_openable', False, e.msg, 'recover-board')
            add('dtr_rts_ok', False, 'n/a')
            add('repl_prompt', False, e.detail or '', 'recover-board')
            add('raw_repl', False, 'n/a')
    else:
        for n in ('port_openable', 'dtr_rts_ok', 'repl_prompt', 'raw_repl'):
            add(n, False, 'no port', 'recover-board')

    # 9. 固件
    if board:
        try:
            code = ('import os\n'
                    'u = os.uname()\n'
                    'print("FW", u.version)\n'
                    'print("PAYLOAD_END")\n')
            r = board.exec(code, timeout=6)
            fw = ''
            for line in r.out.splitlines():
                if line.startswith('FW '):
                    fw = line[3:].strip()
            add('firmware_version', bool(fw) and r.ok, fw or (r.err or '')[:80])
        except Exception as e:
            add('firmware_version', False, str(e))
        try:
            board.close()
        except Exception:
            pass
    else:
        add('firmware_version', False, 'no board')

    # 10. MTP 设备（注册表判定，快）
    mtp = False
    detail = 'not found'
    try:
        import winreg
        k = winreg.OpenKey(winreg.HKEY_LOCAL_MACHINE,
                           r'SOFTWARE\Microsoft\Windows Portable Devices\Devices')
        i = 0
        while True:
            try:
                name = winreg.EnumKey(k, i)
            except OSError:
                break
            i += 1
            if 'VID_1209&PID_ABD1' in name.upper() or 'CANMV' in name.upper():
                mtp = True
                detail = name.split('#')[1] if '#' in name else name
    except Exception as e:
        detail = str(e)
    add('mtp_device_present', mtp, detail, 'pull-logs')

    # 11. logs 目录
    try:
        C.ensure_dir(C.LOGS)
        add('logs_dir', os.path.isdir(C.LOGS), C.LOGS)
    except Exception as e:
        add('logs_dir', False, str(e))

    # ---------- 输出 ----------
    width = max(len(c['check']) for c in CHECKS)
    if not args.json:
        print('%-*s  %-6s %s' % (width, 'CHECK', 'RESULT', 'DETAIL'))
        print('-' * (width + 40))
        for c in CHECKS:
            print('%-*s  %-6s %s' % (width, c['check'], 'PASS' if c['ok'] else 'FAIL', c['detail']))

    fails = [c for c in CHECKS if not c['ok']]
    summary = {'fail_count': len(fails), 'pass_count': len(CHECKS) - len(fails)}
    if fails:
        first = fails[0]
        summary['first_fail'] = first['check']
        summary['next_skill'] = first['skill'] or 'recover-board'
        if not args.json:
            print('')
            print('[!] 第一个失败项: %s → 先跑技能 %s' % (first['check'], summary['next_skill']))
        return C.finish(args.json, 'fail', C.E_PORT if any(
            c['check'].startswith(('serial', 'port', 'dtr', 'repl', 'raw')) for c in fails) else C.E_DATA,
            **summary)
    return C.finish(args.json, 'ok', **summary)


if __name__ == '__main__':
    sys.exit(main())
