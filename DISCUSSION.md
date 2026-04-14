# DISCUSSION

> **Note for English readers**: This is a time-stamped project
> decision journal kept in Chinese. It records design debates,
> rejected approaches, and post-mortem notes as they happened. If
> you're looking for a user-facing description of the project, see
> [README.md](README.md). If you want a version history in English,
> see the **EN** summary blocks at the top of each entry in
> [CHANGELOG.md](CHANGELOG.md). This file is not intended as
> primary documentation — it's the author's working journal, kept
> public for transparency.

按时间线记录这个项目的决策过程和踩坑实况。

## 2026-04-13 项目启动

### 起源需求
用户希望有一个"渲染后的 markdown 文件阅读器"，配合 Everything 搜到 .md 直接打开。明确不要浏览器，要本地原生体验。

### 0.1.0 — 浏览器 + CDN（被否）
- 方案：PowerShell 把 .md 内容 base64 嵌入 HTML 模板（marked.js + github-markdown-css + highlight.js 走 CDN），写到 %TEMP%，默认浏览器打开
- 文件：`open-md.cmd` + `open-md.ps1`
- **被用户否的原因**：用浏览器打开就是浏览器界面，标签栏、地址栏都不想要；并且 .ps1 在"打开方式"对话框里不显示，用户搞不清 .cmd 和 .ps1 的关系

### 0.2.0 — mshta + HTA + Markdig（被否）
- 方案：cmd 多语言文件单一启动器；Markdig.dll 本地渲染，首次从 nuget 下载缓存；HTA 模板由 mshta.exe 启动
- 解决了"不是浏览器"和"单一文件关联"
- **被用户否的原因**：mshta 弹出的窗口本质是个普通系统对话框，不够独立优雅
- 期间踩坑：Markdig 0.37 依赖 `System.Memory.dll`（PS 5.1 / .NET Framework 4.x 不带）→ 降级到 0.18.3 net452 零依赖；iex 字符冲突 → 改用临时 .ps1 `-File` 运行；`#--PSBEGIN--` 标记被 cmd 命令行字面量误匹配 → `LastIndexOf` 替代 `IndexOf`

### 0.3.0 — Python tkinter frameless 自绘窗口
- 方案：彻底放弃 mshta/HTA，用 Python tkinter 自己写
- 参考同目录 `2026-04-07-桌面置顶卡片-desktop-sticky-card` 的视觉语言
- `overrideredirect(True)` 去掉系统标题栏 + 自绘 1px 边框 + 自绘 Topbar
- 5 个主题（Light/Sepia/Morandi/Nord/Dark）+ 4 档字号（S/M/L/XL）
- 内置简易 markdown 解析器渲染到 `tk.Text`
- 状态持久化（`.md-reader-state.json`）
- 文件：`md-reader.pyw` + `md-reader.cmd`（薄封装 `pythonw md-reader.pyw`）

### 0.4.0 — 同一天的多轮迭代汇总
（参考 CHANGELOG.md 0.4.0 条目，要点）
- **多标签单窗口**：`msvcrt.locking` 单实例 + 文件 IPC（`.md-reader-pending-<pid>-<ts>.txt` 唯一文件名避免竞争）+ 每 350ms 主进程轮询
- **TOC 侧边栏**：解析 h1-h3，点击跳转，状态持久化
- **文件 watcher**：900ms mtime 轮询自动重载
- **自定义主题目录**：`themes/*.json` 启动时合并到 `THEMES`
- **GFM 表格**：`text.window_create` 嵌入 grid Frame
- **半屏默认尺寸**：`SystemParametersInfoW(SPI_GETWORKAREA)` 拿任务栏排除后的工作区，默认靠右半屏
- **最大化按钮 + F11**：用 `ShowWindow(SW_MAXIMIZE/SW_RESTORE)` 模拟（因为 `overrideredirect(True)` 下系统 zoomed 不可靠）
- **TOC 字体修复**：`Segoe UI` → `Microsoft YaHei`，否则中文 bold/regular 回退到 YaHei/SimSun 出现"黑体+宋体"混排
- **字号 slider**：S/M/L/XL 档位 → 连续整数 8-28，`A− N A+` 按钮 + 滚轮 + Ctrl+= / Ctrl+−，其它字号由 body 比例派生

