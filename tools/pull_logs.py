#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""pull_logs.py —— 把板端 /data/logs 拉到本地 logs/（技能 pull-logs）

板子在 Windows 上是 MTP 便携设备（无盘符），只能走 Shell 命名空间，
所以真正干活的是 tools/_mtp_pull.ps1（PowerShell + Shell COM），本脚本负责
参数、超时、机读摘要与退出码。

用法:
    python tools/pull_logs.py
    python tools/pull_logs.py --only apriltag_20261117_204500
    python tools/pull_logs.py --remote data/live --dest logs/live
退出码: 0 成功 / 2 找不到设备 / 4 拷贝命令失败 / 7 远端路径不存在
"""
import argparse
import os
import subprocess
import sys

import _common as C

PS1 = os.path.join(C.TOOLS, '_mtp_pull.ps1')


def main():
    ap = argparse.ArgumentParser(description='从 CanMV MTP 设备拉取日志')
    ap.add_argument('--remote', default='data/logs', help='设备内路径，默认 data/logs')
    ap.add_argument('--dest', default=C.LOGS, help='本地目标目录，默认 logs/')
    ap.add_argument('--only', help='只拉某个 run 目录')
    ap.add_argument('--force', action='store_true', help='覆盖已存在')
    ap.add_argument('--timeout', type=float, default=300, help='总超时秒')
    ap.add_argument('--json', action='store_true')
    args = ap.parse_args()

    if not os.path.exists(PS1):
        return C.die(args.json, 'missing_helper', C.E_PRE, '缺少 %s' % PS1)

    cmd = ['powershell', '-NoProfile', '-ExecutionPolicy', 'Bypass', '-File', PS1,
           '-Remote', args.remote, '-Dest', args.dest]
    if args.only:
        cmd += ['-Only', args.only]
    if args.force:
        cmd += ['-Force']

    try:
        p = subprocess.run(cmd, capture_output=True, timeout=args.timeout)
    except subprocess.TimeoutExpired:
        return C.die(args.json, 'timeout', C.E_DATA, 'MTP 拉取超时（%.0fs）' % args.timeout,
                     remote=args.remote)

    text = (p.stdout or b'').decode('utf-8', 'replace')
    kv = {}
    pulled = []
    current = None
    for line in text.splitlines():
        if '=' not in line:
            continue
        k, v = line.split('=', 1)
        k, v = k.strip(), v.strip()
        if k == 'PULLED':
            current = v
            pulled.append(v)
        elif k == 'FILES' and current:
            kv.setdefault('files_' + current, v)
        elif k == 'BYTES' and current:
            kv.setdefault('bytes_' + current, v)
        else:
            kv[k] = v

    result = kv.get('RESULT', 'unknown')
    if result == 'no_device':
        return C.die(args.json, 'no_device', C.E_PORT,
                     '「此电脑」里没有 CanMV 便携设备：查供电/Type-C 数据线', remote=args.remote)
    if result == 'missing':
        return C.die(args.json, 'remote_missing', C.E_PRE,
                     '设备内没有 /%s：先跑 tools/record.py start' % args.remote,
                     remote=args.remote)
    if p.returncode not in (0,):
        return C.die(args.json, 'pull_failed', C.E_DATA,
                     '拉取失败(rc=%d)' % p.returncode, detail=text[-400:])

    # 校验：拉回来的 run 里应该有 data.csv
    valid = 0
    for name in pulled:
        d = os.path.join(args.dest, name)
        if os.path.isfile(os.path.join(d, 'data.csv')):
            valid += 1

    print('[+] 拉取 %d 项，跳过 %d 项 → %s'
          % (int(kv.get('PULLED_COUNT', 0)), int(kv.get('SKIPPED_COUNT', 0)), args.dest))
    for name in pulled:
        print('    %-28s files=%s bytes=%s' % (name, kv.get('files_' + name, '?'),
                                               kv.get('bytes_' + name, '?')))
    if pulled and valid < len(pulled):
        print('[!] 有 %d 项缺 data.csv（可能仍在写入/被中断）' % (len(pulled) - valid))

    out = {'skill': 'pull-logs', 'remote': args.remote, 'dest': args.dest,
           'pulled_count': int(kv.get('PULLED_COUNT', 0)),
           'skipped_count': int(kv.get('SKIPPED_COUNT', 0)),
           'runs': ';'.join(pulled) or '-', 'valid_runs': valid}
    if pulled:
        out['last_run'] = pulled[-1]
        out['last_run_dir'] = os.path.join(args.dest, pulled[-1])
    return C.finish(args.json, 'ok' if valid > 0 or not pulled else 'partial', **out)


if __name__ == '__main__':
    sys.exit(main())
