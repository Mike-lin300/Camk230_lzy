#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""record.py —— 离线录制（技能 offline-record）

板端落盘到 /data/logs/<run_id>/（CSV + 抽帧 JPEG），跑满时长自动结束。
拷回本地用 pull_logs.py。

用法:
    python tools/record.py start --duration 180
    python tools/record.py start --mode blob --duration 30
    python tools/record.py status            # 看板端已有哪些 run
退出码: 0 完成 / 2 无端口 / 3 端口占用 / 4 超时 / 5 板端异常 / 6 不完整 / 7 参数错
"""
import argparse
import sys
import time

import _common as C
from _mprepl import Board, BoardError

STATUS_CODE = '''
import os
root = '/data/logs'
try:
    names = os.listdir(root)
except OSError:
    names = []
for n in names:
    d = root + '/' + n
    try:
        files = os.listdir(d)
    except OSError:
        files = []
    try:
        nframes = len(os.listdir(d + '/frames'))
    except OSError:
        nframes = 0
    print('RUN=%s files=%d frames=%d' % (n, len(files), nframes))
print('PAYLOAD_END')
'''


def cmd_status(b, json_mode):
    res = b.exec(STATUS_CODE, timeout=12)
    runs = [l[4:] for l in res.out.splitlines() if l.startswith('RUN=')]
    print('[+] 板端 /data/logs 共 %d 个 run' % len(runs))
    for r in runs:
        print('    %s' % r)
    return C.finish(json_mode, 'ok', skill='offline-record', action='status',
                    runs=len(runs), list=';'.join(runs) or '-')


def cmd_start(b, args, json_mode):
    rid = args.run_id or ('%s_%s' % (args.mode, C.run_id()))
    cfg = {'mode': args.mode, 'duration_s': args.duration, 'width': args.width,
           'height': args.height, 'save_interval_ms': args.save_interval_ms,
           'jpeg_quality': args.quality, 'run_id': rid, 'display': 'none'}
    t0 = time.time()
    try:
        res, kv, ended = C.exec_payload(b, 'record.py', cfg,
                                        timeout=args.duration + 120)
    except BoardError as e:
        return C.die(json_mode, 'repl_error', e.code, e.msg, detail=e.detail, run_id=rid)
    dur = int((time.time() - t0) * 1000)

    if not res.ok:
        return C.die(json_mode, 'script_error', C.E_SCRIPT, '板端录制异常',
                     detail=(res.err or '').strip()[:400], run_id=rid)
    if not ended:
        return C.die(json_mode, 'incomplete', C.E_DATA, '缺少 PAYLOAD_END（录制被中断）',
                     detail=res.out[-300:], run_id=rid)

    print('[+] 录制完成：%s 帧，命中 %s，存图 %s 张'
          % (kv.get('FRAMES'), kv.get('HITS'), kv.get('SAVED')))
    print('    板端目录：%s' % kv.get('DIR'))
    print('    下一步：python tools/pull_logs.py')
    return C.finish(json_mode, 'ok', skill='offline-record', action='start',
                    run_id=kv.get('RUN_ID', rid), board_dir=kv.get('DIR', ''),
                    frames=kv.get('FRAMES'), hits=kv.get('HITS'),
                    saved=kv.get('SAVED'), duration_ms=dur)


def main():
    ap = argparse.ArgumentParser(description='K230 离线录制')
    ap.add_argument('cmd', nargs='?', default='start', choices=['start', 'status'])
    ap.add_argument('--mode', choices=['blob', 'apriltag'], default='apriltag')
    ap.add_argument('--duration', type=int, default=180, help='录制秒数（默认 180，上限 600）')
    ap.add_argument('--width', type=int, default=320)
    ap.add_argument('--height', type=int, default=240)
    ap.add_argument('--save-interval-ms', type=int, default=1000)
    ap.add_argument('--quality', type=int, default=75)
    ap.add_argument('--run-id', help='自定义运行目录名')
    C.add_common_args(ap)
    args = ap.parse_args()

    if args.duration < 1 or args.duration > 600:
        return C.die(args.json, 'bad_input', C.E_PRE, '--duration 需在 1..600 秒之间')

    try:
        b = Board(args.port).connect()
    except BoardError as e:
        return C.die(args.json, 'port_error', e.code, e.msg, detail=e.detail)

    try:
        if args.cmd == 'status':
            return cmd_status(b, args.json)
        return cmd_start(b, args, args.json)
    finally:
        b.close()


if __name__ == '__main__':
    sys.exit(main())