## 2026-04-13 当前在做的事

### 用户提出的两个新方向

1. **Win11 磁吸支持**（snap layouts、Win+方向、拖到屏幕边自动半屏）
   - 用户问"为什么不能用磁吸"
   - 我解释根因：`overrideredirect(True)` 让 Windows 不把它当真窗口，丢失所有 DWM 窗口管理功能
   - 给出三条路：
     - **A** 手动模拟（拖到边检测）— 不够 Win11 原生
     - **B** Win32 自定义标题栏（保 frameless 美观 + 真窗口）— 工程量大但是正解
     - **C** 放弃 frameless 用系统标题栏 — 最简单但失视觉
   - **用户选 B**

2. **WYSIWYG 编辑**
   - 用户希望"在渲染态下直接编辑"
   - 我解释三条路：
     - **A** 仅前向（编辑后保存丢格式）— 文档逐渐塌缩，不可用
     - **B** 双向 WYSIWYG（写反向序列化器）— 150-250 行，表格/链接有损
     - **C** 分屏编辑（顶部渲染 + 底部 raw markdown 双向同步）— 务实方案
   - **用户选"新增可以打开分屏编辑功能"，方向是 C**

### 实施顺序约定
B 是窗口架构性变更，C 是 UI 增量，先做 B 再做 C。**当前正在做 B，C 还未开始。**

### B 的实施踩坑实况

1. **第一次实现** — `SetWindowLongPtrW(GWLP_WNDPROC)` + `CallWindowProcW` 老式 wndproc 子类化
   - 加 `WNDPROC_TYPE` ctypes WINFUNCTYPE 包装回调
   - `WM_NCCALCSIZE` 返回 0 让客户端区域延伸到窗口边
   - `WM_NCHITTEST` 返回 `HTCAPTION/HTLEFT/HTBOTTOM/HTMAXBUTTON` 等
   - 编译 + 启动 OK，窗口风格位正确（`WS_CAPTION=False, WS_THICKFRAME=True`）
   - **但点击最大化按钮闪退**

2. **第一轮修复尝试**
   - 把 `WNDPROC` 返回类型从 `c_long` 改成 `c_ssize_t`（64 位 LRESULT 是 8 字节）
   - `_toggle_max` 的 ShowWindow 调用从 wndproc 内同步改成 `after_idle` 异步
   - **还是闪退**，无 Python 异常日志（说明是 C 层崩溃）

3. **第二轮 — 换用 `SetWindowSubclass`**
   - 改用 comctl32 的 `SetWindowSubclass + DefSubclassProc` 现代 API（保留 Tk 的 wndproc，由 comctl32 维护订阅链）
   - 移除 `WM_NCLBUTTONDOWN(HTMAXBUTTON)` 拦截，让默认流程处理
   - 监听 `WM_SIZE` 同步 `self.maximized` 状态
   - **第一次最大化成功，但点还原按钮还是闪退**
   - 崩溃日志为空 → 仍是 C 层崩溃，怀疑 `DefSubclassProc` 处理 HTMAXBUTTON 时调 DWM 画"按下"视觉，而我们没有标准非客户区 → DWM 解引用空指针

4. **第三轮（当前实施）**
   - 加 `faulthandler.enable()` 写 `.md-reader-crash.log`，下次 C 层崩溃会留 C 调用栈
   - **自接管 `WM_NCLBUTTONDOWN/UP(HTMAXBUTTON)`**：DOWN 直接 `return 0`，UP 走 `after_idle → _toggle_max_native`
   - `_toggle_max_native` 用 `IsZoomed(hwnd)` 实时判方向，不依赖 `self.maximized` 字段
   - **等用户验证**

### 已确认正常的能力
- 单实例 + 多标签 + 标签 IPC
- TOC 侧边栏渲染和跳转
- 字号 slider 8-28 + 滚轮 + Ctrl+= / Ctrl+−
- GFM 表格、引用、列表、代码块渲染
- 主题切换、状态持久化
- `Win+←/→` 半屏（已经因为 `WS_THICKFRAME` 自动获得）
- 拖 Topbar 到屏幕边的 Aero Snap（同上）
- F11 切最大化（走 Tk 路径，未触发 HTMAXBUTTON）

