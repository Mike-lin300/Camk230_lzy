# payloads/display.py —— 3.5" MIPI 屏（ST7701S 800x480）点亮测试
# CFG: seconds mode(bars|camera) width height
import time
from media.sensor import *
from media.display import *
from media.media import *

CFG = CFG if 'CFG' in globals() else {}
SEC = CFG.get('seconds', 10)
MODE = CFG.get('mode', 'bars')
W = CFG.get('width', 800)
H = CFG.get('height', 480)

sensor = Sensor(width=1280, height=960)
sensor.reset()
sensor.set_framesize(width=W, height=H)
sensor.set_pixformat(Sensor.RGB565)

# ST7701 = 01Studio 3.5 寸 MIPI 屏；to_ide=True 同时送一份到 IDE 帧缓冲
Display.init(Display.ST7701, width=W, height=H, to_ide=True)
MediaManager.init()
sensor.run()

print('LCD=ST7701')
print('RES=%dx%d' % (W, H))
print('MODE=%s' % MODE)

clock = time.clock()
t0 = time.ticks_ms()
frames = 0
while time.ticks_diff(time.ticks_ms(), t0) < SEC * 1000:
    clock.tick()
    img = sensor.snapshot()

    if MODE == 'bars':
        th = H // 3
        img.draw_rectangle(0, 0, W, th, color=(255, 0, 0), fill=True)
        img.draw_rectangle(0, th, W, th, color=(0, 255, 0), fill=True)
        img.draw_rectangle(0, th * 2, W, H - th * 2, color=(0, 0, 255), fill=True)
        img.draw_string_advanced(24, 24, 48, 'K230 LCD OK', color=(255, 255, 255))
        img.draw_string_advanced(24, 96, 32, 'ST7701 800x480', color=(255, 255, 255))

    img.draw_string_advanced(24, H - 56, 32, 'FPS %.1f' % clock.fps(), color=(255, 255, 255))
    Display.show_image(img)
    frames += 1

print('FRAMES=%d' % frames)
print('FPS=%.1f' % clock.fps())
print('PAYLOAD_END')

sensor.stop()
Display.deinit()
MediaManager.deinit()
