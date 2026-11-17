# FACTS —— 本机 + CanMV K230 的环境事实卡

> 只写**已验证**的事实，每条带验证方式；不确定的进 `UNVERIFIED`，并写明怎么升级为 VERIFIED。
> 复核「已验」项：`python tools/smoke.py` + `python tools/board.py`。
> 需要人做的事见 `NEEDS-YOU.md`（AI 不要替人下结论）。

## A. 运行环境

| # | 事实 | 验证方式 |
| --- | --- | --- |
| A1 | 内置 Python 3.12：`C:\Users\19159\.dsh\dsh-runtimes\dsh-primary-runtime\dependencies\python\python.exe`；系统 `python` 是 **3.10**，两个都能跑本包 | `python -V`；`smoke.py` 在 3.10 与 3.12 下均 11/11 PASS |
| A2 | **没有 pyserial**；pip 走 aliyun 镜像能下载，但落盘被拒（`[Errno 13]`） | `python -c "import serial"` → ModuleNotFoundError |
| A3 | **没有 ffmpeg / ffprobe** | `Get-Command ffmpeg` → 未找到 |
| A4 | 当前 DSH 沙箱：Low 完整性、workspace-write；WMI（`Win32_SerialPort`/`Get-PnpDevice`）被拒，**COM 口可打开** | `smoke.py` 全 PASS 即证明 COM 可用 |
| A5 | `powershell.exe` 是 5.1：中文 `.ps1` **必须带 UTF-8 BOM**，且默认禁止未签名脚本 | 无 BOM 时解析报 `Unexpected token`；`.cmd` 里加 `-ExecutionPolicy Bypass` |
| A6 | 工作区可写；pip 建的 `_tmp_pip` 子目录带拒绝 ACE，删不掉（已避开） | `smoke.py` 的 `workspace_writable` |
| A7 | 用户终端：PowerShell 5.1，仓库根目录下 `python tools/xxx.py` 直接可用；`cd tools` 后 `python xxx.py` 也可用 | `userTemp_test.md` 实录（2026-11-17） |

## B. 串口与 REPL 协议

| # | 事实 | 验证方式 |
| --- | --- | --- |
| B1 | 板子 CDC 串口 = **COM13**，`USBSER000`，来自注册表 `HKLM\HARDWARE\DEVICEMAP\SERIALCOMM` | `smoke.py` 的 `serial_port_found` |
| B2 | 打开后**必须拉 DTR + RTS**，否则 0 字节；拉起后立刻收到 `\r\n>>> ` | `smoke.py` 的 `dtr_rts_ok` |
| B3 | 115200-8N1；CDC 实际不限速 | `tools/_wincom.py` 默认值 |
| B4 | raw REPL：`Ctrl-A` 进 `raw REPL; CTRL-B to exit` → 发代码 + `\x04` → `OK` + stdout + `\x04` + stderr + `\x04>` | `smoke.py` 的 `raw_repl` |
| B5 | **单次写超过约 256 B 会丢字节**（实测 `display` 截成 `splay`）→ 必须 ≤256 B / ~8 ms 分块 | `_mprepl.py` 的 `exec()` |
| B6 | `Ctrl-C` 打断程序；`Ctrl-D` 软复位；上个进程可能把板子留在 raw 态 → 进入前先 `Ctrl-B` | `_mprepl.py` 的 `sync()`/`enter_raw()` |
| B7 | **IDE 打开时会独占 COM13**，工具报 `exit 3 busy/denied` | `userTemp_test.md` 第 35–40 行实录 |

## C. 固件与板端环境

| # | 事实 | 验证方式 |
| --- | --- | --- |
| C1 | 固件 `v1.8-0-gc2d1f5c on 2026-07-03`，`sysname=rt-smart`，`machine=k230_canmv_01studio` | `python tools/board.py` |
| C2 | 芯片 ID `c052d6c3fb06c1d5c11a1c3e70ef53a69ad4fc54f6031b4bf5a8277b568f4241` | 同上 `chipid` |
| C3 | 可用模块：`image` / `cv_lite` / `ulab.numpy` / `media.sensor` / `media.mp4format`；顶层 `sensor` 不可 import（走 `media.sensor`） | `board.py` 的 `mod_*` |
| C4 | 板端 `/`、`/sdcard`、`/data` 可列；`os.statvfs('/')` 返回 0（**读不到容量**） | `board.py` 的 `path_*` |
| C5 | 摄像头 `gc2093_csi2`，原生 1920x1080@60 | `run_code.py payloads/camera.py` 的板端日志 |
| C6 | `img.get_pixel()` 在 RGB565 返回 `(r,g,b)`；`img.save(path, quality=)` 可用 | `camera.py` 亮度统计 + `--save` |
| C7 | **3.5" 屏 = ST7701S，800x480**：`Display.init(Display.ST7701, width=800, height=480, to_ide=True)` 可出图 | `python tools/display.py` → `frames=686, fps=97.6` |