### 已确认有问题的能力
- 点击 Topbar 上的 `□`/`❐` 按钮在最大化和还原之间切换（HTMAXBUTTON 触发）→ 第三轮修复中

### 已知设计取舍
- 鼠标 hover `□` 按钮时 Tk 的 hover 变色不会触发（因为 Windows 把这块识别为非客户区，Tk 收不到 Enter 事件）。这是 HTMAXBUTTON 必须付的代价 — 要 Win11 4 宫格 snap 选择器就丢这个 hover 高亮

## 2026-04-13 22:40 第二轮：用户报 "放大到全屏后卡退" + 依然无法移动

### 从诊断日志反推用户行为
`.md-reader-crash.log` 抓到的 NCHITTEST 轨迹：
```
hit#1 cx=267 cy=145 -> CLIENT   # 用户一开始在正文区乱点试图拖拽
hit#2-8 cx=~1200 cy=12 zoomed=1 -> CAPTION  # 后来在 max 之后的窗口上部
```
读出两件事：
1. 用户**从来没真的命中过 63 px 高的 topbar 拖拽带**。他们以为整个"白色/主题色"上边都是标题栏，实际只有最顶上 ~30 逻辑像素那一条是 HTCAPTION。这不是 bug 是 UX 事故。
2. 用户点了 max 按钮成功最大化后，再点 "□/❐" 还原 → 进程静默消失（faulthandler 没抓到栈，说明死在 C 层）。

### 用 PostMessage 复现 HTMAXBUTTON 闪退
冷启动 → 用 `SendMessage(WM_NCHITTEST)` 扫到 max 按钮位置 → `PostMessage(WM_NCLBUTTONDOWN/UP, HTMAXBUTTON)` → **第一次点击就 alive=0**。即便 DISCUSSION 里第三轮已经"自接管 DOWN/UP 返回 0 + UP 里 after_idle 调 _toggle_max_native"，该路径依然会杀进程。结论：**HTMAXBUTTON 在我们这个自定义 chrome 上就是一颗未爆弹**。不管自接管还是交给 DefSubclassProc，DWM 的 max 按钮视觉层都会碰到不存在的非客户区状态然后挂掉。

### 为什么用户能"放大到全屏"但不能还原
他们大概率用的是 Win+↑ 或者双击 topbar（走 OS 默认 WM_SYSCOMMAND 路径），而还原时用的是 "□/❐" 按钮（走 HTMAXBUTTON → 炸）。这和我们 ShowWindow(SW_MAXIMIZE) 的裸调用（b31/b41 都验证过稳定）没关系——问题就是 HTMAXBUTTON 那条入口。

### 第四轮修复（当前）
彻底放弃 HTMAXBUTTON。换思路：把最大化按钮**当成普通客户区 Tk Label**处理，Win11 的 snap layouts 4 宫格悬浮预览也一并放弃——换来稳定。
1. `_hit_test` 删掉所有 `_HTMAXBUTTON` 返回，统一返回 `_HTCLIENT`，让 Tk 的 `<Button-1>` 绑定接住 → 走 `_toggle_max` → `ShowWindow(SW_MAXIMIZE/RESTORE)`（这条路径 b31/b41 验证过双向稳）。
2. `_wndproc` 删掉 `WM_NCLBUTTONDOWN/UP + HTMAXBUTTON` 的拦截分支。
3. 把拖拽区从"只有 topbar"扩到"topbar + tab bar"：新增 `_get_drag_area_height() = topbar_h + tab_holder_h`（~111 物理像素 = ~55 逻辑像素），`_hit_test` 在这整个区间内，只要没命中按钮/标签就返回 HTCAPTION。用户现在从哪块"顶部空地"都能拖。
4. 新增 `_tab_hit()` — 用**预先注册**的 `self._tab_click_widgets` 列表来命中 tab 标签/关闭按钮，**不在 NCHITTEST handler 里动态走 winfo_children**（Tcl 不是完全可重入的，从 Win32 消息泵回调里递归遍历 Tk 部件族会偶发炸，b39 外部扫描观察到过）。`_populate_tabs` 每次重建时刷新这个列表。

