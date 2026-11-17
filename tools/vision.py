#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""vision.py —— 在线视觉检测（技能 vision-blob-online / vision-apriltag-online）

逐帧结果经串口回传，本地落 CSV；不写板端磁盘、不依赖 IDE。
人要看画面：python tools/accept.py --skill vision-apriltag

用法:
    python tools/vision.py --mode apriltag --frames 120
    python tools/vision.py --mode blob --threshold "30,100,15,127,15,127" --min-pixels 300
    python tools/vision.py --mode apriltag --display ide     # 推图到 IDE（人验收）
退出码: 0 检出 / 2 无端口 / 3 端口占用 / 4 超时 / 5 板端异常 / 6 零帧 / 7 零检出
"""
import argparse
import csv
import os
import sys
import time

import _common as C
from _mprepl import Board, BoardError

HEADER = ['frame', 'found', 'id', 'cx', 'cy', 'w', 'h', 'rot']


def main():
    ap = argparse.ArgumentParser(description='K230 在线视觉检测')
    ap.add_argument('--mode', choices=['blob', 'apriltag'], default='apriltag')
    ap.add_argument('--frames', type=int, default=120)
    ap.add_argument('--width', type=int, default=320)
    ap.add_argument('--height', type=int, default=240)
    ap.add_argument('--display', choices=['none', 'ide'], default='none')
    ap.add_argument('--threshold', default='30,100,15,127,15,127',
                    help='blob 模式 LAB 阈值，逗号分隔 6 个数')
    ap.add_argument('--min-pixels', type=int, default=300)
    ap.add_argument('--allow-empty', action='store_true',
                    help='零检出也返回 0（只验通路时用）')
    ap.add_argument('--csv', help='CSV 输出路径（默认 logs/live_<mode>_<ts>.csv）')
    C.add_common_args(ap)
    args = ap.parse_args()

    try:
        th = [int(x) for x in args.threshold.split(',')]
        assert len(th) == 6
    except Exception:
        return C.die(args.json, 'bad_input', C.E_PRE, '--threshold 需要 6 个整数')

    cfg = {'mode': args.mode, 'display': args.display, 'frames': args.frames,
           'width': args.width, 'height': args.height, 'threshold': th,
           'min_pixels': args.min_pixels}

    if args.csv:
        csv_path = args.csv
    else:
        C.ensure_dir(C.LOGS)
        csv_path = os.path.join(C.LOGS, 'live_%s_%s.csv' % (args.mode, C.run_id()))

    try:
        b = Board(args.port).connect()
    except BoardError as e:
        return C.die(args.json, 'port_error', e.code, e.msg, detail=e.detail)

    timeout = args.timeout or max(args.frames / 8.0 + 25.0, 30.0)
    try:
        res, kv, ended = C.exec_payload(b, 'vision.py', cfg, timeout=timeout)
    except BoardError as e:
        b.close()
        return C.die(args.json, 'repl_error', e.code, e.msg, detail=e.detail,
                     port=b.port, frames_done=-1)
    b.close()

    rows = []
    for line in res.out.splitlines():
        if line.startswith('R,'):
            parts = line[2:].split(',')
            if len(parts) >= 8:
                rows.append(parts[:8])

    C.ensure_dir(os.path.dirname(csv_path))
    with open(csv_path, 'w', encoding='utf-8', newline='\n') as f:
        w = csv.writer(f)
        w.writerow(HEADER)
        for r in rows:
            w.writerow(r)

    if not res.ok:
        return C.die(args.json, 'script_error', C.E_SCRIPT, '板端脚本异常',
                     detail=(res.err or '').strip()[:400], csv=csv_path, port=b.port)
    if not ended:
        return C.die(args.json, 'incomplete', C.E_DATA, '缺少 PAYLOAD_END',
                     detail=res.out[-300:], rows=len(rows), csv=csv_path, port=b.port)

    frames = int(kv.get('FRAMES', len(rows)) or 0)
    hits = int(kv.get('HITS', 0) or 0)
    fps = kv.get('FPS_MEAN', '?')
    ratio = (hits / float(frames)) if frames else 0.0

    print('[+] 模式=%s  帧数=%d  命中=%d (%.0f%%)  平均FPS=%s'
          % (args.mode, frames, hits, ratio * 100, fps))
    print('    CSV：%s' % csv_path)

    out = {'skill': 'vision-%s-online' % args.mode, 'mode': args.mode,
           'port': b.port, 'frames': frames, 'hits': hits,
           'hit_ratio': '%.3f' % ratio, 'fps_median': fps,
           'display': args.display, 'csv': csv_path}
    if frames == 0:
        return C.finish(args.json, 'no_frames', C.E_DATA, **out)
    if hits == 0:
        out['hint'] = '零检出：确认目标在画面内；或先跑 camera-check 确认有画面'
        return C.finish(args.json, 'no_detection',
                        0 if args.allow_empty else C.E_PRE, **out)
    return C.finish(args.json, 'ok', **out)


if __name__ == '__main__':
    sys.exit(main())
