#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""display.py —— 3.5" MIPI 屏点亮 / 预览（技能 display-lcd）

用法:
    python tools/display.py                       # 10 秒彩条 + 文字
    python tools/display.py --mode camera --seconds 20
    python tools/display.py --json
退出码: 0 已出图（屏是否真亮需人确认） / 2 无端口 / 3 端口占用 / 4 超时 / 5 板端异常 / 6 无帧
"""
import argparse
import sys

import _common as C
from _mprepl import Board, BoardError


def main():
    ap = argparse.ArgumentParser(description='K230 3.5 寸 MIPI 屏测试（ST7701）')
    ap.add_argument('--seconds', type=int, default=10)
    ap.add_argument('--mode', choices=['bars', 'camera'], default='bars')
    C.add_common_args(ap)
    args = ap.parse_args()

    cfg = {'seconds': args.seconds, 'mode': args.mode, 'width': 800, 'height': 480,
           'display': 'ide'}

    try:
        b = Board(args.port).connect()
    except BoardError as e:
        return C.die(args.json, 'port_error', e.code, e.msg, detail=e.detail)

    try:
        res, kv, ended = C.exec_payload(b, 'display.py', cfg, timeout=args.seconds + 40)
    except BoardError as e:
        b.close()
        return C.die(args.json, 'repl_error', e.code, e.msg, detail=e.detail, port=b.port)
    b.close()

    if not res.ok:
        return C.die(args.json, 'script_error', C.E_SCRIPT, '板端显示初始化失败',
                     detail=(res.err or '').strip()[:400], port=b.port)
    if not ended:
        return C.die(args.json, 'incomplete', C.E_DATA, '缺少 PAYLOAD_END',
                     detail=res.out[-300:], port=b.port)

    frames = int(kv.get('FRAMES', 0) or 0)
    print('[+] 已显示 %d 帧（%s），FPS=%s' % (frames, kv.get('MODE', args.mode), kv.get('FPS', '?')))
    print('    LCD=%s  RES=%s' % (kv.get('LCD', '?'), kv.get('RES', '?')))
    print('    >> 请人眼确认屏幕：应看到 红/绿/蓝 三条色带 + "K230 LCD OK"')

    out = {'skill': 'display-lcd', 'port': b.port, 'lcd': kv.get('LCD', 'ST7701'),
           'res': kv.get('RES', '800x480'), 'mode': args.mode,
           'frames': frames, 'fps': kv.get('FPS', '?'),
           'needs_human_confirm': 'true'}
    if frames == 0:
        return C.finish(args.json, 'no_frames', C.E_DATA, **out)
    return C.finish(args.json, 'ok', **out)


if __name__ == '__main__':
    sys.exit(main())
