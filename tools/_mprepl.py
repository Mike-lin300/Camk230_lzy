#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""_mprepl.py —— CanMV/MicroPython raw REPL 客户端。

协议（业界通用）：
  Ctrl-C          : 打断当前程序，回到友好 REPL 的 >>> 提示符
  Ctrl-A          : 进入 raw REPL，返回 "raw REPL; CTRL-B to exit\\r\\n>"
  发代码 + Ctrl-D  : 执行，返回 b"OK" + stdout + b"\\x04" + stderr + b"\\x04>"
  Ctrl-B          : 退回友好 REPL
  Ctrl-D(友好态)  : 软复位

本模块只负责"发文本、收文本"，不关心业务。
"""
import time

from _wincom import SerialPort, SerialError, pick_port, find_ports

OK, ERR_PORT, ERR_BUSY, ERR_REPL, ERR_TIMEOUT, ERR_SCRIPT = 0, 2, 3, 4, 4, 5


class BoardError(Exception):
    def __init__(self, code, msg, detail=''):
        self.code = code
        self.msg = msg
        self.detail = detail
        Exception.__init__(self, msg)


class Result(object):
    def __init__(self, ok, out, err):
        self.ok = ok
        self.out = out
        self.err = err

    def __repr__(self):
        return 'Result(ok=%s, out=%r, err=%r)' % (self.ok, self.out[:80], self.err[:80])


class Board(object):
    def __init__(self, port='auto', baud=115200):
        self.port_name = port
        self.baud = baud
        self.sp = None
        self._raw = False

    # ---------------- 连接 ----------------
    def connect(self, settle=0.35):
        try:
            name = pick_port(self.port_name)
        except SerialError as e:
            raise BoardError(ERR_PORT, 'no usable COM port', str(e))
        try:
            self.sp = SerialPort(name, self.baud).open()
        except SerialError as e:
            raise BoardError(ERR_BUSY if e.code == 5 else ERR_PORT,
                             'cannot open %s' % name, str(e))
        self.port = name
        time.sleep(settle)
        self.sync()
        return self

    def close(self):
        if self.sp:
            try:
                self.exit_raw()
            except Exception:
                pass
            self.sp.close()
            self.sp = None

    def __enter__(self):
        return self.connect()

    def __exit__(self, *a):
        self.close()

    def sync(self, attempts=3):
        """回到友好 REPL 的 >>> 提示符（能处理"上一个进程把它留在 raw REPL"的情况）。"""
        for _ in range(attempts):
            for kick in (b'\x03', b'\x02\x03'):
                self.sp.purge()
                self.sp.write(kick)
                data, ok = self.sp.read_until(b'>>>', timeout=1.5)
                if ok:
                    self._raw = False
                    return True
            time.sleep(0.15)
        raise BoardError(ERR_REPL, 'no REPL prompt',
                         'Ctrl-C 无响应；可能 main.py 死循环，或端口被 IDE 占用')

    # ---------------- 模式 ----------------
    def enter_raw(self):
        if self._raw:
            return True
        self.sp.purge()
        self.sp.write(b'\x02')          # 若上一次留在 raw 态，先退出（友好态下无副作用）
        time.sleep(0.05)
        self.sp.read_for(60)
        self.sp.purge()
        self.sp.write(b'\r\x01')
        data, ok = self.sp.read_until(b'raw REPL', timeout=3.0)
        if not ok:
            raise BoardError(ERR_REPL, 'cannot enter raw REPL',
                             data[-120:].decode('utf-8', 'replace'))
        self._raw = True
        self.sp.read_for(80)
        return True

    def exit_raw(self):
        if not self._raw:
            return
        self.sp.write(b'\x02')
        self.sp.read_for(150)
        self._raw = False

    # ---------------- 执行 ----------------
    def exec(self, code, timeout=20.0, on_data=None, keep_raw=True):
        """把 code 作为一段脚本在板子上执行，返回 Result(ok, stdout, stderr)。"""
        if isinstance(code, str):
            code = code.encode('utf-8')
        self.enter_raw()
        try:
            # 分块写入：CDC 接收缓冲有限，一次性灌几 KB 会丢字节（实测丢成 'splay'）
            payload = code + b'\x04'
            CHUNK = 256
            for i in range(0, len(payload), CHUNK):
                self.sp.write(payload[i:i + CHUNK])
                time.sleep(0.008)
            buf = b''
            t0 = time.time()
            last = 0
            matched = False
            while (time.time() - t0) < timeout:
                chunk = self.sp.read()
                if chunk:
                    buf += chunk
                    if on_data and len(buf) - last > 0:
                        on_data(buf[last:])
                        last = len(buf)
                    if buf.count(b'\x04') >= 2 and buf.rstrip().endswith(b'\x04>'):
                        matched = True
                        break
                else:
                    time.sleep(0.01)
            if on_data and len(buf) > last:
                on_data(buf[last:])
            ok, out, err = self._parse(buf)
            if not matched:
                raise BoardError(ERR_TIMEOUT, 'script did not finish in %.0fs' % timeout,
                                 ('stdout tail: ' + out[-200:]) if out else '')
            return Result(ok, out, err)
        finally:
            if not keep_raw:
                self.exit_raw()

    @staticmethod
    def _parse(buf):
        body = buf
        if body.startswith(b'OK'):
            body = body[2:]
        # 去掉尾部 \x04> 与可能的裸 \x04
        i1 = body.find(b'\x04')
        if i1 < 0:
            return True, body.decode('utf-8', 'replace'), ''
        out = body[:i1]
        rest = body[i1 + 1:]
        i2 = rest.find(b'\x04')
        err = rest[:i2] if i2 >= 0 else rest
        return (err.strip() == b''), out.decode('utf-8', 'replace'), err.decode('utf-8', 'replace')

    # ---------------- 便捷 ----------------
    def run(self, code, timeout=20.0):
        """执行并在失败时抛 BoardError(5)。"""
        res = self.exec(code, timeout=timeout)
        if not res.ok:
            raise BoardError(ERR_SCRIPT, 'board script raised', (res.err or '').strip())
        return res.out

    def soft_reset(self, timeout=8.0):
        """友好态 Ctrl-D 软复位，等 banner。"""
        self.exit_raw()
        self.sp.write(b'\x04')
        data, ok = self.sp.read_until(b'>>>', timeout=timeout)
        return data, ok

    def file_remove(self, path):
        """删除板端文件；不存在返回 False。"""
        code = ('import os\n'
                'try:\n'
                '    os.remove(%r)\n'
                '    print("REMOVED")\n'
                'except OSError:\n'
                '    print("ABSENT")\n' % path)
        res = self.exec(code, timeout=6.0)
        return 'REMOVED' in res.out


def probe_ports():
    return find_ports()
