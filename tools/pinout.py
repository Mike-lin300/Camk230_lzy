#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""pinout.py —— 引脚/复用查询（技能 pinout，纯静态，不需要板子）

用法:
    python tools/pinout.py                 # 全表
    python tools/pinout.py --search IO2
    python tools/pinout.py --search UART1
    python tools/pinout.py --pin 8
    python tools/pinout.py --json
退出码: 0 有结果 / 6 无匹配
"""
import argparse
import sys

import _common as C

# (pin 号, 丝印, GPIO, 复用/说明)
PINS = [
    (1, '3.3V', '', '电源输出'),
    (2, '5V', '', '电源输出'),
    (3, 'SDA2', 'IO12', 'I2C2_SDA / UART2_RX 复用'),
    (4, '5V', '', '电源输出'),
    (5, 'SCL2', 'IO11', 'I2C2_SCL / UART2_TX 复用'),
    (6, 'GND', '', '地'),
    (7, 'IO2', 'IO2', '普通 IO（本包外接 LED 默认用）'),
    (8, 'TX1', 'IO3', 'UART1_TX'),
    (9, 'GND', '', '地'),
    (10, 'RX1', 'IO4', 'UART1_RX'),
    (11, 'IO5', 'IO5', '普通 IO'),
    (12, 'IO6', 'IO6', '普通 IO'),
    (13, 'PWM0', 'IO42', 'PWM0'),
    (14, 'GND', '', '地'),
    (15, 'PWM1', 'IO43', 'PWM1'),
    (16, 'PWM2', 'IO46', 'PWM2'),
    (17, '3.3V', '', '电源输出'),
    (18, 'PWM3', 'IO47', 'PWM3'),
    (19, 'SPI0_MOSI', 'IO16', 'SPI0_MOSI'),
    (20, 'GND', '', '地'),
    (21, 'SPI0_MISO', 'IO17', 'SPI0_MISO'),
    (22, 'IO18', 'IO18', '普通 IO'),
    (23, 'SPI0_SCLK', 'IO15', 'SPI0_SCLK'),
    (24, 'SPI0_CS0', 'IO14', 'SPI0_CS0'),
    (25, 'GND', '', '地'),
    (26, 'SPI0_CS1', 'IO61', 'SPI0_CS1'),
    (27, 'IO19', 'IO19', '普通 IO'),
    (28, 'IO60', 'IO60', '普通 IO'),
    (29, 'IO20', 'IO20', '普通 IO'),
    (30, 'GND', '', '地'),
    (31, 'IO32', 'IO32', 'I2S_CLK'),
    (32, 'ADC0', '', 'ADC 0~3.6V'),
    (33, 'IO33', 'IO33', 'I2S_WS'),
    (34, 'GND', '', '地'),
    (35, 'IO34', 'IO34', 'I2S_DIN'),
    (36, 'ADC1', '', 'ADC 0~3.6V'),
    (37, 'IO35', 'IO35', 'I2S_DOUT'),
    (38, 'ADC2', '', 'ADC 0~1.8V（勿超）'),
    (39, 'GND', '', '地'),
    (40, 'ADC3', '', 'ADC 0~1.8V（勿超）'),
]

ONBOARD = [
    ('GPIO52', '板载蓝色 LED', '高电平点亮', '已文档化，未实测'),
    ('GPIO21', '板载 KEY', '内部上拉，按下为 0', '已文档化，未实测'),
    ('GPIO3/4', 'UART1 TX/RX', 'pin8 / pin10', '已文档化，未实测'),
]


def main():
    ap = argparse.ArgumentParser(description='CanMV K230 40Pin 引脚查询')
    ap.add_argument('--search', help='模糊匹配（丝印/GPIO/功能）')
    ap.add_argument('--pin', type=int, help='按排针号查')
    ap.add_argument('--json', action='store_true')
    args = ap.parse_args()

    rows = PINS
    q = (args.search or '').upper()
    if q:
        rows = [r for r in rows if q in ('%s %s %s %s' % r).upper()]
    if args.pin:
        rows = [r for r in rows if r[0] == args.pin]

    if not rows:
        return C.die(args.json, 'no_match', C.E_DATA, '没有匹配的引脚', query=args.search or '')

    if not args.json:
        print('%-4s %-12s %-6s %s' % ('PIN', 'SILK', 'GPIO', 'FUNC'))
        print('-' * 60)
        for p, silk, gpio, note in rows:
            print('%-4d %-12s %-6s %s' % (p, silk, gpio, note))
        print('')
        print('板载器件:')
        for g, what, how, status in ONBOARD:
            print('  %-9s %-12s %s  [%s]' % (g, what, how, status))
        print('')
        print('注意: 左下角/排针端头的 2x3 调试排针（TX0/RX0/TX3/RX3）不可占用。')

    return C.finish(args.json, 'ok', skill='pinout', rows=len(rows),
                    query=args.search or (str(args.pin) if args.pin else 'all'),
                    pins=';'.join('%d:%s' % (r[0], r[1]) for r in rows))


if __name__ == '__main__':
    sys.exit(main())
