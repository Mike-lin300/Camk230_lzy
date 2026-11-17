# payloads/camera.py —— 摄像头通路自检（可单独在 IDE 里运行）
# CFG: display(none|ide) width height save(0|1) frames
import time
import os
from media.sensor import *
from media.display import *
from media.media import *

CFG = CFG if 'CFG' in globals() else {}
DISP = CFG.get('display', 'none')
W = CFG.get('width', 640)
H = CFG.get('height', 480)
WARM = CFG.get('frames', 30)

sensor = Sensor()
sensor.reset()
sensor.set_framesize(width=W, height=H)
sensor.set_pixformat(Sensor.RGB565)

if DISP == 'ide':
    Display.init(Display.VIRT, sensor.width(), sensor.height(), to_ide=True)
MediaManager.init()
sensor.run()

clock = time.clock()
img = None
for _i in range(WARM):
    clock.tick()
    img = sensor.snapshot()
    if DISP == 'ide':
        Display.show_image(img)

w = img.width()
h = img.height()

total = 0
n = 0
mn = 255
mx = 0
dark = 0
for y in range(0, h, 16):
    for x in range(0, w, 16):
        px = img.get_pixel(x, y)
        if type(px) is tuple:
            r, g, b = px[0], px[1], px[2]
        else:
            r = g = b = px
        lum = (r * 38 + g * 75 + b * 15) >> 7
        total += lum
        n += 1
        if lum < mn:
            mn = lum
        if lum > mx:
            mx = lum
        if lum < 16:
            dark += 1

print('W=%d' % w)
print('H=%d' % h)
print('LUMA_MEAN=%d' % (total // max(n, 1)))
print('LUMA_MIN=%d' % mn)
print('LUMA_MAX=%d' % mx)
print('SAMPLES=%d' % n)
print('DARK_RATIO=%.3f' % (dark / float(max(n, 1))))
print('FPS=%.1f' % clock.fps())

if CFG.get('save', 0):
    try:
        os.mkdir('/data/live')
    except OSError:
        pass
    path = '/data/live/cam_%d.jpg' % (int(time.time()) % 1000000)
    try:
        img.save(path)
        print('SAVED=%s' % path)
    except Exception as e:
        print('SAVE_FAIL=%s' % e)

print('PAYLOAD_END')

sensor.stop()
if DISP == 'ide':
    Display.deinit()
MediaManager.deinit()
