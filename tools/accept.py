#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""accept.py —— 生成"人验收用"的脚本（技能：人机分段里的验收环节）

平台：把同一份 payload + 同一套参数，输出成一个可直接在 CanMV IDE 里运行的文件
      （唯一差别：DISPLAY='ide'，图像推到 IDE 帧缓冲区；并且静音逐帧日志）。

用法:
    python tools/accept.py --skill vision-apriltag
    python tools/accept.py --skill camera-check
    python tools/accept.py --list
退出码: 0 已生成 / 7 未知技能
"""
import argparse
import os
import sys

import _common as C

MAP = {
    'vision-apriltag': ('vision.py', {
        'mode': 'apriltag', 'display': 'ide', 'frames': 1000000,
        'width': 320, 'height': 240, 'quiet': 1}),
    'vision-blob': ('vision.py', {
        'mode': 'blob', 'display': 'ide', 'frames': 1000000,
        'width': 320, 'height': 240, 'quiet': 1,
        'threshold': [30, 100, 15, 127, 15, 127], 'min_pixels': 300}),
    'camera-check': ('camera.py', {
        'display': 'ide', 'frames': 1000000, 'width': 640, 'height': 480}),
    'display-lcd': ('display.py', {
        'display': 'ide', 'mode': 'bars', 'seconds': 1000000,
        'width': 800, 'height': 480}),
    'gpio-led': ('gpio.py', {
        'action': 'blink', 'pin': 52, 'times': 1000000, 'interval_ms': 200}),
}

HEAD = '''"""由 tools/accept.py 自动生成，供人工在 CanMV IDE 中验收。

用法：CanMV IDE 打开本文件 -> 点运行 -> 看图像缓冲区 / 板载灯。
同一次任务里，AI 跑的是同一份 payload、同一套参数，差别只有 DISPLAY='ide'。
生成命令见文件末尾注释。
"""
'''


def main():
    ap = argparse.ArgumentParser(description='生成人验收脚本')
    ap.add_argument('--skill', help='技能名，见 --list')
    ap.add_argument('--list', action='store_true', help='列出可生成的技能')
    ap.add_argument('--json', action='store_true')
    args = ap.parse_args()

    if args.list:
        for k, (p, cfg) in sorted(MAP.items()):
            print('%-20s -> payloads/%s  display=ide' % (k, p))
        return C.finish(args.json, 'ok', skill='accept', count=len(MAP),
                        skills=','.join(sorted(MAP)))

    skill = args.skill
    if not skill or skill not in MAP:
        return C.die(args.json, 'unknown_skill', C.E_PRE,
                     '未知技能：%s（--list 看可选项）' % skill)

    payload_name, cfg = MAP[skill]
    src = C.payload(payload_name)
    code = HEAD + '# python tools/accept.py --skill %s\n' % skill + C.with_cfg(src, cfg)
    out = os.path.join(C.ensure_dir(C.ACCEPT), '%s.py' % skill)
    C.write_text(out, code)

    print('[+] 已生成：%s' % out)
    print('    下一步：CanMV IDE -> 打开该文件 -> 运行（停止 = Ctrl-C 或点停止按钮）')
    print('    验收点：图像缓冲区有画面/框；与 AI 报告里的 frames/hits 对照')
    return C.finish(args.json, 'ok', skill='accept', accept_path=out,
                    payload=payload_name, display='ide')


if __name__ == '__main__':
    sys.exit(main())
