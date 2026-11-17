#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
analyze_log.py —— 分析 K230 离线记录（examples/07_offline_logger.py 的产物）

用法：
    python analyze_log.py <run_dir>
    python analyze_log.py logs/20261117_201503
    python analyze_log.py logs/20261117_201503 --no-svg

输入（run 目录下）：
    meta.txt        参数与环境
    data.csv        每帧一行，可能带 #EOF 结尾行
    frames/*.jpg    抽帧（可选）

输出：
    <run_dir>/report.md    给人看的报告（含"给 AI 的摘要"）
    <run_dir>/timeline.svg FPS / 偏差 / 目标尺寸 的时序图（--no-svg 可关）
    控制台摘要

只依赖标准库，任何 Python 3.8+ 都能跑。
"""

import argparse
import glob
import math
import os
import sys
from collections import Counter

# ---------------------------------------------------------------- 解析


def parse_meta(path):
    meta = {}
    if not os.path.exists(path):
        return meta
    with open(path, 'r', encoding='utf-8', errors='replace') as f:
        for line in f:
            line = line.strip()
            if not line or line.startswith('#'):
                continue
            if '=' in line:
                k, v = line.split('=', 1)
                meta[k.strip()] = v.strip()
    return meta


def parse_csv(path):
    """返回 (rows, eof, n_bad)。rows 是按表头转成数值的 dict 列表。"""
    rows, bad, eof = [], 0, None
    if not os.path.exists(path):
        return rows, eof, bad
    header = None
    with open(path, 'r', encoding='utf-8', errors='replace') as f:
        for raw in f:
            line = raw.strip()
            if not line:
                continue
            if line.startswith('#'):
                if line.startswith('#EOF'):
                    eof = {}
                    for part in line[4:].split(','):
                        if '=' in part:
                            k, v = part.split('=', 1)
                            eof[k.strip()] = v.strip()
                continue
            if header is None:
                header = [h.strip() for h in line.split(',')]
                continue
            parts = line.split(',')
            if len(parts) != len(header):
                bad += 1
                continue
            row = {}
            ok = True
            for k, v in zip(header, parts):
                try:
                    row[k] = float(v) if ('.' in v or 'e' in v.lower()) else int(v)
                except ValueError:
                    ok = False
                    break
            if ok:
                rows.append(row)
            else:
                bad += 1
    return rows, eof, bad


def stat(vals):
    if not vals:
        return None
    s = sorted(vals)
    n = len(s)
    mu = sum(s) / n
    return {
        'n': n,
        'mean': mu,
        'median': s[n // 2] if n % 2 else (s[n // 2 - 1] + s[n // 2]) / 2.0,
        'min': s[0],
        'max': s[-1],
        'p95': s[min(n - 1, int(n * 0.95))],
        'std': math.sqrt(sum((x - mu) ** 2 for x in s) / n),
    }


def runs_of(rows, key='found'):
    """把 found==1 的连续行合并成区间"""
    out = []
    start = None
    for r in rows:
        v = r.get(key, 0)
        if v and start is None:
            start = r.get('t_ms', 0)
        elif not v and start is not None:
            out.append((start, r.get('t_ms', 0)))
            start = None
    if start is not None and rows:
        out.append((start, rows[-1].get('t_ms', 0)))
    return out


# ---------------------------------------------------------------- 报告

def fnum(v, nd=1, dash='n/a'):
    return dash if v is None else ('%.*f' % (nd, v))


def build_report(run_dir, rows, meta, eof, n_bad):
    res = meta.get('resolution', '')
    try:
        w_img, h_img = [int(x) for x in res.lower().split('x')]
    except Exception:
        w_img, h_img = 0, 0

    lines = []
    add = lines.append

    if not rows:
        add('# 运行报告（无数据）')
        add('')
        add('`data.csv` 里没有可解析的数据行。可能原因：文件为空、格式被改动、或运行刚开始就中断。')
        return '\n'.join(lines)

    # ---- 基础量
    t_end = rows[-1].get('t_ms', 0)
    duration_s = t_end / 1000.0
    n = len(rows)
    eff_rate = n / duration_s if duration_s > 0 else 0
    found = sum(1 for r in rows if r.get('found'))
    hit_ratio = found / n

    fps_vals = [r.get('fps', 0) for r in rows if r.get('fps', 0) > 0.5]
    fps_st = stat(fps_vals)

    intervals = []
    for i in range(1, n):
        intervals.append(rows[i].get('t_ms', 0) - rows[i - 1].get('t_ms', 0))
    iv_st = stat(intervals)
    med_iv = iv_st['median'] if iv_st else 0
    thr = max(3 * med_iv, 120) if med_iv else 120
    gaps = [(intervals[i], rows[i + 1].get('t_ms', 0))
            for i in range(len(intervals)) if intervals[i] > thr]

    segs = runs_of(rows)
    seg_durs = [(b - a) for a, b in segs]
    longest_seg = max(seg_durs) if seg_durs else 0

    ids = Counter(int(r.get('id', -1)) for r in rows if r.get('found') and r.get('id', -1) >= 0)
    dx_vals = [r.get('dx', 0) for r in rows if r.get('found')]
    dy_vals = [r.get('dy', 0) for r in rows if r.get('found')]
    size_vals = [max(r.get('w', 0), r.get('h', 0)) for r in rows if r.get('found')]
    dx_st, dy_st, size_st = stat(dx_vals), stat(dy_vals), stat(size_vals)

    frames = sorted(glob.glob(os.path.join(run_dir, 'frames', '*.jpg')))

    # ---- 结论
    issues, goods = [], []
    if eof is None:
        issues.append('CSV 没有 `#EOF` 结尾行 → 本次运行**被中断**（断电 / 复位 / 强杀），数据可能不完整')
    elif str(eof.get('reason', '')).startswith('error'):
        issues.append('运行以异常结束：`%s`' % eof.get('reason'))

    if fps_st:
        if fps_st['median'] >= 20:
            goods.append('帧率中位数 %.1f FPS，够做闭环（≥20 是舒适区）' % fps_st['median'])
        elif fps_st['median'] >= 10:
            issues.append('帧率中位数只有 %.1f FPS，做闭环会偏迟钝（建议降分辨率）' % fps_st['median'])
        else:
            issues.append('帧率中位数只有 %.1f FPS，**不适合闭环**，先解决性能' % fps_st['median'])

    if hit_ratio >= 0.5:
        goods.append('检测命中率 %.0f%%，目标稳定在视野内' % (hit_ratio * 100))
    elif hit_ratio >= 0.2:
        issues.append('检测命中率只有 %.0f%%，时有时无' % (hit_ratio * 100))
    else:
        issues.append('检测命中率仅 %.0f%%，检测本身有问题（先回 M3 调阈值/查标签）' % (hit_ratio * 100))

    if len(gaps) > 5:
        issues.append('出现 %d 次卡顿（最大 %d ms），写盘/编码可能拖慢了主循环' % (len(gaps), max(g[0] for g in gaps)))
    elif gaps:
        goods.append('只有 %d 次轻微卡顿（最大 %d ms）' % (len(gaps), max(g[0] for g in gaps)))
    else:
        goods.append('时序干净，没有超过 %d ms 的间隔' % int(thr))

    if dx_st and abs(dx_st['mean']) > 0.15 * (w_img or 1):
        issues.append('目标长期偏在画面一侧（dx 均值 %.0f px），说明机位/标签位置没对正' % dx_st['mean'])

    verdict = '良好' if not issues else ('有问题' if len(issues) >= 3 else '基本可用')

    # ---- 写成 markdown
    add('# 运行报告：%s' % (meta.get('run_id') or os.path.basename(run_dir.rstrip('\\/'))))
    add('')
    add('| 项 | 值 |')
    add('| --- | --- |')
    add('| 检测模式 | %s |' % meta.get('mode', '?'))
    add('| 分辨率 | %s |' % (res or '?'))
    add('| 计划时长 | %s s |' % meta.get('duration_s', '?'))
    add('| 实际时长 | %.1f s |' % duration_s)
    add('| 数据行数 | %d（坏行 %d） |' % (n, n_bad))
    add('| 结束原因 | %s |' % (eof.get('reason', '⚠ 无 #EOF（被中断）') if eof else '⚠ 无 #EOF（被中断）'))
    add('| 脚本 | %s |' % meta.get('script', '?'))
    add('| 固件 | %s |' % meta.get('firmware', '?'))
    add('| 芯片 ID | %s |' % meta.get('chipid', '?'))
    add('| 抽帧图片 | %d 张 |' % len(frames))
    add('')
    add('## 结论：%s' % verdict)
    add('')
    for g in goods:
        add('- ✅ %s' % g)
    for i in issues:
        add('- ⚠️ %s' % i)
    add('')

    add('## 时序与帧率')
    add('')
    add('| 指标 | 值 |')
    add('| --- | --- |')
    add('| 采样率（等效） | %.1f 行/秒 |' % eff_rate)
    add('| FPS 中位数 / 均值 | %s / %s |' % (fnum(fps_st and fps_st['median']), fnum(fps_st and fps_st['mean'])))
    add('| FPS 最低 / 最高 | %s / %s |' % (fnum(fps_st and fps_st['min']), fnum(fps_st and fps_st['max'])))
    add('| 帧间隔中位数 | %s ms |' % fnum(med_iv))
    add('| 最大卡顿 | %d ms |' % (max(g[0] for g in gaps) if gaps else 0))
    add('')

    add('## 检测质量')
    add('')
    add('| 指标 | 值 |')
    add('| --- | --- |')
    add('| 命中行数 / 比例 | %d / %.0f%% |' % (found, hit_ratio * 100))
    add('| 命中段数 | %d 段 |' % len(segs))
    add('| 最长连续命中 | %.1f s |' % (longest_seg / 1000.0))
    add('| 出现过的 id | %s |' % (', '.join('%d×%d' % (k, v) for k, v in sorted(ids.items())) or '—'))
    add('')

    if dx_st or size_st:
        add('## 目标位置与尺寸（命中帧）')
        add('')
        add('| 量 | 均值 | 中位数 | 标准差 | 最小 | 最大 | p95 |')
        add('| --- | --- | --- | --- | --- | --- | --- |')
        for name, st, nd in (('dx (px)', dx_st, 1), ('dy (px)', dy_st, 1),
                             ('目标尺寸 (px)', size_st, 1)):
            if st:
                add('| %s | %s | %s | %s | %s | %s | %s |' % (
                    name, fnum(st['mean'], nd), fnum(st['median'], nd), fnum(st['std'], nd),
                    fnum(st['min'], nd), fnum(st['max'], nd), fnum(st['p95'], nd)))
        add('')

    if len(segs) > 1:
        add('## 命中区间（前 5 段）')
        add('')
        for a, b in segs[:5]:
            add('- %.2f s → %.2f s（%.2f s）' % (a / 1000.0, b / 1000.0, (b - a) / 1000.0))
        add('')

    if frames:
        add('## 抽帧图片')
        add('')
        add('共 %d 张，文件名里的数字是帧号（对应 CSV 的 `frame` 列）：' % len(frames))
        add('')
        for p in frames[:8]:
            add('- `frames/%s`' % os.path.basename(p))
        if len(frames) > 8:
            add('- …（其余 %d 张略）' % (len(frames) - 8))
        add('')

    # ---- 给 AI 的摘要
    add('## 给 AI 的摘要')
    add('')
    add('```')
    add('run_id=%s' % meta.get('run_id', '?'))
    add('mode=%s' % meta.get('mode', '?'))
    add('res=%s' % res)
    add('duration_s=%.1f' % duration_s)
    add('rows=%d' % n)
    add('rate_per_s=%.1f' % eff_rate)
    add('fps_median=%s' % fnum(fps_st and fps_st['median']))
    add('fps_p5=%s' % fnum(sorted(fps_vals)[max(0, int(len(fps_vals) * 0.05))] if fps_vals else None))
    add('gaps=%d' % len(gaps))
    add('max_gap_ms=%d' % (max(g[0] for g in gaps) if gaps else 0))
    add('hit_ratio=%.2f' % hit_ratio)
    add('segments=%d' % len(segs))
    add('longest_seg_s=%.2f' % (longest_seg / 1000.0))
    add('ids=%s' % (','.join('%d:%d' % (k, v) for k, v in sorted(ids.items())) or '-'))
    if dx_st:
        add('dx_mean=%.1f' % dx_st['mean'])
        add('dx_std=%.1f' % dx_st['std'])
        add('dy_mean=%.1f' % dy_st['mean'])
        add('size_mean=%.1f' % (size_st['mean'] if size_st else 0))
    add('eof=%s' % ('yes' if eof else 'NO'))
    add('verdict=%s' % verdict)
    add('```')
    add('')
    add('> 这份报告由 `tools/analyze_log.py` 自动生成。把整个 run 目录给 AI，'
        '让它读 `report.md` + `data.csv`，需要看现场时再看 `frames/` 里的图。')

    return '\n'.join(lines)


# ---------------------------------------------------------------- SVG

def build_svg(rows, path):
    if len(rows) < 2:
        return False
    ts = [r.get('t_ms', 0) for r in rows]
    t0, t1 = ts[0], ts[-1]
    span = max(1, t1 - t0)

    panels = []
    panels.append(('FPS', [('fps', [r.get('fps', 0) for r in rows], '#2f7ed8')]))
    if any(r.get('found') for r in rows):
        panels.append(('偏差 dx / dy (px)', [
            ('dx', [r.get('dx', 0) if r.get('found') else None for r in rows], '#d9534f'),
            ('dy', [r.get('dy', 0) if r.get('found') else None for r in rows], '#5cb85c'),
        ]))
        panels.append(('目标尺寸 (px)', [
            ('size', [max(r.get('w', 0), r.get('h', 0)) if r.get('found') else None for r in rows], '#f0ad4e'),
        ]))

    W, PH, ML, MR, MT, GAP = 900, 150, 66, 18, 26, 26
    H = MT + len(panels) * (PH + GAP) + 20
    out = ['<svg xmlns="http://www.w3.org/2000/svg" width="%d" height="%d" '
           'font-family="Segoe UI,Microsoft YaHei,sans-serif" font-size="11">' % (W, H),
           '<rect width="100%%" height="100%%" fill="#ffffff"/>']
    plot_w = W - ML - MR

    for idx, (title, series) in enumerate(panels):
        top = MT + idx * (PH + GAP)
        vals = [v for _, ys, _ in series for v in ys if v is not None]
        if not vals:
            continue
        vmin, vmax = min(vals), max(vals)
        if vmax == vmin:
            vmax = vmin + 1
        pad = (vmax - vmin) * 0.08
        vmin -= pad
        vmax += pad

        out.append('<text x="%d" y="%d" fill="#333" font-weight="600">%s</text>' % (ML, top - 8, title))
        out.append('<rect x="%d" y="%d" width="%d" height="%d" fill="#fafafa" stroke="#ddd"/>'
                   % (ML, top, plot_w, PH))
        # y 网格
        for k in (0.0, 0.5, 1.0):
            vy = top + PH - k * PH
            vv = vmin + k * (vmax - vmin)
            out.append('<line x1="%d" y1="%.1f" x2="%d" y2="%.1f" stroke="#e8e8e8"/>'
                       % (ML, vy, ML + plot_w, vy))
            out.append('<text x="%d" y="%.1f" fill="#888" text-anchor="end">%.4g</text>'
                       % (ML - 6, vy + 4, vv))

        for name, ys, color in series:
            pts = []
            for r, v in zip(rows, ys):
                if v is None:
                    continue
                x = ML + (r.get('t_ms', 0) - t0) / span * plot_w
                y = top + PH - (v - vmin) / (vmax - vmin) * PH
                pts.append('%.1f,%.1f' % (x, y))
            if len(pts) >= 2:
                out.append('<polyline fill="none" stroke="%s" stroke-width="1.3" points="%s"/>'
                           % (color, ' '.join(pts)))
            # 图例
            lx = ML + 6 + 74 * [s[0] for s in series].index(name)
            out.append('<rect x="%d" y="%d" width="9" height="9" fill="%s"/>' % (lx, top + 5, color))
            out.append('<text x="%d" y="%d" fill="#555">%s</text>' % (lx + 13, top + 13, name))

    out.append('<text x="%d" y="%d" fill="#888">时间 0 → %.1f s</text>'
               % (ML, H - 6, span / 1000.0))
    out.append('</svg>')

    with open(path, 'w', encoding='utf-8') as f:
        f.write('\n'.join(out))
    return True


# ---------------------------------------------------------------- main

def out(s=''):
    """控制台输出兜底：Windows 的 GBK 控制台打不出 ✅ / ⚠️ 这类字符"""
    try:
        print(s)
    except UnicodeEncodeError:
        enc = sys.stdout.encoding or 'ascii'
        print(s.encode(enc, 'replace').decode(enc, 'replace'))


def summarize(report):
    """从报告的『给 AI 的摘要』代码块里抽取 key=value，供 SUMMARY/JSON 使用。"""
    kv = {}
    grab = False
    for line in report.splitlines():
        if line.strip().startswith('```'):
            grab = not grab
            continue
        if grab and '=' in line:
            k, v = line.split('=', 1)
            kv[k.strip()] = v.strip()
    return kv


def main():
    ap = argparse.ArgumentParser(description='分析 K230 离线记录（技能 analyze-log）')
    ap.add_argument('run_dir', help='run 目录（含 meta.txt / data.csv）')
    ap.add_argument('--no-svg', action='store_true', help='不生成 timeline.svg')
    ap.add_argument('--json', action='store_true', help='只输出 JSON 摘要')
    args = ap.parse_args()

    import _common as C

    run_dir = args.run_dir.rstrip('\\/')
    if not os.path.isdir(run_dir):
        print('找不到目录：%s' % run_dir, file=sys.stderr)
        return C.die(args.json, 'bad_input', C.E_PORT, 'run 目录不存在: %s' % run_dir)

    meta = parse_meta(os.path.join(run_dir, 'meta.txt'))
    rows, eof, n_bad = parse_csv(os.path.join(run_dir, 'data.csv'))

    report = build_report(run_dir, rows, meta, eof, n_bad)
    out_md = os.path.join(run_dir, 'report.md')
    with open(out_md, 'w', encoding='utf-8') as f:
        f.write(report)

    svg_ok = False
    if not args.no_svg:
        svg_ok = build_svg(rows, os.path.join(run_dir, 'timeline.svg'))

    if not rows:
        return C.finish(args.json, 'no_data', C.E_DATA, **{
            'skill': 'analyze-log', 'run_dir': run_dir, 'report': out_md, 'rows': 0})

    # 控制台摘要：取报告里"结论"之后到"时序与帧率"之前的部分
    out(report.split('## 结论：', 1)[-1].split('## 时序与帧率')[0].strip())
    out('')
    out('报告：%s' % out_md)
    if svg_ok:
        out('图表：%s' % os.path.join(run_dir, 'timeline.svg'))

    kv = summarize(report)
    kv['skill'] = 'analyze-log'
    kv['run_dir'] = run_dir
    kv['report'] = out_md
    if svg_ok:
        kv['svg'] = os.path.join(run_dir, 'timeline.svg')
    eof_ok = 'eof=yes' in report
    return C.finish(args.json, 'ok', **kv)


if __name__ == '__main__':
    sys.exit(main())
