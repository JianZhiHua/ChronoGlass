# ChronoGlass

**ChronoGlass** 是一个基于 `Python + PyQt6` 的 Windows 桌面悬浮时钟与提醒工具，集成 `系统时钟`、`生活的小确幸`、`倒计时`、`秒表`、`闹钟` 五种模式。它强调低干扰、常驻桌面、快速切换和本地持久化，适合长期停放在桌面侧边使用。

整体界面采用 Nord 风格深色主题，主窗口无边框、半透明、始终置顶，支持托盘常驻和任意位置拖动。

## 功能概览

- 五种模式一体化：系统时钟、生活的小确幸、倒计时、秒表、闹钟管理
- 无边框悬浮窗口：透明背景、始终置顶、支持拖动
- 托盘集成：左键切换显示/隐藏，右键打开完整菜单
- 本地持久化：天气位置、目标倒计时、闹钟统一保存到脚本或 `exe` 同级目录
- 异步天气请求：通过后台线程访问 `wttr.in`，避免阻塞 UI
- 可选农历扩展：安装 `lunar-python` 后显示农历、节气、节日和宜忌
- 纯代码 UI 控件：自绘开关、自定义步进器，降低打包后资源缺失风险

## 页面截图
<img src="https://drive.google.com/u/0/drive-viewer/AKGpihZoWWJzCwBaDz_66GLcZVR-yyiIwokRiaL6lUk1tP3EwhTWRffKxDhaX7t6sg_ovl7Dr9b-6iO3hlpDtUSlQpEWUqCXb9hGmqQ" alt="系统时钟">

## 模式说明

### 1. 系统时钟

- 显示当前时间，精确到秒
- 显示日期、星期和天气信息
- 双击窗口可设置天气位置，例如 `北京`、`Shanghai`
- 启动后会按已保存的位置自动获取天气
- 每 30 分钟自动刷新一次天气
- 天气接口使用 `wttr.in`
- 安装 `lunar-python` 后额外显示农历日期、最近节气和简化宜忌
- 未安装 `lunar-python` 时程序仍可正常运行

### 2. 生活的小确幸

- 用于展示每日目标倒计时
- 默认标题为 `生活的小确幸`
- 默认目标时间为当前时间后 1 小时
- 目标时间按 `HH:mm:ss` 格式保存
- 支持上传 `PNG / JPG / JPEG / BMP / WEBP / GIF` 图片
- GIF 会在页面中直接播放
- 右键窗口可打开编辑器，修改标题、目标时间和图片
- 目标时间已到后，页面会显示 `恭喜` 和目标标题
- 安装 `lunar-python` 后会在卡片上显示最近节日倒计时徽标

### 3. 倒计时

- 默认时长为 20 分钟
- 支持空格键启动 / 暂停
- 支持鼠标滚轮按 1 分钟步进增减时长
- 支持双击窗口直接输入 1 到 1440 分钟
- 结束时自动停止并播放系统提示音
- 托盘菜单可重置当前倒计时

### 4. 秒表

- 支持空格键启动 / 暂停
- 实时显示累计计时时长
- 托盘菜单可将当前计时归零

### 5. 闹钟

- 支持添加、修改、删除闹钟
- 支持 `一次性` 和 `每天` 两种重复规则
- 列表显示时间、标签、重复方式、剩余时间和启用状态
- 启用状态使用自绘开关控件切换
- 一次性闹钟触发后会自动禁用，并标记为 `已触发` 或 `已过期`
- 剩余时间支持按小时、分钟、秒组合显示
- 为避免 `QTimer` 抖动漏响，触发判断使用 1 秒时间窗口
- 触发时弹出置顶提醒框，可选择 `延时5分钟`、`修改设置` 或 `完成`
- 每日闹钟在同一天内只会触发一次

## 交互说明

| 操作 | 说明 |
| :--- | :--- |
| 左键单击托盘图标 | 显示或隐藏主窗口 |
| 右键单击托盘图标 | 打开托盘菜单 |
| 右键主窗口 | 打开托盘菜单；在 `生活的小确幸` 模式下改为打开编辑器 |
| 点击右上角 `⇆` | 按顺序切换 5 种模式 |
| 点击右上角 `—` | 隐藏到托盘 |
| 点击右上角 `×` | 彻底退出程序 |
| 双击主窗口 | 在系统时钟模式下设置天气位置；在倒计时模式下设置分钟数 |
| 空格键 | 在倒计时和秒表模式下启动 / 暂停 |
| 鼠标滚轮 | 在倒计时模式下按分钟调节时长 |
| 鼠标左键拖动窗口 | 移动无边框主窗口 |