### 验证（本机）
- b41：ShowWindow(SW_MAXIMIZE) ↔ ShowWindow(SW_RESTORE) 跑四回合，`alive=1 zoomed` 正确翻转 ✓
- b42：NCHITTEST 沿 y 扫描，dy=3→HTTOP / dy=20-105→HTCAPTION / dy=130+→HTCLIENT ✓（拖拽区 111 px 有了）
- b42 扫完 HTMAXBUTTON 统计：**0 次**，确认删干净 ✓
- b44：启动后不动、不扫它，3 秒后还活着 ✓
- 已知注意：从另一个进程密集 SendMessage(WM_NCHITTEST) 会偶发打挂窗口（Tcl 重入风险），但那是测试机的脚本副作用，不是用户真鼠标交互路径。

### 还要用户验证
- [ ] 真人鼠标：点 □ 最大化 / 点 ❐ 还原 / 双击顶部切换，都不能 卡退
- [ ] 真人鼠标：从 tab bar 空地拖拽能移动窗口
- [ ] 真人鼠标：字号连击 A+ 不再全量重建卡顿（180 ms 防抖）

## 2026-04-13 23:25 **终章**：认输，回退到 overrideredirect

### 第五轮用户还是卡退
日志抓到 zoomed=1 heartbeat 两条之后进程直接消失，faulthandler 零栈。第五轮的 `WM_NCCALCSIZE` 不动 rgrc + `SC_MOVE 拦截 + WM_NCLBUTTONDBLCLK 拦截` 方案仍然没救回来。用户问"之前的参考项目都是怎么做的"。

### 去看参考项目
`D:\ClaudeCodeWorkspace\2026-04-07-桌面置顶卡片-desktop-sticky-card\sticky-card.pyw` — **`overrideredirect(True)` + Tk 级别手动 drag/resize**。零 Win32 subclass、零 NCHITTEST、零 NCCALCSIZE、零 DWM 交互。就是朴素地：
- `root.overrideredirect(True)`
- 给 topbar 几个 widget bind `<Button-1>/<B1-Motion>` 记坐标 + `root.geometry()` 移动
- `root.bind("<Motion>")` 检测边沿改 cursor + 边沿拖拽 resize

这条路径**被验证过几个月稳定**，只是因为 Win11 snap 不支持所以 0.3.0 → B 路换掉了。

### 现实是
用户为了要 Win11 snap 走 B，结果 B 炸了五轮，**到最后 Win11 snap 也没用上**（因为窗口每次都卡退）。所以实际状态是：付了 frameless 的所有工程成本，没拿到任何收益。

**决策：彻底放弃 B，回退到 sticky-card 的 A 路径**。丢失 Win11 原生 drag-to-edge 贴边，换回窗口稳定。

### 改动
1. `__init__` 加 `self.root.overrideredirect(True)`
2. **删光** `_setup_custom_chrome / _wndproc / _hit_test / _button_hit / _tab_hit / _get_topbar_height / _get_drag_area_height / _on_max_state_changed / _diag / _heartbeat`
3. `_toggle_max` 只保留 Tk-only 路径：`self.normal_geo = root.geometry()` + `root.geometry(work_area)` 切换
4. `_show_window` 不再调 `ShowWindow`，纯 `deiconify + lift + focus_force`
5. `_build_ui` 末尾给 `topbar / topbar_inner / tab_holder` 三个 widget 绑 `<Button-1> → _drag_start`、`<B1-Motion> → _drag_move`、`<Double-Button-1> → _toggle_max`。topbar 上的 Label 按钮和 tab 标签有自己的 Button-1 binding，Tk 事件分发优先命中更具体的 widget，不冲突。
6. `root` 绑 `<Motion>/<Button-1>/<B1-Motion>/<ButtonRelease-1>` 用已有的 `_resize_cursor/_resize_start/_resize_move/_resize_end`（这些方法之前就写好了但没被 wire 起来，之前是死代码，现在激活）
7. Win32 常量和 `_user32/_comctl32` 绑定留在模块顶部作为惰性导入，不主动调用

### 验证
- b65: 语法 OK，冷启动 alive ✓
- b66: 新窗口 style=0x96000008 = WS_POPUP + WS_VISIBLE + clip siblings/children，**没有** WS_CAPTION / WS_THICKFRAME ✓
- b68: 删掉 state.json 后冷启动 rect=(1536,0,3072,1824) 正好是右半屏工作区 ✓
- 真人鼠标拖拽/缩放/max 还原：**交给用户验证**

