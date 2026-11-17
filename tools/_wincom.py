#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""_wincom.py —— 纯 ctypes 的 Windows 串口（不依赖 pyserial）。

为什么不用 pyserial：本机 pip 走 aliyun 镜像能下载但落盘被沙箱拒绝，
所以这里直连 Win32 API。仅 Windows 有效，本项目也只跑 Windows。
"""
import ctypes
import ctypes.wintypes as wt
import time

k32 = ctypes.WinDLL('kernel32', use_last_error=True)
k32.CreateFileW.restype = wt.HANDLE
k32.CreateFileW.argtypes = [wt.LPCWSTR, wt.DWORD, wt.DWORD, ctypes.c_void_p,
                            wt.DWORD, wt.DWORD, wt.HANDLE]
k32.ReadFile.argtypes = [wt.HANDLE, ctypes.c_void_p, wt.DWORD,
                         ctypes.POINTER(wt.DWORD), ctypes.c_void_p]
k32.ReadFile.restype = wt.BOOL
k32.WriteFile.argtypes = [wt.HANDLE, ctypes.c_void_p, wt.DWORD,
                          ctypes.POINTER(wt.DWORD), ctypes.c_void_p]
k32.WriteFile.restype = wt.BOOL

GENERIC_READ = 0x80000000
GENERIC_WRITE = 0x40000000
OPEN_EXISTING = 3
INVALID_HANDLE = ctypes.c_void_p(-1).value
MAXDWORD = 0xFFFFFFFF

SETRTS, CLRRTS, SETDTR, CLRDTR = 3, 4, 5, 6
PURGE_RXABORT, PURGE_RXCLEAR, PURGE_TXABORT, PURGE_TXCLEAR = 0x0001, 0x0002, 0x0004, 0x0008

ERR_NOT_FOUND = 2
ERR_ACCESS = 5
ERR_BUSY = 121           # semaphore timeout
ERR_DEVICE_GONE = 1167


class SerialError(Exception):
    def __init__(self, code, msg):
        self.code = code
        self.msg = msg
        Exception.__init__(self, '[%d] %s' % (code, msg))


class DCB(ctypes.Structure):
    _fields_ = [('DCBlength', wt.DWORD), ('BaudRate', wt.DWORD), ('flags', wt.DWORD),
                ('wReserved', wt.WORD), ('XonLim', wt.WORD), ('XoffLim', wt.WORD),
                ('ByteSize', wt.BYTE), ('Parity', wt.BYTE), ('StopBits', wt.BYTE),
                ('XonChar', ctypes.c_char), ('XoffChar', ctypes.c_char),
                ('ErrorChar', ctypes.c_char), ('EofChar', ctypes.c_char),
                ('EvtChar', ctypes.c_char), ('wReserved1', wt.WORD)]


class COMMTIMEOUTS(ctypes.Structure):
    _fields_ = [('ReadIntervalTimeout', wt.DWORD), ('ReadTotalTimeoutMultiplier', wt.DWORD),
                ('ReadTotalTimeoutConstant', wt.DWORD),
                ('WriteTotalTimeoutMultiplier', wt.DWORD), ('WriteTotalTimeoutConstant', wt.DWORD)]


def find_ports():
    """返回 {COMx: 设备路径}，走注册表，不依赖 WMI（本机 WMI 被拒）。"""
    import winreg
    out = {}
    try:
        key = winreg.OpenKey(winreg.HKEY_LOCAL_MACHINE, r'HARDWARE\DEVICEMAP\SERIALCOMM')
    except OSError:
        return out
    i = 0
    while True:
        try:
            name, val, _ = winreg.EnumValue(key, i)
        except OSError:
            break
        i += 1
        if isinstance(val, str) and val.upper().startswith('COM'):
            out[val.upper()] = name
    return out


def pick_port(preferred='auto'):
    ports = find_ports()
    if not ports:
        raise SerialError(ERR_NOT_FOUND, 'no serial port in registry')
    if preferred and preferred != 'auto':
        p = preferred.upper()
        if p not in ports:
            raise SerialError(ERR_NOT_FOUND, 'port %s not present (have %s)'
                              % (p, ','.join(sorted(ports))))
        return p
    if len(ports) == 1:
        return list(ports)[0]
    # 多个端口：优先 USBSER（CDC），否则取第一个
    for p, dev in sorted(ports.items()):
        if 'USBSER' in dev.upper():
            return p
    return sorted(ports)[0]


class SerialPort(object):
    def __init__(self, port, baud=115200):
        self.port = port.upper()
        self.baud = baud
        self.h = None

    # ---------- 生命周期 ----------
    def open(self):
        h = k32.CreateFileW('\\\\.\\' + self.port, GENERIC_READ | GENERIC_WRITE,
                            0, None, OPEN_EXISTING, 0, None)
        if not h or h == INVALID_HANDLE:
            code = ctypes.get_last_error()
            if code in (ERR_ACCESS, ERR_BUSY):
                raise SerialError(ERR_ACCESS, '%s busy/denied (IDE 是否占用了端口？)' % self.port)
            if code == ERR_NOT_FOUND:
                raise SerialError(ERR_NOT_FOUND, '%s not found' % self.port)
            raise SerialError(code, ctypes.FormatError(code))
        self.h = h
        self._configure()
        return self

    def _configure(self):
        dcb = DCB()
        dcb.DCBlength = ctypes.sizeof(DCB)
        if not k32.GetCommState(self.h, ctypes.byref(dcb)):
            raise SerialError(ctypes.get_last_error(), 'GetCommState failed')
        dcb.BaudRate = self.baud
        dcb.ByteSize = 8
        dcb.Parity = 0
        dcb.StopBits = 0
        dcb.flags = (dcb.flags | 0x0001) & ~0x0004      # fBinary=1, fParity=0
        if not k32.SetCommState(self.h, ctypes.byref(dcb)):
            raise SerialError(ctypes.get_last_error(), 'SetCommState failed')
        to = COMMTIMEOUTS(MAXDWORD, MAXDWORD, 100, 0, 2000)
        if not k32.SetCommTimeouts(self.h, ctypes.byref(to)):
            raise SerialError(ctypes.get_last_error(), 'SetCommTimeouts failed')
        # CDC 必须拉 DTR/RTS，否则一个字节都收不到
        k32.EscapeCommFunction(self.h, SETDTR)
        k32.EscapeCommFunction(self.h, SETRTS)

    def close(self):
        if self.h:
            try:
                k32.EscapeCommFunction(self.h, CLRDTR)
                k32.CloseHandle(self.h)
            finally:
                self.h = None

    def __enter__(self):
        return self.open()

    def __exit__(self, *a):
        self.close()

    # ---------- 收发 ----------
    def purge(self):
        k32.PurgeComm(self.h, PURGE_RXCLEAR | PURGE_TXCLEAR)

    def write(self, data):
        if isinstance(data, str):
            data = data.encode('utf-8')
        n = wt.DWORD(0)
        buf = ctypes.create_string_buffer(data, len(data))
        if not k32.WriteFile(self.h, buf, len(data), ctypes.byref(n), None):
            raise SerialError(ctypes.get_last_error(), 'WriteFile failed')
        return n.value

    def read(self, max_bytes=4096):
        buf = ctypes.create_string_buffer(max_bytes)
        got = wt.DWORD(0)
        if not k32.ReadFile(self.h, buf, max_bytes, ctypes.byref(got), None):
            code = ctypes.get_last_error()
            raise SerialError(code, 'ReadFile failed: %s' % ctypes.FormatError(code))
        return buf.raw[:got.value]

    def read_for(self, ms):
        """在 ms 毫秒内尽量读完，返回 bytes。"""
        out = b''
        t0 = time.time()
        while (time.time() - t0) * 1000 < ms:
            chunk = self.read()
            if chunk:
                out += chunk
            else:
                time.sleep(0.02)
        return out

    def read_until(self, pattern, timeout=5.0, max_bytes=1 << 20):
        """读到出现 pattern 或超时；返回 (data, matched)。"""
        out = b''
        t0 = time.time()
        while (time.time() - t0) < timeout:
            chunk = self.read()
            if chunk:
                out += chunk
                if pattern in out:
                    return out, True
                if len(out) > max_bytes:
                    break
            else:
                time.sleep(0.01)
        return out, pattern in out
