#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""gpio.py —— GPIO / 板载灯 / 按键（技能 gpio-led）

用法:
    python tools/gpio.py --action on
    python tools/gpio.py --action blink --times 5 --interval-ms 150
    python tools/gpio.py --action key --times 10        # 10 秒内按了几次板载 KEY
    python tools/gpio.py --action on --pin 2            # 排针 pin7 的外接 LED
退出码: 0 成功 / 2 无端口 / 3 端口占用 / 4 超时 / 5 板端异常 / 7 该脚不可用作 GPIO
"""
import argparse
import sys

import _common as C
from _mprepl import Board, BoardError


def main():
    ap = argparse.ArgumentParser(description='K230 GPIO 控制')
    ap.add_argument('--action', choices=['on', 'off', 'blink', 'read', 'key'], default='on')
    ap.add_argument('--pin', type=int, default=None,
                    help='不填则自动：key→21，其它→52（52=板载灯 21=板载KEY 2=pin7）')
    ap.add_argument('--times', '--time', type=int, default=3, help='blink=次数 key=秒数')
    ap.add_argument('--interval-ms', type=int, default=200)
    C.add_common_args(ap)
    args = ap.parse_args()

    pin = args.pin if args.pin is not None else (21 if args.action == 'key' else 52)
    if args.action == 'key' and pin != 21:
        print('[!] 注意：key 动作读的是 --pin=%d；板载 KEY 通常是 21' % pin)

    cfg = {'action': args.action, 'pin': pin, 'times': args.times,
           'interval_ms': args.interval_ms, 'display': 'none'}

    try:
        b = Board(args.port).connect()
    except BoardError as e:
        return C.die(args.json, 'port_error', e.code, e.msg, detail=e.detail)

    to = args.timeout or (args.times + 10 if args.action == 'key' else 20)
    try:
        res, kv, ended = C.exec_payload(b, 'gpio.py', cfg, timeout=to)
    except BoardError as e:
        b.close()
        return C.die(args.json, 'repl_error', e.code, e.msg, detail=e.detail, port=b.port)
    b.close()

    print(res.out.strip())

    if not res.ok:
        return C.die(args.json, 'script_error', C.E_SCRIPT, '板端脚本异常',
                     detail=(res.err or '').strip()[:300], port=b.port)
    if not ended:
        return C.die(args.json, 'incomplete', C.E_DATA, '缺少 PAYLOAD_END',
                     detail=res.out[-200:], port=b.port)
    if kv.get('ERR_PIN_CONST'):
        return C.die(args.json, 'bad_pin', C.E_PRE,
                     'GPIO%d 在 FPIOA 里没有对应常量，换一个脚（pinout 技能可查）' % pin,
                     port=b.port)

    out = {'skill': 'gpio-led', 'port': b.port, 'action': args.action, 'pin': pin}
    for k in ('STATE', 'VALUE', 'PRESSES'):
        if k in kv:
            out[k.lower()] = kv[k]
    return C.finish(args.json, 'ok', **out)


if __name__ == '__main__':
    sys.exit(main())
