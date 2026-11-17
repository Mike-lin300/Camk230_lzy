# payloads/vision.py —— 在线视觉检测（逐帧回传，不写盘）
# CFG: mode(blob|apriltag) display frames width height threshold min_pixels
import time
from media.sensor import *
from media.display import *
from media.media import *
# 若报 NameError: name 'image'，取消下一行注释
# import image

CFG = CFG if 'CFG' in globals() else {}
MODE = CFG.get('mode', 'apriltag')
DISP = CFG.get('display', 'none')
NFRAMES = CFG.get('frames', 120)
W = CFG.get('width', 320)
H = CFG.get('height', 240)
TH = CFG.get('threshold', [30, 100, 15, 127, 15, 127])
MIN_PIX = CFG.get('min_pixels', 300)

sensor = Sensor(width=1280, height=960)
sensor.reset()
sensor.set_framesize(width=W, height=H)
sensor.set_pixformat(Sensor.RGB565)

if DISP == 'ide':
    Display.init(Display.VIRT, sensor.width(), sensor.height(), to_ide=True)
MediaManager.init()
sensor.run()

print('MODE=%s' % MODE)
print('W=%d' % W)
print('H=%d' % H)

clock = time.clock()
hits = 0
seq = 0
t0 = time.ticks_ms()

while seq < NFRAMES:
    clock.tick()
    img = sensor.snapshot()
    found = 0
    tid = -1
    cx = 0
    cy = 0
    w = 0
    h = 0
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
            img.draw_cross(cx, cy, color=(0, 255, 0), thickness=1)
    else:
        blobs = img.find_blobs([tuple(TH)])
        if blobs:
            b = blobs[0]
            for x in blobs:
                if x[4] > b[4]:
                    b = x
            if b[4] >= MIN_PIX:
                found = 1
                cx = b[5]
                cy = b[6]
                w = b[2]
                h = b[3]
                img.draw_rectangle(b[0], b[1], b[2], b[3], color=(0, 255, 0), thickness=2)
                img.draw_cross(cx, cy, color=(255, 0, 0), thickness=1)

    if found:
        hits += 1

    # 机器读：R,帧号,命中,id,cx,cy,w,h,rot
    print('R,%d,%d,%d,%d,%d,%d,%d,%.1f' % (seq, found, tid, cx, cy, w, h, rot))

    if DISP == 'ide':
        Display.show_image(img)
        print('FPS=%.1f' % clock.fps())

    seq += 1

dur = time.ticks_diff(time.ticks_ms(), t0)
print('FRAMES=%d' % seq)
print('HITS=%d' % hits)
print('DURATION_MS=%d' % dur)
print('FPS_MEAN=%.1f' % (seq * 1000.0 / max(dur, 1)))
print('PAYLOAD_END')

sensor.stop()
if DISP == 'ide':
    Display.deinit()
MediaManager.deinit()
