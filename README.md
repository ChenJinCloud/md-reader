# MD Reader

![Banner](banner.jpg)

## 解决什么问题

我的日常工作流是同时开一堆终端让 AI Agent 并行跑任务，每个窗口一个活儿，产出都是 `.md` 报告/方案/分析。任务完成后我需要快速扫一眼结果 —— 不是当时跟它讨论，是事后看交付。

这时候"打开 Markdown 文件"这个动作就变得很尴尬：

- **浏览器预览**不行，浏览器界面太杂，地址栏/标签栏/插件图标都在抢视觉
- **IDE（Qoder / Cursor / VSCode）里开预览**可以，但是**为了看一份笔记开一整个 IDE 太重**，开机慢、内存大、视觉嘈杂，本质上是把 IDE 当记事本用
- **系统自带的记事本**不渲染 Markdown，一堆 `#` `*` `>` 符号直接劝退
- **HTA / mshta**是系统对话框的长相，丑且没独立感

MD Reader 就是为这个场景存在的一个极轻的桌面 Markdown 阅读器：**Everything 搜到 → 回车 → 一张纸**。frameless 圆角窗口、纸质主题、颗粒纹理、衬线字体、可拖拽 TOC、多标签、分屏编辑。打开快、视觉干净，像桌面小程序而不是文档查看器。需要改点什么？`Ctrl+E` 当场分屏编辑，自动保存回原文件。

如果 AI 在另一个窗口改同一份文件（比如 Claude Code 在修订方案），reader 窗口会自动跟着拉取新内容，不需要你关闭重开。

## 特性

- **纸质配色** — Parchment / Medium / Rice / Linen / Ink 五套主题，全部按"纸 + 墨"的物理质感配色，不用纯白背景也不用纯黑文字
- **真 · 颗粒纹理** — 正文和 TOC 用 Tk `-bgstipple` 做逐像素两色噪点抖动（启动时生成固定种子的 32×32 XBM 位图），不是纯底色
- **圆角窗口** — Win32 `CreateRoundRectRgn` + `SetWindowRgn`，18 px 半径，一次性调用零副作用
- **frameless + 自绘 topbar** — 没有系统标题栏，自己绘 chrome，按钮全在顶部一排
- **多标签单窗口** — 再次用 `md-reader.cmd` 打开新文件 = 作为新标签加入现有窗口，`msvcrt.locking` 抢单实例锁 + 文件 IPC
- **TOC 侧边栏** — 解析 h1-h3 点击跳转，**宽度可拖拽**（140–600 px），状态持久化
- **分屏编辑模式** — `Ctrl+E` 切换，底部展开 MONO 字体编辑面板，改动 250 ms 防抖实时重渲染正文，900 ms 防抖自动保存到文件，`Ctrl+S` 即刻保存
- **和外部编辑器双向同步** — Claude Code 等第三方工具改动当前打开的文件时，reader 窗口自动拉新内容到正文和编辑缓冲区（前提：你本地没有未保存的改动）
- **文件 watcher** — 活跃标签外部修改自动重新渲染并保留滚动位置
- **字号连续调节** — 8–28 pt，`A−  N  A+` 按钮、`Ctrl+=` / `Ctrl+-`、或字号数字滚轮，180 ms 防抖合并连击
- **GFM 支持** — 标题、段落、加粗/斜体/删除线/行内代码、有序/无序/任务列表、引用、围栏代码块、链接、表格、分隔线
- **自定义主题目录** — `themes/*.json` 自动加载合并
- **状态自动保存** — 窗口位置、大小、主题、字号、TOC 宽度、编辑面板高度、最大化状态全部持久化
- **零依赖** — 仅 Python 3 标准库（`tkinter` / `ctypes` / `msvcrt`），不装 pip
- **高 DPI 支持** — Per-Monitor v1 DPI 感知

## 快速启动

```bash
# 1) 一次性注册 .md 文件关联（Win10/11 必须，否则"打开方式"勾不上"始终使用"）
双击 install.cmd

# 2) 之后任意 .md 文件双击或回车就在独立窗口里打开
```

