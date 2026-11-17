#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""recover.py —— 板子失联/自启锁死的半自动恢复（技能 recover-board）

默认 **dry-run**：只诊断 + 打印将要做的动作，不动任何文件。
加 --yes 才把 sdcard/main.py 改名为 main.py.bak（保留现场，不删除）。

用法:
    python tools/recover.py                 # 诊断
    python tools/recover.py --yes           # 执行改名
    python tools/recover.py --yes --reset   # 改名后软复位
    python tools/recover.py --release-port  # 只查端口是否被占用

退出码: 0 已恢复/无需恢复 / 2 无端口 / 3 端口被占 / 4 REPL 无响应 / 6 需物理断电
"""
import argparse
import sys
import time

import _common as C
import _wincom
from _mprepl import Board, BoardError

MAIN = '/sdcard/main.py'
BAK = '/sdcard/main.py.bak'


def check_main(b):
    code = ('import os\n'
            'try:\n'
            '    s = os.stat(%r)\n'
            '    print("MAIN_SIZE", s[6])\n'
            'except OSError:\n'
            '    print("MAIN_ABSENT")\n'
            'print("PAYLOAD_END")\n' % MAIN)
    res = b.exec(code, timeout=8)
    if not res.ok:
        return None, res.err
    for line in res.out.splitlines():
        if line.startswith('MAIN_SIZE'):
            return int(line.split()[1]), None
    return 0, None


def rename_main(b):
    code = ('import os\n'
            'os.rename(%r, %r)\n'
            'print("RENAMED")\n'
            'print("PAYLOAD_END")\n' % (MAIN, BAK))
    res = b.exec(code, timeout=8)
    return res.ok and 'RENAMED' in res.out, res.err


def main():
    ap = argparse.ArgumentParser(description='CanMV K230 半自动恢复')
    ap.add_argument('--yes', action='store_true', help='真的执行改名（默认只诊断）')
    ap.add_argument('--reset', action='store_true', help='操作后软复位')
    ap.add_argument('--release-port', action='store_true', help='只检查端口是否可用')
    C.add_common_args(ap)
    args = ap.parse_args()

    ports = _wincom.find_ports()
    if not ports:
        return C.die(args.json, 'no_port', C.E_PORT,
                     '注册表里没有任何串口：先查供电与 Type-C 数据线，再按 RST')

    if args.release_port:
        try:
            from _wincom import SerialPort
            sp = SerialPort(list(ports)[0]).open()
            sp.close()
            return C.finish(args.json, 'ok', skill='recover-board',
                            action='port_free', port=list(ports)[0])
        except Exception as e:
            return C.die(args.json, 'port_busy', C.E_BUSY,
                         '端口被占用：关闭 CanMV IDE / 串口助手后重试', detail=str(e))

    b = Board(args.port)
    try:
        b.connect()
    except BoardError as e:
        if e.code == C.E_BUSY:
            return C.die(args.json, 'port_busy', C.E_BUSY,
                         '端口被占用：先关掉 CanMV IDE（同一 COM 不能共享）', detail=e.detail)
        if e.code == C.E_REPL:
            # 连上了但没有提示符 → 试软复位
            print('[*] Ctrl-C 无响应，尝试软复位（Ctrl-D）…')
            try:
                b.sp.write(b'\x04')
                data, ok = b.sp.read_until(b'>>>', timeout=10)
                if not ok:
                    raise BoardError(C.E_REPL, 'still no prompt')
                print('[+] 软复位后恢复提示符')
            except Exception:
                b.close()
                print('[!] 软复位也无效。确定性下一步：')
                print('    1) 拔掉 Type-C，等 5 秒，重新插上（物理断电）')
                print('    2) 再用本工具复查：python tools/recover.py --release-port')
                print('    3) 仍失败 → 用读卡器删 sdcard/main.py，或重烧镜像')
                return C.die(args.json, 'needs_power_cycle', C.E_DATA,
                             'REPL 无响应，需要物理断电后重试', port=list(ports)[0])
        else:
            return C.die(args.json, 'port_error', e.code, e.msg, detail=e.detail)

    size, err = check_main(b)
    if size is None:
        b.close()
        return C.die(args.json, 'script_error', C.E_SCRIPT, '无法读取 main.py 状态', detail=str(err))

    action = 'none'
    if size:
        print('[*] 发现自启脚本 %s（%d 字节）' % (MAIN, size))
        if args.yes:
            ok, rerr = rename_main(b)
            if not ok:
                b.close()
                return C.die(args.json, 'rename_failed', C.E_SCRIPT,
                             '改名失败', detail=str(rerr))
            print('[+] 已改名 → %s' % BAK)
            action = 'renamed'
        else:
            print('[!] dry-run：未改动。要执行请加 --yes')
            print('    将执行：os.rename(%r, %r)' % (MAIN, BAK))
            action = 'planned'
    else:
        print('[+] 没有 main.py，REPL 正常，无需恢复')

    if args.reset and action in ('renamed', 'none'):
        try:
            b.soft_reset()
            print('[+] 软复位完成')
        except Exception as e:
            print('[!] 软复位异常: %s' % e)
    b.close()

    return C.finish(args.json, 'ok', skill='recover-board', action=action,
                    main_size=size, port=list(ports)[0])


if __name__ == '__main__':
    sys.exit(main())
