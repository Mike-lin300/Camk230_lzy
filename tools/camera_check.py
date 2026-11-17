#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""camera_check.py —— 摄像头通路自检（技能 camera-check）

不看图也能判断"镜头有没有画面"：在板端采样亮度分布，回传数值。
人要看画面：python tools/accept.py --skill camera-check

用法:
    python tools/camera_check.py
    python tools/camera_check.py --width 800 --height 480 --save
    python tools/camera_check.py --json
退出码: 0 正常 / 2 无端口 / 3 端口占用 / 4 超时 / 5 板端异常 / 6 画面异常(全黑/全白)
"""
import argparse
import sys
import time

import _common as C
from _mprepl import Board, BoardError


def main():
    ap = argparse.ArgumentParser(description='K230 摄像头通路自检')
    ap.add_argument('--width', type=int, default=640)
    ap.add_argument('--height', type=int, default=480)
    ap.add_argument('--save', action='store_true', help='在板端存一张 JPEG 到 /data/live/')
    C.add_common_args(ap)
    args = ap.parse_args()

    cfg = {'display': 'none', 'width': args.width, 'height': args.height,
           'save': 1 if args.save else 0, 'frames': 30}

    try:
        b = Board(args.port).connect()
    except BoardError as e:
        return C.die(args.json, 'port_error', e.code, e.msg, detail=e.detail)

    t0 = time.time()
    try:
        res, kv, ended = C.exec_payload(b, 'camera.py', cfg, timeout=args.timeout or 45)
    except BoardError as e:
        b.close()
        return C.die(args.json, 'repl_error', e.code, e.msg, detail=e.detail, port=b.port)
    b.close()

    if not res.ok:
        return C.die(args.json, 'script_error', C.E_SCRIPT, '板端脚本异常',
                     detail=(res.err or '').strip()[:400], port=b.port)
    if not ended:
        return C.die(args.json, 'incomplete', C.E_DATA, '缺少 PAYLOAD_END（可能超时/被中断）',
                     detail=res.out[-300:], port=b.port)

    try:
        luma = int(kv.get('LUMA_MEAN', -1))
        dark = float(kv.get('DARK_RATIO', '1'))
        w = int(kv.get('W', 0))
        h = int(kv.get('H', 0))
    except ValueError:
        luma, dark, w, h = -1, 1.0, 0, 0
    fps = kv.get('FPS', '?')

    print('[+] 采集：%dx%d  亮度均值=%d  暗像素比例=%.2f  FPS=%s'
          % (w, h, luma, dark, fps))
    if kv.get('SAVED'):
        print('    板端已存图：%s' % kv['SAVED'])
        print('    拉回：python tools/pull_logs.py --remote data/live')

    verdict = 'ok'
    if w <= 0 or h <= 0:
        verdict, reason = 'bad', '分辨率读到 0'
    elif 0 <= luma < 8 or dark > 0.95:
        verdict, reason = 'too_dark', '画面几乎全黑：镜头盖/排线/曝光'
    elif luma > 250:
        verdict, reason = 'too_bright', '画面过曝：强光直射'
    else:
        reason = '亮度分布正常'

    print('    判定：%s（%s）' % (verdict, reason))
    out = {'skill': 'camera-check', 'port': b.port, 'width': w, 'height': h,
           'luma_mean': luma, 'dark_ratio': '%.3f' % dark, 'fps': fps,
           'verdict': verdict, 'elapsed_ms': int((time.time() - t0) * 1000)}
    if kv.get('SAVED'):
        out['board_path'] = kv['SAVED']
    if verdict == 'ok':
        return C.finish(args.json, 'ok', **out)
    out['reason'] = reason
    return C.finish(args.json, verdict, C.E_DATA, **out)


if __name__ == '__main__':
    sys.exit(main())
