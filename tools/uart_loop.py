#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""uart_loop.py —— UART1 回环自测（技能 uart-loopback）

前置（需要人）：一根杜邦线短接排针 pin8(TX1) 与 pin10(RX1)。

用法:
    python tools/uart_loop.py
    python tools/uart_loop.py --baud 115200 --count 5
退出码: 0 全通 / 2 无端口 / 3 端口占用 / 4 超时 / 5 板端异常 / 6 部分丢帧 / 7 完全收不到（多半没短接）
"""
import argparse
import sys

import _common as C
from _mprepl import Board, BoardError


def main():
    ap = argparse.ArgumentParser(description='K230 UART 回环测试（UART1 / UART2）')
    ap.add_argument('--uart', type=int, choices=[1, 2], default=1,
                    help='1=pin8/pin10(GPIO3/4)  2=GPIO11/12(端子口 TX2/RX2)')
    ap.add_argument('--baud', type=int, default=115200)
    ap.add_argument('--count', type=int, default=5)
    C.add_common_args(ap)
    args = ap.parse_args()

    cfg = {'uart': args.uart, 'baud': args.baud, 'count': args.count,
           'interval_ms': 100, 'display': 'none'}

    try:
        b = Board(args.port).connect()
    except BoardError as e:
        return C.die(args.json, 'port_error', e.code, e.msg, detail=e.detail)

    try:
        res, kv, ended = C.exec_payload(b, 'uart_loop.py', cfg,
                                        timeout=args.timeout or (args.count * 0.5 + 20))
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

    try:
        rx = int(kv.get('RX_BYTES', 0))
        match = int(kv.get('MATCH_FRAMES', 0))
        expect = int(kv.get('EXPECT_FRAMES', args.count))
    except ValueError:
        rx, match, expect = 0, 0, args.count

    out = {'skill': 'uart-loopback', 'port': b.port, 'uart': args.uart, 'baud': args.baud,
           'rx_bytes': rx, 'match_frames': match, 'expect_frames': expect}

    if rx == 0:
        out['hint'] = ('收不到任何字节：UART%d 需把 TX 与 RX 短接（UART1=pin8/pin10，UART2=GPIO11/12）' % args.uart)
        return C.finish(args.json, 'no_echo', C.E_PRE, **out)
    if match < expect:
        return C.finish(args.json, 'partial', C.E_DATA, **out)
    return C.finish(args.json, 'ok', **out)


if __name__ == '__main__':
    sys.exit(main())