也可以直接命令行启动：

```cmd
md-reader.cmd "path\to\file.md"
```

或者绕过 .cmd 启动器直接调：

```cmd
pythonw md-reader.pyw "path\to\file.md"
```

第一次运行起主进程；再次运行会检测到锁，把新文件路径交给主进程后自己退出——主进程把新文件作为新标签打开。

## 快捷键

| 键位 | 行为 |
|---|---|
| `Esc` | 关闭窗口 |
| `Ctrl+W` | 关闭当前标签（最后一个 = 关窗口） |
| `F5` / `Ctrl+R` | 重新加载当前标签 |
| `F11` / 双击顶部 / 点 `□` | 最大化 / 还原 |
| `Ctrl+E` / 点 `✎` | 切换分屏编辑模式 |
| `Ctrl+S` | 编辑模式下保存当前文件 |
| `Ctrl+Tab` / `Ctrl+PgDn` | 下一个标签 |
| `Ctrl+Shift+Tab` / `Ctrl+PgUp` | 上一个标签 |
| `Ctrl+=` / `Ctrl++` | 字号增大 |
| `Ctrl+-` | 字号减小 |

## 鼠标操作

| 操作 | 功能 |
|---|---|
| 拖拽 topbar / tab bar 空白处 | 移动窗口 |
| 双击 topbar | 最大化 / 还原 |
| 拖拽窗口左/右/下边缘或左下/右下角 | 调整窗口大小 |
| 拖拽 TOC 和正文之间的 5 px 分隔条 | 调整 TOC 宽度（140–600 px） |
| 拖拽正文和编辑面板之间的 5 px 分隔条 | 调整编辑面板高度（120–900 px） |
| 点 TOC 里的标题 | 跳转到文档对应位置 |
| 字号数字上滚轮 | 字号增减 |
| 点 topbar 主题名 | 循环切换主题 |

## 顶栏按钮

| 按钮 | 功能 |
|---|---|
| ● | 装饰圆点 |
| 数字 | 当前字号（8–28 pt） |
| Parchment / Medium / ... | 当前主题名，点击循环切换 |
| ↻ | 重新加载当前文件 |
| ✎ | 切换分屏编辑模式 |
| ☰ | 切换 TOC 侧边栏 |
| `A−` `N` `A+` | 字号减 / 当前值 / 字号加 |
| `□` / `❐` | 最大化 / 还原 |
| ✕ | 关闭窗口 |

## 文件结构

```
├── md-reader.pyw              # 主程序（~1690 行纯 Python）
├── md-reader.cmd              # 薄启动器（命令行调用）
├── install.cmd                # 一次性注册 .md 关联（HKCU，不需要管理员）
├── test-sample.md             # 测试文档，覆盖常用 GFM 语法
├── themes/                    # 可选，放自定义主题 JSON
├── banner.jpg                 # 项目宣传图
├── banner.html                # banner 源文件
├── README.md                  # 本文件
├── CHANGELOG.md               # 版本变更记录
├── DISCUSSION.md              # 项目决策时间线
├── LICENSE                    # MIT
├── .md-reader-state.json      # 用户状态（自动生成）
├── .md-reader-noise.xbm       # 纸面颗粒噪点位图（自动生成）
├── .md-reader.lock            # 单实例锁（自动生成）
├── .md-reader-pending-*.txt   # 单实例 IPC（自动生成）
└── .md-reader-crash.log       # 崩溃/诊断日志（按需生成）
```

## 主题

五套内置主题，全部按"纸 + 墨"物理质感配色：

| 主题 | 背景 | 文字 | Accent | 意象 |
|---|---|---|---|---|
| **Parchment** | `#F3EBD6` | `#3C3328` | `#8B3A2F` 朱砂 | 羊皮纸 |
| **Medium** | `#FFFFFF` | `#292929` | `#1A8917` 墨绿 | Medium.com 白纸 |
| **Rice** | `#EEE6D0` | `#45423A` | `#6E7A5A` 鼠尾草 | 米纸 / 和纸 |
| **Linen** | `#E2E0D5` | `#36404A` | `#3B5A78` 普鲁士蓝 | 亚麻 / 蓝图纸 |
| **Ink** | `#22201E` | `#E6DFD0` | `#D4A757` 黄铜 | 炭笔素描本 |