### 取舍
- 丢失：Win11 拖到屏幕边贴边、Win+方向键 snap、snap layouts 4 宫格预览
- 保留：F11 最大化 / ❐ 按钮最大化 / 双击顶部最大化 / 字号 / 主题 / tab / TOC / 所有内容渲染
- 如果将来又想要 Win11 snap，**不要再碰自定义 chrome**，换思路：用系统标题栏 + DwmExtendFrameIntoClientArea 把内容延伸到标题栏下方

## 2026-04-13 23:00 第三轮：用户报 "又变成全屏然后卡死"

### 从日志反推
第二轮修复之后，用户又试了一遍。日志显示：
```
hit#1 cy=146 -> CLIENT        # 又在正文区乱点
[7 秒静默]
hit#2-8 cy=12 zoomed=1 -> CA  # 已经 max 了，鼠标在顶部 y=12 扫过
[日志在 hit#8 之后停]
```
信息量更大的是：**日志里全程没有 "hit → max button" 的记录**。意味着用户根本没点到我们的 max 按钮。他们是**双击顶部**进的 max 态。然后在 max 态下鼠标横扫 topbar — 这个轨迹非常像**试图拖拽 topbar 把窗口从全屏拉回来**（Windows 默认的 drag-to-restore 手势）。

### 根因猜想：drag-to-restore 路径炸
Windows 对 `HTCAPTION 点击拖拽 maximized 窗口` 的默认处理是：
1. `DefWindowProc` 把 `WM_NCLBUTTONDOWN + HTCAPTION` 内部转成 `WM_SYSCOMMAND + SC_MOVE`
2. SC_MOVE 在 maximized 状态下会走一条特殊路径：先 `SW_RESTORE` 再 "恢复到光标位置跟手"
3. 这条路径会和我们的自定义 chrome（特别是 `WM_NCCALCSIZE` 的 zoomed 分支）打架 → 卡死

另外 `WM_NCCALCSIZE` 的 zoomed 分支本身也可疑 — restore 动画期间 rect 会快速变化，我们每次都改 rgrc[0].left/top/right/bottom，可能让 client area 短暂变成负尺寸，Tk 渲染进去就卡。

### 第五轮修复
1. **`WM_NCCALCSIZE` 不再改 rgrc**。不管 zoomed 不 zoomed 都直接 `return 0`（client=window）。代价：最大化时 topbar 右边会被屏幕外溢出的 12 px 吃掉一点，可忍。
2. **拦截 `WM_SYSCOMMAND + SC_MOVE + zoomed`**：直接 `ShowWindow(SW_RESTORE)` 不跟手。用户丢失"拖 maximized 窗口还原并跟手"的手势，换来不会卡死。
3. **拦截 `WM_NCLBUTTONDBLCLK + HTCAPTION`**：改走我们自己的 `_toggle_max` 路径，绕开 DefWindowProc 的双击处理（那条路径也会走 SC_MAXIMIZE/SC_RESTORE 内部流程，可能和 chrome 状态打架）。
4. **大幅加诊断**：
   - heartbeat 每 2 秒写一条 `zoomed=? maxflag=?`，能判断 Tk mainloop 是真卡死还是只是视觉看起来卡
   - 记录 `WM_SYSCOMMAND`、`WM_ENTERSIZEMOVE`、`WM_EXITSIZEMOVE`、`WM_NCLBUTTONDBLCLK`
   - hit 日志 cap 从 8 提到 50，且连续相同结果去重（连续移动中拿到 N 次 CAPTION 不重复写）

### 本机验证
- b53: 外部 `WM_SYSCOMMAND(SC_MAXIMIZE)` → `SC_MOVE` → `SC_MAXIMIZE` → `SC_RESTORE` 走完，进程 alive，日志显示 `syscommand SC_MOVE on zoomed → SW_RESTORE` 正确触发 ✓
- b56: 冷启动 5 秒后 heartbeat 连续两条，zoomed=0 ✓
- 已知测试副作用：外部进程 `SendMessage(WM_NCHITTEST)` 密集投递会偶发打挂窗口（Tcl 非完全可重入），不是用户路径不用管