## 托盘菜单

- 切换到 `系统时钟`
- 切换到 `生活的小确幸`
- 切换到 `倒计时模式`
- 切换到 `秒表计时`
- 切换到 `闹钟`
- 重置当前计时
- 打开闹钟设置
- 彻底退出程序

## 数据存储

程序会把运行时数据保存在脚本目录或打包后的 `exe` 同级目录，而不是依赖当前工作目录。主要文件如下：

- `chronoglass_state.json`
- `chronoglass.log`

### 状态文件结构

`chronoglass_state.json` 统一保存程序配置和闹钟数据：

```json
{
  "version": 1,
  "config": {
    "location": "北京",
    "ambition": {
      "title": "下班",
      "target_time": "21:00:00",
      "image_path": "D:/Images/goal.gif"
    }
  },
  "alarms": [
    {
      "time": "20:55:00",
      "name": "晚间提醒",
      "enabled": true,
      "repeat": "daily",
      "last_trigger_date": ""
    }
  ]
}
```

### 旧数据迁移

如果目录中仍存在旧版文件：

- `alarms.json`
- `config.json`

程序会在首次启动时自动读取并迁移到 `chronoglass_state.json`。旧文件不会被自动删除。

### 日志

状态读写失败、天气请求异常或提示音播放失败时，会追加写入 `chronoglass.log`。

## 运行环境

- Windows 10 / 11
- Python 3.x

## 依赖

必需依赖：

```bash
pip install PyQt6
```

可选依赖：

```bash
pip install lunar-python
```

打包相关依赖：

```bash
pip install nuitka zstandard
```

## 开发运行

```bash
python ChronoGlass.py
```

当前版本仍然保留 `ChronoGlass.py` 作为兼容入口，但主逻辑已经拆分到 `chronoglass/` 包内，便于后续维护和扩展。

## 代码结构

拆分后的核心模块如下：

- `chronoglass/app.py`：主窗口、模式切换、天气刷新、托盘菜单、应用启动入口
- `chronoglass/dialogs.py`：闹钟编辑、闹钟列表、闹钟提醒、目标倒计时编辑等对话框
- `chronoglass/state.py`：配置与闹钟的序列化、状态文件读写、旧数据迁移、日志记录
- `chronoglass/widgets.py`：自定义开关、自定义步进器等可复用控件
- `chronoglass/common.py`：资源路径、数据文件路径、公共常量
- `ChronoGlass.py`：轻量启动入口，默认调用 `chronoglass.app.main()`

如果后续继续扩展功能，建议优先把新逻辑放进 `chronoglass/` 包，而不是重新堆回入口文件。

## 打包说明

项目提供了 Windows 构建脚本 `build.bat`。脚本会执行以下流程：

1. 检查 `.venv\Scripts\python.exe`
2. 检查 `tray_icon.ico`
3. 检查 `mycert.pfx`
4. 检查 `VS2019` 的 `VsDevCmd.bat`
5. 清理旧的 `out/`
6. 使用 `Nuitka` 构建单文件 GUI 程序
7. 调用 `signtool` 对 `out\ChronoGlass.exe` 进行签名

直接运行：

```bat
build.bat
```

如果你的 Visual Studio 安装路径、证书路径或签名参数不同，需要先修改 `build.bat` 中对应变量。

## 项目结构

- `ChronoGlass.py`：程序入口文件
- `chronoglass/__init__.py`：包导出
- `chronoglass/app.py`：主窗口与应用入口
- `chronoglass/dialogs.py`：各类对话框
- `chronoglass/state.py`：状态存储与日志逻辑
- `chronoglass/widgets.py`：自定义控件
- `chronoglass/common.py`：公共常量与路径工具
- `build.bat`：构建与签名脚本
- `tray_icon.ico` / `tray_icon.png`：程序图标资源
- `mycert.pfx`：签名证书
- `chronoglass_state.json`：运行时状态文件
- `chronoglass.log`：运行时日志
- `out/`：构建输出目录

## 稳定性设计

- 天气请求在后台线程执行，并带有并发保护，避免重复请求和界面阻塞
- 状态文件使用原子写入，降低异常中断导致的数据损坏风险
- 闹钟通过 `last_trigger_date` 去重，防止同一天重复弹窗
- 倒计时和闹钟提示音异常会被记录到日志，不会直接导致程序崩溃

## 开源协议

本项目采用 [MIT License](LICENSE)。
