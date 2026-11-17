# payloads/probe.py —— 板端事实采集（可单独在 IDE 里运行）
# 输出形如 key=value，工具与人都能读。最后一行固定 PAYLOAD_END。
import os
import gc

try:
    import machine
except ImportError:
    machine = None


def kv(k, v):
    print('%s=%s' % (k, v))


u = os.uname()
kv('fw_sysname', u.sysname)
kv('fw_release', u.release)
kv('fw_version', u.version)
kv('fw_machine', u.machine)

if machine:
    try:
        kv('chipid', ''.join(['%02x' % b for b in machine.chipid()]))
    except Exception:
        kv('chipid', 'na')
    try:
        kv('temp_c', machine.temperature())
    except Exception:
        kv('temp_c', 'na')

kv('mem_free', gc.mem_free())

for name in ('image', 'cv_lite', 'ulab.numpy', 'media.mp4format', 'sensor', 'media.sensor'):
    try:
        __import__(name)
        kv('mod_' + name.replace('.', '_'), 1)
    except Exception:
        kv('mod_' + name.replace('.', '_'), 0)

for p in ('/', '/sdcard', '/data'):
    try:
        os.listdir(p)
        kv('path_' + (p.strip('/') or 'root'), 1)
    except Exception:
        kv('path_' + (p.strip('/') or 'root'), 0)

try:
    s = os.statvfs('/')
    total = (s[0] * s[2]) // 1024
    free = (s[0] * s[3]) // 1024
    kv('fs_total_kb', total if total else 'na')
    kv('fs_free_kb', free if total else 'na')
except Exception:
    kv('fs_total_kb', 'na')
    kv('fs_free_kb', 'na')

print('PAYLOAD_END')