## 2026-04-13 17:00 第一轮：用户报 bug：窗口卡死在半屏 + 缩放卡顿

### 用户原话
"打开是可以打开，但是会固定为在桌面的一半，没有办法去移动它，没有办法去控制大小，放大缩小也非常卡顿。"

### 排查

1. **环境探测**：3 显示器，主屏 3072×1920 物理像素 / 200% DPI，工作区 3072×1824。state.json 写的是物理像素（1562×1895 @ 1536,0），刚好是右半屏 — "stuck at half screen" 其实是**默认的右半屏初始位置**，不是 bug。
2. **跑动实例 enum**：抓到一个 hwnd style=0x170f0008，**WS_MAXIMIZE 位是亮的**，但 state.maximized=false。说明上一会话点了 □ 后状态没回写干净，下次启动就带着 WS_MAXIMIZE 复活了。
3. **冷启动复测**：杀干净所有 pythonw、清 lock、重启 → style=0x060f0008（无 WS_MAXIMIZE）；用 SendMessage(WM_NCHITTEST) 沿 y 轴扫描：
   - 顶 0–5 px → HTTOP（上沿 resize）
   - 6–65 px → HTCAPTION（topbar 拖拽区）
   - 80+ px → HTCLIENT（正文）
   - 左/右/下边沿 → HTLEFT/HTRIGHT/HTBOTTOM ✓
4. **结论**：自定义 chrome 在冷启动时是**正常工作**的。用户遇到的 "不能移动" 大概率是因为 (a) 残留的 WS_MAXIMIZE 让窗口处于"被认为是最大化但 rect 不是全屏"的诡异中间态，导致拖动行为被抑制；(b) 也可能是 topbar 高度过窄不容易点中。

### 修复（已落地）

1. **冷启动强制 restore**：`_setup_custom_chrome()` 末尾，如果 `state.maximized=false` 但 `IsZoomed(hwnd)=true`，立即 `ShowWindow(SW_RESTORE)`，断掉残留 WS_MAXIMIZE 链。
2. **topbar 命中区加固**：`_get_topbar_height()` 改成缓存历史最大值 + 用 `winfo_reqheight()` 兜底 + 强制最低 32 px，避免初始化期间 winfo_height=1 误判。
3. **字号缩放卡顿**：原 `_bump_font` 直接调 `_rebuild()`（销毁整个 UI + 重 parse markdown），快速点 A+ 时每次都全量重建 → 卡顿。改成 180 ms 防抖：先即时刷数字标签做反馈，180 ms 内的连击合并成一次 rebuild。
4. **诊断日志**：新增 `_diag()` 写入 `.md-reader-crash.log`，启动时记 hwnd / style / zoomed / topbar_req；前 8 次 NCHITTEST 也记 cx/cy/topbar_h/zoomed/result。便于用户复现时回传。

### 验证结果（本机）
- 启动后 `_diag` 输出：`style_after=0x060f0008 zoomed=0 topbar_req=61` ✓
- 外部 SendMessage 探针：HTCAPTION/HTCLIENT/HTTOP/HTLEFT/HTRIGHT/HTBOTTOM 全部正确返回 ✓
- 编程 SetWindowPos 移动+缩放 OK ✓
- 真人鼠标拖拽测试 = **待用户验证**

## 待办

- [ ] **B 路收尾**：等用户验证 `□`/`❐` 是否还崩，崩则看 `.md-reader-crash.log` 里的 C 调用栈
- [ ] **C 路（分屏编辑）**：B 稳定后开始
- [ ] **README 重写**：现在的 README 还停留在 mshta + Markdig 时代，与 0.4.0 后的实际严重不符
- [ ] **CHANGELOG 0.5.0**：等 B + C 都收尾后写一个新版本号

## 2026-04-14 从 .cmd 迁移到 .exe

### 起因
用户反映：把 md-reader 作为 `.md` 默认应用时，"打开方式"对话框里出现多条 "MD Reader"，选任何一条都反复弹出该对话框，无法真正选定。