点 topbar 上的主题名循环切换：`Parchment → Medium → Rice → Linen → Ink → Parchment`。

## 自定义主题

在项目目录下建 `themes/` 子目录，放 JSON 文件。文件名就是主题名。所有 key 都必填：

```json
{
  "bg": "#F3EBD6",
  "fg": "#3C3328",
  "secondary": "#8A7C66",
  "accent": "#8B3A2F",
  "title": "#2A231A",
  "hr": "#DCCEB0",
  "border": "#C9B98F",
  "topbar": "#ECE1C3",
  "code_bg": "#E4D7B5",
  "quote_fg": "#6A5D4A",
  "scroll": "#BDAB85"
}
```

启动时扫描合并到内置 `THEMES`，缺 key 的文件会被跳过。

配色建议：**背景别用纯白、文字别用纯黑**。纸质主题的精神是"永远差那么一点点色度"，才有墨水在纸上的感觉。

## Claude Code 集成（可选）

如果你是 Claude Code 用户，项目自带一个 Skill 定义 `skill/SKILL.md`，装好后就可以直接对 Claude 说"**打开你刚写的那份 md**"、"**用阅读器看一下**"、"**render this markdown**"之类的话，Claude 会自动调 `md-reader.cmd` 把文件拉到独立窗口里——不用你自己复制路径、不用 Edit 工具，也不会把文件内容贴回对话。

安装：把 `skill/SKILL.md` 复制到 `~/.claude/skills/md-reader/SKILL.md`：

```bash
# Windows (Git Bash / WSL / MSYS)
mkdir -p ~/.claude/skills/md-reader
cp skill/SKILL.md ~/.claude/skills/md-reader/SKILL.md
```

或者直接在 Windows 资源管理器里把 `skill` 目录复制成 `C:\Users\<你>\.claude\skills\md-reader`。

Claude Code 下次启动时会自动识别这个 skill，当对话里出现"打开 md"类语义时就调用。触发条件、边界（比如只在"想看、想读、想渲染"时调用，而不是"想编辑或提问"时）都写在 `SKILL.md` 的 description 里。

## 状态记忆

所有偏好都写在 `.md-reader-state.json`（项目目录下），下次启动自动恢复：

| 字段 | 说明 |
|---|---|
| `theme` | 当前主题 |
| `font_size` | 正文字号（8–28 pt） |
| `width` / `height` / `x` / `y` | 窗口尺寸和位置 |
| `maximized` | 是否最大化 |
| `toc_visible` / `toc_width` | TOC 侧边栏是否显示 / 宽度 |
| `edit_visible` / `edit_height` | 编辑模式是否打开 / 高度 |

任何交互改动（切主题、拖边缘、调字号等）都会立刻写盘，不依赖正常关窗。即使进程被 kill，最后一次偏好也不会丢。想重置：删掉这个文件再启动即可。

## 工作原理

```
.md 文件
   │
   ▼
md-reader.cmd   ← 薄启动器
   │
   └─ start "" pythonw md-reader.pyw <file>
        │
        ▼
  md-reader.pyw (Python + tkinter + overrideredirect)
        │
        ├─ msvcrt.locking 抢单实例锁
        │   ├─ 抢到 → 自己是主进程，开窗口
        │   └─ 没抢到 → 写 .md-reader-pending-<pid>-<ts>.txt 退出
        │
        ├─ 主进程每 350 ms 扫 pending 文件 → 新标签
        ├─ 主进程每 900 ms 检查活跃标签 mtime → 自动重载
        │
        ├─ Win32 SetWindowRgn 裁剪窗口成 18 px 圆角
        │
        └─ 渲染：内置 markdown parser → tk.Text + tag_configure
                 ↓
                 paper tag 带 bgstipple=@noise.xbm → 纸面颗粒纹理
```