## D. 设备形态（MTP，无盘符）

| # | 事实 | 验证方式 |
| --- | --- | --- |
| D1 | 板子是**便携设备 `CanMV`**（`USB#VID_1209&PID_ABD1&MI_02`），**没有盘符**；`fsutil`/`Get-Volume` 看不到外接卷 | `smoke.py` 的 `mtp_device_present` |
| D2 | 读：Shell 命名空间可列目录、可递归拷贝（实测 3 文件 1.87 MB / 1.27 s） | `python tools/pull_logs.py` |
| D3 | **写：Shell `CopyHere` 进设备静默失败**（`NewFolder` 可成功）→ 放文件只能靠 IDE/资源管理器 | 本轮实测 |
| D4 | 板端目录：`sdcard/{examples,res,libs,revision.txt}`、`data/`（用户区） | 已列目录 |

## E. 性能（2026-11-17 实测，非标称）

| 场景 | 结果 |
| --- | --- |
| `display.py` 800x480 出图 + 画色带（无检测） | **97.6 FPS**（686 帧 / 8 s） |
| `camera_check` 640x480，仅 snapshot + 亮度采样 | 12.5 FPS（采样 1200 点的 Python 循环是瓶颈） |
| `vision.py --mode apriltag` QVGA | 14–15 FPS（用户实测 60 帧） |
| `vision.py` + 用户屏幕标签 60 帧 | `hits=38/60`（63%），`fps=15.0` |
| `record.py` QVGA 30 s（flush 每 150 帧） | 481 行 / 30.1 s ≈ **16.0 行/秒**，卡顿 0 次 |
| 卡顿旧账 | flush 每 30 帧时 18 次 ≥120 ms、13.6 FPS → 改 150 帧后归零 |

> **关键结论**：通路本身能跑 97 FPS，**瓶颈在 `find_apriltags` 与 Python 层逐像素/画图操作**。
> 要做 ≥20 FPS 闭环，方向是：ROI 只搜中心区、降 QVGA 以下、去掉每帧 `print`、必要时换 `cv_lite`。

## F. 用户实测记录（2026-11-17 21:00–21:23，`userTemp_test.md`）

| 项 | 结果 | 结论 |
| --- | --- | --- |
| 板载灯 GPIO52 | `STATE=1`，用户看到灯亮 | **VERIFIED** |
| 外接灯 `--pin 2` | `STATE=1` | 软件通路 OK（灯是否亮未书面确认） |
| UART1 回环 | 先 `rx_bytes=0`（未短接）→ 短接后 `40`、`match=5/5` | **VERIFIED** |
| AprilTag（屏幕上的图） | 两次：7/60（12%）、38/60（63%），fps 14–15 | **VERIFIED**，可检出 |
| 摄像头 | IDE 里看到回显（`accept.py --skill camera-check`） | **VERIFIED** |
| 板载 KEY | 两条命令都是 `PRESSES=0`，但 SUMMARY 显示 `pin=52` | **测试无效**（命令没带 `--pin`，读成灯脚）；已把默认改成 21 |
| 3.5" 屏 | 软件侧 686 帧 / 97.6 FPS 出图 | 屏是否真亮 **待人眼确认**（NEEDS-YOU A） |

## G. UNVERIFIED（仍未验证）

| # | 未验证项 | 怎么升级为 VERIFIED |
| --- | --- | --- |
| G1 | 板载 KEY（GPIO21）按下是否读到 0 | `python tools/gpio.py --action key --times 5`，5 秒内按 2–3 次，`presses≥1` |
| G2 | 3.5" 屏是否真的亮（软件已出图） | `python tools/display.py --seconds 15` 人眼看色带 |
| G3 | UART2 端子口丝印是否为 `11/TX2`、`12/RX2` | 看板子丝印；确认后 `uart_loop.py --uart 2` 短接自测 |
| G4 | SD 卡容量与剩余空间 | `os.statvfs` 返回 0；用读卡器在 PC 上看 |
| G5 | `media.mp4format` 能否真的录出可播放 MP4 | 跑 `legacy-教程/K230入门包/examples/08_record_mp4_EXPERIMENTAL.py`，确认 `video saved!` |
| G6 | 匿名飞控帧格式 / 波特率 / 校验 | 拿到飞控《通信协议》逐项核对，**不要照抄网上** |
| G7 | MTP 写入在资源管理器拖拽下是否正常 | 用户日常拖拽可用即视为验证；脚本层已确认失败 |

## H. 复核清单（怀疑环境变了就跑这三条）

1. `python tools/smoke.py` —— 11 项全 PASS 才继续
2. `python tools/board.py` —— 核对 `fw_version` 是否仍是 `v1.8-0-gc2d1f5c`
3. `python tools/pinout.py --pin 8` —— 确认 UART1 引脚约定没变