### 排查链
1. **多条重复项的来源**：`HKCU\Software\Classes\Applications` 下留有 `md-reader.cmd` 和 `open-md.cmd` 两条旧条目，路径还指向 `D:\ClaudeCodeWorkspace\2026-04-13-markdown阅读器-md-reader\`（老路径，后来在外层加了 `2026-04-05-AI编程学习-learning-ai-coding\` 父目录，原路径彻底失效）；加上本次新建的 `MDReader.File` ProgID，共 3 条
2. **点选后反复弹窗的根因**：
   - 两条旧 Applications 条目启动时目标不存在 → 失败 → 回落到"选择应用"
   - 新建的 `MDReader.File` ProgID 用 `.cmd` 作为 open command → **Windows 10/11 不接受 `.bat`/`.cmd` 作为合法默认应用**，对话框会反复弹
3. **UserChoice 锁死**：`FileExts\.md\UserChoice` 指向已失效的 `Applications\md-reader.cmd`。该键受 DENY ACL 保护（Win10 以来的反劫持机制），脚本无法删除或覆写，只能通过"设置 → 默认应用"UI 让 Windows 自己重算 Hash

### 决策：打包成单文件 .exe
- 工具：PyInstaller `--onefile --windowed --name md-reader`
- 产物：`dist\md-reader.exe`（~11 MB，单文件，自带 Python 运行时 + tkinter，纯 stdlib 依赖零外部包）
- **关键验证**：`SCRIPT_DIR = os.path.dirname(os.path.abspath(sys.argv[0]))` 用的是 `sys.argv[0]` 而非 `__file__`，在 PyInstaller `--onefile` 下会正确解析到 `.exe` 所在目录而非临时解压目录。状态文件/锁文件/崩溃日志路径都不用改代码
- 冒烟测试：用 `dist\md-reader.exe` 打开含中文路径的 InsForge README，tasklist 看到两个 md-reader.exe 进程（主进程 + 单实例 IPC 子进程）正常驻留

### 清理动作
- 删除 `HKCU\Software\Classes\Applications\md-reader.cmd` 和 `open-md.cmd`
- 删除 `FileExts\.md\OpenWithList` 中 MRU 里残留的 `md-reader.cmd` 条目
- `MDReader.File\shell\open\command` 改指向 `dist\md-reader.exe "%1"`
- `MDReader.File\DefaultIcon` 指向 `dist\md-reader.exe,0`
- **用户需手动完成的最后一步**：Win11 UserChoice ACL 限制，必须通过 `设置 → 应用 → 默认应用 → .md` 选 **Markdown (MD Reader)**，让 Windows 自己重算 UserChoice Hash

### 遗留 TODO
- [ ] 把 `dist\md-reader.exe` 复制到不含中文的稳定目录（如 `D:\Tools\md-reader\`），避免源目录重命名再次失效
- [ ] `build\` 和 `md-reader.spec` 加入 `.gitignore`
- [ ] 给 exe 配真正的 `.ico` 图标（当前跳过，banner.jpg 不能直接作为 `--icon`）
- [ ] 考虑把 PyInstaller 打包步骤写进 CHANGELOG.md 0.5.0 条目

## 文件清单当前状态

| 文件 | 状态 |
|---|---|
| `md-reader.pyw` | ~870 行，含 Win32 自定义 chrome（实施中） |
| `md-reader.cmd` | 薄封装，调 pythonw（保留作为开发期启动器） |
| `dist/md-reader.exe` | **PyInstaller 打包产物，当前推荐作为关联默认** |
| `md-reader.spec` | PyInstaller 配置文件（自动生成） |
| `build/` | PyInstaller 中间产物（建议加入 .gitignore） |
| `test-sample.md` | GFM 测试覆盖标题/列表/任务/代码/表格/引用/中英混排 |
| `README.md` | **过时**，停在 mshta 方案 |
| `CHANGELOG.md` | 0.4.0 已写到位，0.5.0 待开 |
| `DISCUSSION.md` | **本文件** |
| `.md-reader-state.json` | 运行时生成 |
| `.md-reader.lock` / `.md-reader-pending-*.txt` | IPC 文件 |
| `.md-reader-crash.log` | faulthandler 崩溃日志（按需生成） |
| `test-sample-en.md` | 英文样例，专门用于验证翻译 / 中英对照模式 |

## 2026-04-15 0.5.0 — 英译中 / 中英对照阅读模式

### 需求
用户读英文 md 文档时希望一键出中文，或者原文+译文对照着看。明确两条约束：只做英→中；翻译引擎用 lark-cli 或"其他已有服务"。

### 翻译引擎选型
第一候选是 lark-cli，但 `lark-cli schema translation` 报 "Unknown service"，直接调 `/open-apis/translation/v1/text/translate` 也 404——飞书开放平台并不对外暴露机器翻译 API。

第二候选是 Claude API，但环境里没有 `ANTHROPIC_API_KEY`，现场让用户配 key 太重，否决。

最终选 **Google Translate `gtx` 公共端点**（`translate.googleapis.com/translate_a/single?client=gtx`）：免 key、质量可接受、响应快。用户已有 Clash 代理跑在 `127.0.0.1:7897`（carnival 项目留下的），直接复用。代理地址通过 `MD_READER_PROXY` 环境变量可覆盖，不强依赖固定端口。

现场实测三段：`**bold**` 和中文标点都保留得很干净，质量可以接受作为"扫读辅助"——正式翻译场景本来就不应该指望 gtx。

### 为什么不用整文档批量翻译
最初想过把整个 md 一次性发给 gtx，省往返时间。问题是「中英对照」模式需要把译文按 block 对齐回原文，整文档翻译后再切块几乎不可能对齐（Google 会合并/拆分段落）。所以架构从一开始就选**段落级切块 → 逐段翻译 → 段落级重组**。

### 切块策略
`extract_md_blocks` 基本上是把 `_render` 的 line-based parser 复刻了一遍，但产出数据而非渲染指令。四种 block：

- `verbatim`：代码块 / 空行 / HR / 表格 / ——整块原样留下，翻译层不碰
- `prefixed`：标题 / 列表项 / 任务项——拆成 `prefix + text`，只翻 text，重组时前缀拼回去
- `quote`：blockquote 连续行折叠成一段，重组时加回 `> ` 前缀
- `para`：普通段落连续行折叠（用空格 join），重组时按原样或译文输出

表格特意走 verbatim：monospace 表格翻译后中英宽度不一致，列对齐会爆，ROI 低。

### 三态渲染
翻译层只做 `markdown → markdown` 变换，下游 `_render` 完全不动。三态：

- `orig`：原文直出
- `zh`：每个可翻译 block 替换为中文
- `bi`：每个可翻译 block 输出 `原文 + 空行 + 译文`，让 `_render` 把它们当成两个独立段落处理——零额外状态，视觉上就是"英中英中"交错

这个设计的关键是复用 `_render_active(src_override=...)` 这个既有参数——翻译功能本质上只是个预处理器，跟现有渲染路径零耦合。

### 缓存
两级：

1. **磁盘译文缓存** `%LOCALAPPDATA%\md-reader\translate-cache.json`，key = `sha1(原文)`，跨会话 / 跨文件共享。同一句话在不同文档里命中同一条。
2. **tab 级 block 切片缓存** `tab["trans_blocks"]`，避免每次切换三态都重解析。文件 mtime 变化时丢弃切片缓存（但不丢译文缓存）。

### 异步
翻译跑在 `threading.Thread(daemon=True)` 里，完成后通过 `self.root.after(0, ...)` 回到 Tk 主线程重渲染。翻译中按钮显示 `…` 防重复触发。段落间目前**串行**调用 gtx，N 段 ≈ N×200ms，几十段的文档 2-5 秒能出结果；如果以后大文档体感卡，可以改 `ThreadPoolExecutor(max_workers=6)` 并发。

### 踩坑
- 第一版 `_build_ui` 里读 `self.tabs[self.active].get("trans_mode")` 但首次 build 时 `self.active == -1`（tab 还没 open），需要 guard `if self.tabs and 0 <= self.active ...`
- `_switch_tab` 需要额外调 `_refresh_trans_btn`，否则切 tab 时按钮还显示上一个 tab 的状态
- smoke test 用 Windows cmd 打印中文是乱码（cp936 vs utf-8），写文件读就正常——跟功能无关
- 没有原生 lark-cli 翻译命令是个意外，文档里 Lark 有「文档翻译」但没有「纯文本翻译」的开放 API
