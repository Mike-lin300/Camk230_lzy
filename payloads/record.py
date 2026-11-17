# payloads/record.py —— 离线录制：CSV + 抽帧 JPEG 落板端磁盘（无人看管也能跑）
# CFG: mode(blob|apriltag) duration_s width height save_interval_ms jpeg_quality run_id
import time
import os
from media.sensor import *
from media.display import *
from media.media import *

CFG = CFG if 'CFG' in globals() else {}
MODE = CFG.get('mode', 'apriltag')
DUR = CFG.get('duration_s', 180)
W = CFG.get('width', 320)
H = CFG.get('height', 240)
SAVE_MS = CFG.get('save_interval_ms', 1000)
QUAL = CFG.get('jpeg_quality', 75)
DISP = CFG.get('display', 'none')
RUN = CFG.get('run_id') or ('r%d' % (int(time.time()) % 100000000))

ROOT = '/data/logs'
try:
    os.mkdir(ROOT)
except OSError:
    pass
D = ROOT + '/' + RUN
try:
    os.mkdir(D)
except OSError:
    pass
try:
    os.mkdir(D + '/frames')
except OSError:
    pass

meta = open(D + '/meta.txt', 'w')
meta.write('run_id=%s\n' % RUN)
meta.write('mode=%s\n' % MODE)
meta.write('resolution=%dx%d\n' % (W, H))
meta.write('duration_s=%d\n' % DUR)
meta.write('save_interval_ms=%d\n' % SAVE_MS)
meta.write('jpeg_quality=%d\n' % QUAL)
meta.write('source=payloads/record.py\n')
meta.close()

sensor = Sensor(width=1280, height=960)
sensor.reset()
sensor.set_framesize(width=W, height=H)
sensor.set_pixformat(Sensor.RGB565)
if DISP == 'ide':
    Display.init(Display.VIRT, sensor.width(), sensor.height(), to_ide=True)
MediaManager.init()
sensor.run()

csvf = open(D + '/data.csv', 'w')
csvf.write('t_ms,frame,found,id,cx,cy,w,h,rot_deg,dx,dy,fps\n')

clock = time.clock()
t0 = time.ticks_ms()
frames = 0
hits = 0
saved = 0
last_save = 0
reason = 'duration'

print('RUN_ID=%s' % RUN)
print('DIR=%s' % D)

while True:
    clock.tick()
    now = time.ticks_ms()
    t_ms = time.ticks_diff(now, t0)
    img = sensor.snapshot()

    found = 0
    tid = -1
    cx = cy = w = h = 0
    rot = 0.0
    if MODE == 'apriltag':
        tags = img.find_apriltags(families=image.TAG36H11)
        if tags:
            tag = tags[0]
            r = tag.rect()
            found = 1
            tid = tag.id()
            cx = tag.cx()
            cy = tag.cy()
            w = r[2]
            h = r[3]
            rot = tag.rotation() * 57.29578
            img.draw_rectangle(r, color=(255, 0, 0), thickness=2)
    else:
        blobs = img.find_blobs([tuple(CFG.get('threshold', [30, 100, 15, 127, 15, 127]))])
        if blobs:
            b = blobs[0]
            for x in blobs:
                if x[4] > b[4]:
                    b = x
            if b[4] >= CFG.get('min_pixels', 300):
                found = 1
                cx = b[5]
                cy = b[6]
                w = b[2]
                h = b[3]
                img.draw_rectangle(b[0], b[1], b[2], b[3], color=(0, 255, 0), thickness=2)

    if found:
        hits += 1

    csvf.write('%d,%d,%d,%d,%d,%d,%d,%d,%.1f,%d,%d,%.1f\n'
               % (t_ms, frames, found, tid, cx, cy, w, h, rot,
                  cx - W // 2, cy - H // 2, clock.fps()))

    if found and SAVE_MS > 0 and time.ticks_diff(now, last_save) >= SAVE_MS:
        last_save = now
        p = '%s/frames/f%05d_%d.jpg' % (D, frames, t_ms)
        try:
            img.save(p, quality=QUAL)
            saved += 1
        except Exception as e:
            print('SAVE_FAIL=%s' % e)

    if DISP == 'ide':
        Display.show_image(img)

    if frames % 150 == 0:
        try:
            csvf.flush()
        except Exception:
            pass

    frames += 1
    if t_ms >= DUR * 1000:
        break

try:
    csvf.write('#EOF,frames=%d,hits=%d,saved=%d,duration_ms=%d,reason=%s\n'
               % (frames, hits, saved, time.ticks_diff(time.ticks_ms(), t0), reason))
    csvf.flush()
except Exception:
    pass
csvf.close()

print('FRAMES=%d' % frames)
print('HITS=%d' % hits)
print('SAVED=%d' % saved)
print('DURATION_MS=%d' % time.ticks_diff(time.ticks_ms(), t0))
print('PAYLOAD_END')

sensor.stop()
if DISP == 'ide':
    Display.deinit()
MediaManager.deinit()