## 架构历史

（长版在 `CHANGELOG.md` 和 `DISCUSSION.md`）

- **0.1.0** PowerShell + base64 + HTML 模板 + CDN marked.js，浏览器打开。**被否**：不是独立窗口
- **0.2.0** cmd + PowerShell 多语言文件 + 本地 Markdig.dll + HTA + mshta。**被否**：mshta 窗口是系统对话框
- **0.3.0** 彻底换成 Python tkinter + `overrideredirect(True)` 自绘窗口
- **0.4.0** 多标签、TOC、文件 watcher、自定义主题、GFM 表格、字号 slider
- **0.4.1** 为了要 Win11 snap 试了五轮 Win32 自定义 chrome，全部卡退。回退到参考项目 `sticky-card` 的朴素 `overrideredirect` 方案，丢 snap 换稳定，同时修复字号连击卡顿
- **0.4.2** 视觉重设计：纸质主题、18 px 圆角窗口（Win32 `SetWindowRgn`）、TOC 宽度可拖拽
- **0.4.3** 真的加上纹理（Tk `-bgstipple` 做两色噪点抖动）、Kraft 主题降饱和
- **0.4.4** 分屏编辑模式
- **0.4.5** 新增 Medium 主题 / 删除 Kraft / 修复切主题丢未保存编辑 / 修复 tab 字体黑粗体突兀 / 编辑模式升级双向同步（900 ms 自动保存 + 外部改动在本地未脏时自动拉取）
- **0.4.6** `install.cmd` 一次性注册 `.md` 文件关联，解决 Win10/11 "打开方式"对话框"始终使用"勾选框灰掉的问题
- **0.4.7** 修复渲染区无法选中复制文本。`self.text` 原本每次渲染后被 `configure(state="disabled")`，tkinter 下这会完全禁用鼠标选区。改为 read-only-but-selectable：保持 `state="normal"`，新增 `_readonly_keypress` 拦截所有写入类按键（只放行 `Ctrl+C / Ctrl+A` 和导航键），同时屏蔽 `<<Paste>>` / `<<Cut>>`。鼠标选区和 Ctrl+C 复制恢复正常

## 已知限制

- **没有 Win11 原生 snap** — 拖到屏幕边不会触发贴边、Win+方向键不响应（`overrideredirect` 的代价，0.4.1 走过五轮弯路证明"保 frameless 又要 snap"是坑，这版彻底放弃）
- **纹理只覆盖 Text 控件** — topbar / tab bar / TOC Frame 的背景依然是纯色，因为 Tk Frame 不支持 stipple。如果要全覆盖需要 Frame → Canvas + `create_image` 铺 tile，那是 0.5.0 的工程量
- **不渲染** LaTeX / Mermaid / PlantUML
- **图片** 只支持本地绝对路径，网络图片不拉

## 环境要求

- Python 3.8+（需含 tkinter，Windows 默认包含）
- Windows 10 / 11

没有 pip、没有虚拟环境、没有 Node、没有 .NET。

## 故障排查

### 双击 .md 没反应 / "打开方式"对话框里"始终使用"勾选框灰掉
跑 `install.cmd`。Windows 不把 `.cmd` 批处理当成真应用，所以默认关联设不上。`install.cmd` 在 `HKCU` 下注册一个 ProgID 直接指向 `pythonw.exe`，让 Windows 识别成真的应用。

### 窗口位置不对 / 状态乱了
删掉 `.md-reader-state.json` 重启。

### 进程卡住 / 窗口不响应
删掉 `.md-reader.lock` 后重启。如果 `.md-reader-crash.log` 有新条目，贴到 issue 里。

### 第三方工具（Claude Code 等）改文件后窗口不更新
检查是否处于分屏编辑模式且本地有未保存的改动（edit_dirty）。这种情况下 reader 会保留本地不覆盖外部——`Ctrl+S` 覆盖外部，或关闭编辑模式接受外部。

## License

MIT
