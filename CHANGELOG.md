# Changelog

本项目所有重要变更都记录在此文件中。
格式参考 [Keep a Changelog](https://keepachangelog.com/zh-CN/1.1.0/)。

## [0.5.0] - 2026-04-15

### 新增

- **英译中 / 中英对照阅读模式**：顶栏新增翻译按钮，三态循环「原 → 双 → 中」，快捷键 `Ctrl+T`
  - 调用 Google Translate 公共端点 `translate.googleapis.com/translate_a/single?client=gtx`（免 key），通过本地代理 `http://127.0.0.1:7897` 出海，可用 `MD_READER_PROXY` 环境变量覆盖
  - 段落级粒度：按 block 切块翻译而非整文档打包，原因是要支持「双语对照」需要保持段落对齐，整文档翻译后无法按 block 交错回去
  - 切块逻辑 `extract_md_blocks`：mirror 渲染器的 line-based parser，产出 `verbatim`（代码块 / 空行 / HR / 表格）、`prefixed`（标题 / 列表 / 任务项，保留 `#`、`- `、`1. ` 等前缀）、`quote`、`para` 四种 block 类型；只对含英文字母的 block 发起翻译，中文块直接跳过
  - 代码块 / 表格 / 链接 URL 全部走 verbatim 路径不翻译；行内 `**bold**`、`` `code` ``、`[link](url)` 交给 gtx 原样保留（实测 Google 保留得很干净）
  - 三态切换直接复用已有的 `_render_active(src_override=...)` 入口：翻译层只做 `markdown → markdown` 的变换，渲染器完全不动
    - `orig` 模式：原文直出
    - `zh` 模式：每个可翻译 block 替换为中文
    - `bi` 模式：每个可翻译 block 输出 `原文 + 空行 + 译文` 交错，让下游 `_render` 像渲染两个普通段落一样处理
- **磁盘缓存**：`%LOCALAPPDATA%\md-reader\translate-cache.json`，key = `sha1(原文)`，跨会话复用；文件 mtime 变化时仅丢弃当前 tab 的 block 切片缓存，译文缓存保留（同一段英文若未变仍命中）
- **异步不阻塞 UI**：翻译跑在 `threading.Thread(daemon=True)` 里，完成后 `root.after(0, ...)` 回到 Tk 主线程重渲染；翻译中按钮显示 `…`，避免重复触发
- 每个 tab 独立记忆 `trans_mode` 和 block 切片

### 变更

- 新增 import：`hashlib` / `threading` / `urllib.request` / `urllib.parse`
- `_open_tab` 在 tab dict 里多塞了 `trans_mode` / `trans_blocks` / `trans_busy` 三个字段
- `_switch_tab` 末尾调 `_refresh_trans_btn`，按钮随 tab 切换刷新

## [0.4.8] - 2026-04-14

### 变更

- **分发方式从 `.cmd + pythonw + .pyw` 正式迁到 `dist\md-reader.exe`**
  - PyInstaller `--onefile --windowed md-reader.pyw` 打出 ~10 MB 的单文件 PE exe
  - `.gitignore` 调整：`dist/` 下除 `md-reader.exe` 外仍忽略，现在仓库直接带出这一份 exe，朋友 clone 即用，不需要本机装 Python
  - `install.cmd` 重写：ProgID `MDReader.Markdown` 和 `Applications\md-reader.exe` 都指向真 PE exe，而不是 `pythonw.exe + .pyw`
  - 背景：0.4.6 版本依赖 `pythonw.exe + .pyw` 路径，Win10/11 UserChoice 在某些机器上会 hash-lock 住无法写入；只有注册真 PE exe 才能在"打开方式"对话框稳定勾上"始终使用"
  - `md-reader.cmd`（源码启动器）保留不变，用于开发时直接从 `.pyw` 启动

### 优化

- **大文档预览性能**：用户反馈"md 内容过多就卡"。定位到 5 个瓶颈并全部修复——
  - **批量渲染**：`_render` 改为先在 Python 里拼纯文本 `parts` + 收集 `(start, end, tag)` span 列表，然后单次 `insert("1.0", big)` + 合并相邻同 tag span 后批量 `tag_add`（索引用 `1.0 + N chars` 形式）。Tk 往返从"每段一次 insert + 每段一次 tag"降到"每合并区间一次 tag_add"。heading mark 也改成插入后按字符偏移 `mark_set`
  - **表格降级**：`_render_table` 原本每张表建 `tk.Frame` + N×M 个 `tk.Label` 再 `window_create` 嵌进 `tk.Text`，embedded window 滚动时重绘代价极高，多表格文档直接拖死。现改为 monospace 纯文本渲染——新增 `_display_width`（用 `unicodedata.east_asian_width` 正确处理 CJK 全角宽度）和 `_pad_cell`（左/右/居中对齐填空格），新增 `table_head / table_row / table_row_alt` 三个 MONO 字体 tag（表头 topbar bg + 粗体，行交替 bg）。彻底不用 embedded window
  - **paper bgstipple 阈值**：`>60000 chars` 的文档跳过 `tag_add("paper", "1.0", "end")`，避免 bgstipple 全局逐像素重绘。小文档保留纸质颗粒
  - **去掉 `_render_active` 里的 `update_idletasks()`**：这个强制同步刷新会放大首帧卡顿
  - **live preview debounce 动态化**：`_on_edit_change` 按 doc_chars 分级——`<30k` = 250 ms / `<60k` = 500 ms / `>60k` = 900 ms，auto-save 同步放宽到 `max(900, live_ms + 200)` ms。之前写死 250 ms 对大文档太激进，每次 pause 都全量重渲染 → UI 冻结
- **新常量**：`LARGE_DOC_CHARS = 60000`（paper 阈值 + debounce 分级共用）
- **新 import**：`unicodedata`（用于 CJK 宽度计算）

## [0.4.7] - 2026-04-14

### 修复

- **渲染区无法选中复制文本**：正文 `self.text` 在 `_render_active` 末尾被 `configure(state="disabled")`，tkinter 下 disabled Text widget 会完全禁用鼠标选区，用户点击拖动毫无反应。修复思路是"read-only but selectable"：保持 `state="normal"`，改为在控件级拦截所有写入类事件
  - 新增 `_readonly_keypress`：`<Key>` 回调，只放行 `Ctrl+C / Ctrl+A / Ctrl+Insert / Ctrl+Home / Ctrl+End` 以及方向/翻页/Shift/Ctrl 等导航与修饰键，其他全部 `return "break"`
  - 屏蔽 `<<Paste>>` 和 `<<Cut>>` 虚拟事件
  - 删除 `_render_active` 里的 `state="normal"` / `state="disabled"` 成对调用（delete + insert 在 normal 态本来就 OK）
  - 鼠标选区、Ctrl+C 复制恢复正常；用户仍然无法通过键盘编辑正文
- **注意**：单实例架构下 `md-reader.cmd` 只把路径转交给已在运行的窗口，不会重载 Python 代码，升级后需要手动关闭现有 MD Reader 再重新打开

## [0.4.6] - 2026-04-14

### 新增

- **`install.cmd` 一次性注册 .md 文件关联**。解决 Win10/11 "Open With" 对话框的已知行为：当用户选择 `.cmd` 批处理文件作为"打开方式"时，"始终使用此应用" 勾选框被灰掉 —— Windows 不把批处理当成真应用。脚本在 `HKCU` 下注册 ProgID `MDReader.Markdown`，直接指向 `pythonw.exe "md-reader.pyw" "%1"`，Windows 识别后 "始终使用" 就能勾。
  - 写入路径：`HKCU\Software\Classes\MDReader.Markdown\shell\open\command`
  - `.md` 扩展名的 `OpenWithProgids` 里挂 `MDReader.Markdown`
  - `Applications\pythonw.exe\SupportedTypes` 里挂 `.md`
  - 跑完用 `SHChangeNotify(SHCNE_ASSOCCHANGED)` 刷一下 shell
  - 不需要管理员权限（全是 HKCU）
  - `install.cmd /uninstall` 卸载

## [0.4.5] - 2026-04-14

### 改动

- **新增 Medium 主题 + 删除 Kraft**：Medium.com 白纸风格，纯白 `#FFFFFF` 底 + 近黑 `#292929` 文字 + 标志性绿 accent `#1A8917`。Kraft 整体删除。`_LEGACY_THEME` 迁移表更新：`Light → Medium`（都是干净白 + 绿），`Sepia/Kraft → Parchment`（最接近的暖纸兜底），其他不变。主题循环顺序：Parchment → Medium → Rice → Linen → Ink

### 修复

- **`_rebuild` 丢失未保存编辑**：切主题 / 切字号 / 折叠 TOC 时走 `_rebuild()` 会 `outer.destroy() + _build_ui()`，新的 `edit_text` 是空白，然后 `_render_active()` 从磁盘重读 —— 如果用户有未保存的编辑就全丢了。修复：重建前 snapshot `edit_text.get("1.0", "end-1c")` 和 `edit_dirty`，重建后用 `_edit_sync_guard` 灌回去，再 `_render_active(src_override=preserved_edit)` 从 buffer 重渲染（不从磁盘）
- **顶部 tab 字体黑粗体突兀**：active tab label 原来用 `font=(..., "bold") + fg=self.t("title")`（每主题最深色），纸质主题下看着像硬塞的黑粗体。改成非加粗 + `fg=self.t("fg")`，active 态依然可辨（靠 2 px accent 条 + 背景色变化）

### 双向同步能力升级（edit 模式 + 外部编辑）

0.4.4 的 edit 模式有两个真实 gap：(1) 只在 Ctrl+S / 切 tab / 关窗口时写盘，不是自动保存；(2) edit 模式开着时 watcher 完全跳过外部 mtime 变化，Claude Code 等第三方工具改文件时 reader 看不到。这版全修掉：

- **自动保存**：`_on_edit_modified` 除了触发 250 ms live-render 防抖外，额外触发 900 ms 的 `_auto_save_edit` 防抖 → `_save_edit_buffer` 写盘 → bump `tab.mtime` 防 echo。Ctrl+S 依然可用做即刻保存
- **edit 模式下的外部变更同步**：`_poll_file_changes` 重写成三分支：
  - `edit_visible=False`：老路径，直接 `_render_active()` 从磁盘重渲染
  - `edit_visible=True` 且 `edit_dirty=False`：外部进程改了文件，本地没脏 buffer → 拉文件内容到 edit buffer（用 `_edit_sync_guard` 包 insert 防止触发 `<<Modified>>`）+ `_render_active(src_override=src)` 重渲染正文
  - `edit_visible=True` 且 `edit_dirty=True`：冲突 —— 外部改了文件同时本地也有未保存编辑。保留本地 buffer（不覆盖），写 `external_edit_conflict` 到 crash log，更新 `tab.mtime` 避免 spam。用户用 Ctrl+S（保留本地覆盖外部）或关闭 edit 模式（下次 watcher tick 接受外部）解决
- **本机验证**：b95 外部进程 rewrite 文件，viewer mode 正确 reload ✓；b96 预设 `edit_visible=true`（buffer 不脏），外部 rewrite 文件，reader 正确 pick up + 没有覆盖外部内容，crash log 无冲突 ✓

### 文件变化

- `md-reader.pyw`: ~1630 行 → ~1690 行
- state schema 变动：`theme: "Kraft"` 的老状态会自动迁移到 `Parchment`

## [0.4.4] - 2026-04-14

### 新增

- **分屏编辑模式**（DISCUSSION.md 里的 C 路方案，从 0.4.0 就定好了方向只是一直没做）
  - topbar 加 `✎` 按钮切换，快捷键 `Ctrl+E`；状态持久化 `edit_visible`
  - 底部加一个 Text 编辑面板，MONO 字体 + `code_bg` 底色（和渲染区视觉分层，不上 stipple 纹理）
  - 编辑面板和正文之间一条 5 px `sb_v_double_arrow` 分隔条，可拖拽调整高度，120–900 px 之间，`edit_height` 持久化
  - **实时双向同步**：编辑区改动 → 250 ms 防抖 → 重新 parse + 渲染正文 + TOC。正文成为 edit buffer 的只读镜像
  - **Ctrl+S 写盘**：`_save_edit_buffer` 把 buffer 写回当前 tab 的文件，bump tab.mtime 让 file watcher 忽略回声
  - **文件 watcher 智能退让**：编辑模式开着时，外部 mtime 变化不触发 `_render_active`，避免和 edit buffer 打架；关闭编辑模式或切换 tab 时恢复正常
  - 切换 tab / 关闭窗口前若 `edit_dirty` 自动 flush 到文件
  - `_render_active` 新增 `src_override` 参数，live 预览时走这条路径（不读文件、不更新 mtime）
  - `<<Modified>>` 回调用 `self._edit_sync_guard` 防止程序化 load（`_load_edit_buffer_from_active`）触发自己的 dirty 标记

### 文件变化

- `md-reader.pyw`: ~1380 行 → ~1630 行
- state schema 新增：`edit_visible: bool`、`edit_height: int`

## [0.4.3] - 2026-04-14

真的加上纹理 + 调 Kraft。

### 新增

- **纸面颗粒纹理**：用 Tk Text 的 `-bgstipple` 标签选项做逐像素两色抖动。启动时生成一张固定随机种子（seed=0xBEEF）的 32×32 1-bit XBM 位图（约 22% 密度），写到 `.md-reader-noise.xbm`。每个主题算一个 `speck = blend(bg, fg, 9%)` 作为"墨迹颗粒"色，定义一个最低优先级的 `paper` 标签（`background=speck, bgstipple=@noise.xbm`），在每次 `_render_active` / `_populate_toc` 完成后 `tag_add("paper", "1.0", "end") + tag_lower("paper")`。效果：正文和 TOC 的背景呈现两色噪点抖动而不是纯色；`code` / `codeblock` 因为有显式 bg 且优先级高，仍然正常覆盖 paper。零 PIL 依赖，零图片文件，纯 Tk 原生。
- **颜色混合工具**：模块级 `_blend_hex(c1, c2, alpha)`，纯 Python 不依赖任何库

### 改动

- **Kraft 重新配色**：用户反馈"太深太黄"。整体降饱和 + 提亮：
  - bg `#DFCBA0` → `#ECDFBE`
  - topbar `#D4BE8F` → `#E3D4AC`
  - code_bg `#CEB580` → `#DDCC98`
  - hr `#C9B384` → `#D7C594`
  - scroll `#A98F62` → `#B39B6A`
  - fg `#3E2C1B` → `#4B3B26`（稍提亮）
  - accent `#A64A2E` → `#9C4A2C`（微降饱和）

### 已知限制

- `bgstipple` 只能通过 Text tag 应用，tk Frame / Label 不支持 stipple，所以 topbar / tab bar / TOC 侧边栏的 Frame 背景依然是纯色。目前只有 Text 控件（正文渲染区和 TOC 列表）有真正的纹理。如果要所有区域都有纹理，需要把 Frame 换成 Canvas + `create_image` 铺 tile，那是 0.5.0 的工程量。

## [0.4.2] - 2026-04-14

纸质质感重设计 + TOC 侧边栏可拖拽 + 窗口圆角。

### 新增

- **窗口圆角**：用 Win32 `CreateRoundRectRgn` + `SetWindowRgn` 裁剪窗口为 18 px 半径圆角矩形。一次性的 Win32 调用，不需要 subclass 不需要 wndproc，和 `overrideredirect` 完美兼容。在窗口每次尺寸变化后（`_show_window / _resize_move / _resize_end / _toggle_max`）自动 re-apply —— region 是按绝对像素定义的，尺寸变了必须重画
- **TOC 侧边栏可拖拽宽度**：`toc_divider` 从 1 px → 5 px，加 `sb_h_double_arrow` cursor 和 `<Button-1>/<B1-Motion>/<ButtonRelease-1>` 绑定，拖动时 `toc_pane.configure(width=...)`，范围 140–600 px
- **TOC 宽度持久化**：`toc_width` 加入 state.json，下次启动恢复

### 改动

- **配色主题彻底重设计**：五个主题全部按"纸 + 墨"的物理质感重新选色。核心原则：不用纯白背景、不用纯黑文字、accent 用褪色 ink 而非荧光色。主题名也改了：
  - ~~Light~~ → **Parchment**（羊皮纸）：暖奶油 `#F3EBD6` + 深褐墨 `#3C3328` + 朱砂 accent `#8B3A2F`
  - ~~Sepia~~ → **Kraft**（牛皮纸 / 档案袋）：`#DFCBA0` + `#3E2C1B` + `#A64A2E`
  - ~~Morandi~~ → **Rice**（米纸 / 和纸）：`#EEE6D0` + `#45423A` + 鼠尾草 `#6E7A5A`
  - ~~Nord~~ → **Linen**（亚麻布 / 蓝图纸）：冷调米白 `#E2E0D5` + 普鲁士蓝墨 `#3B5A78`
  - ~~Dark~~ → **Ink**（炭笔素描本）：近黑 `#22201E` + 暖米白墨 `#E6DFD0` + 黄铜 accent `#D4A757`
- **主题名迁移**：加 `_LEGACY_THEME` 映射表，老 state.json 的 Light/Sepia/Morandi/Nord/Dark 自动转到新名字，老用户升级无感
- **默认主题**：从 Light 变成 Parchment

### 文件变化

- `md-reader.pyw`: ~1290 行 → ~1370 行
- state schema 新增：`toc_width: int`

## [0.4.1] - 2026-04-13

一次失败的架构探险和及时回退。核心经验：**为一个增量能力承担整个架构风险是坏交易**。

### 背景：0.4.0 之后用户问"为什么不支持 Win11 磁吸"
0.3.0 起就用 `overrideredirect(True)` 做 frameless，代价是 Windows 不把这个窗口当真窗口，丢失所有 DWM 窗口管理（贴边、Win+方向键 snap、snap layouts 4 宫格预览）。用户希望加回 Win11 原生 snap。

### B 路尝试（失败）：保 frameless 美观 + 做成真窗口
思路是用 Win32 自定义标题栏：保留 `WS_THICKFRAME` 让 Windows 认可为可 snap 的真窗口，同时用 `WM_NCCALCSIZE` 把客户区延伸到整个窗口做 frameless，用 `WM_NCHITTEST` 自定义标题栏/按钮/边沿命中区。

连续五轮迭代都炸：

1. **第一轮**：`SetWindowLongPtrW(GWLP_WNDPROC)` 老式子类化 + 自接管 NCCALCSIZE/NCHITTEST/NCLBUTTONUP(HTMAXBUTTON) → 点最大化按钮闪退
2. **第二轮**：换成 comctl32 `SetWindowSubclass`（现代 API，DefSubclassProc 走订阅链）→ 第一次最大化成功，点还原闪退
3. **第三轮**：加 `faulthandler.enable()`、自接管 NCLBUTTONDOWN/UP(HTMAXBUTTON) → 依然卡退
4. **第四轮**：彻底删 HTMAXBUTTON 路径，让 max 按钮变成普通 Tk Label 走 Button-1 → `_toggle_max` → `ShowWindow`；扩拖拽区到 topbar+tab bar → 双击顶部 max 之后还是卡退
5. **第五轮**：WM_NCCALCSIZE 永不改 rgrc、拦截 WM_SYSCOMMAND+SC_MOVE+zoomed 改成 SW_RESTORE、拦截 WM_NCLBUTTONDBLCLK+HTCAPTION → 还是卡退，faulthandler 零栈

查日志反推出用户真实路径：双击顶部 → 最大化 OK → 在全屏态下 mouse 横扫 topbar 试图 drag-to-restore → 卡退。DefWindowProc 对"maximized 状态下 HTCAPTION 点击拖拽"的默认处理会走到某个和自定义 chrome 打架的内部状态机，未能根治。

### 回退到 A 路：参考 `sticky-card` 的 `overrideredirect`
去看同目录参考项目 `2026-04-07-桌面置顶卡片-desktop-sticky-card/sticky-card.pyw`（被验证过几个月稳定）：零 Win32 子类化、零 NCHITTEST、零 NCCALCSIZE、零 DWM 交互，朴素的 `overrideredirect(True)` + Tk 级别 `<Button-1>/<B1-Motion>` 手动 drag，`<Motion>` 边沿检测 + 手动 resize。

**决策：彻底放弃 B，回退 A**。付了 frameless 的全部工程成本但 Win11 snap 一次都没真的用上（每次都卡退），换回窗口稳定是正经交易。

### 改动
- `__init__` 加 `self.root.overrideredirect(True)`
- **删除**（约 200 行）：`_setup_custom_chrome / _wndproc / _hit_test / _button_hit / _tab_hit / _get_topbar_height / _get_drag_area_height / _on_max_state_changed / _diag / _heartbeat`
- **激活**之前写好但被架空的 `_drag_start / _drag_move / _resize_cursor / _resize_start / _resize_move / _resize_end` — 这些方法从 0.3.0 就在，第四轮架构换路时留了后路，现在正好走那条后路
- `_build_ui` 末尾给 `topbar / topbar_inner / tab_holder` 三个 widget 绑 `<Button-1> → _drag_start`、`<B1-Motion> → _drag_move`、`<Double-Button-1> → _toggle_max`
- `root` 绑 `<Motion>/<Button-1>/<B1-Motion>/<ButtonRelease-1>` 激活 resize 路径
- `_toggle_max` 走纯 Tk 路径：记 `normal_geo` → `root.geometry(work_area)` 切换，不再调 `ShowWindow`
- `_show_window` 去掉 `ShowWindow(SW_MAXIMIZE)` 分支，纯 `deiconify + lift + focus_force`
- 窗口风格位从自定义 `WS_THICKFRAME + WS_SYSMENU + WS_MINIMIZEBOX + WS_MAXIMIZEBOX` 变成 `WS_POPUP + WS_VISIBLE + WS_CLIPSIBLINGS + WS_CLIPCHILDREN`（即 overrideredirect 默认）

### 修复
- **字号连击卡顿**：`_bump_font` 改成 180ms 防抖。之前每次点 A+ 都全量销毁重建 UI + 重 parse markdown，连击直接堆栈。现在先即时刷数字标签做反馈，180ms 内的连击合并成一次 rebuild

### 取舍
- ✗ **丢失**：Win11 拖到屏幕边贴边 snap、Win+方向键 snap、snap layouts 4 宫格预览
- ✓ **保留**：F11 / ❐ 按钮 / 双击顶部 三种方式最大化、Aero Snap Win11 快捷键（Win+←/→ 仍可手动实现，当前版本未加）、字号 / 主题 / tab / TOC / 所有内容渲染
- ✓ **稳定**：窗口再不会卡退

### 文件变化
- `md-reader.pyw`: ~780 行 → ~1290 行（含 B 路探险残留的 ctypes 常量和 `_bind_native` 绑定；这些现在是惰性导入，不会被调用，留着以备后续扩展）

## [0.4.0] - 2026-04-13

0.3.0 之后同一天的多轮迭代，统一发版。

### 新增

- **多标签单窗口**：再次用 `md-reader.cmd` 打开新文件不再起新窗口，而是作为新标签加入现有窗口
  - 用 `msvcrt.locking` 在 `.md-reader.lock` 上拿独占锁判定单实例
  - 新进程把目标路径写到 `.md-reader-pending-<pid>-<ts>.txt`（每个二级实例唯一文件名，避免和主进程读写竞争），主进程每 350ms 轮询消费
  - 标签栏：active 标签顶部 2px accent 色横条 + 加粗 + bg 背景；inactive 灰色 + topbar 背景
  - 每个标签独立保存滚动位置和 mtime
  - 已经打开过的文件再次打开会切到对应标签，不重复
  - 关掉最后一个标签 = 关窗口
- **TOC 侧边栏**（左侧 220px）：解析当前文档 h1-h3，点击跳转到对应位置；h1 加粗、h2 缩进、h3 更小更淡；topbar 上 `☰` 按钮切换显示/隐藏，状态持久化
- **文件 watcher**：每 900ms 检查活跃标签的 mtime，外部修改自动重新渲染并保留滚动位置；非活跃标签在切换时也会重读文件
- **自定义主题目录**：启动时扫描 `themes/*.json`，文件名作为主题名，required-key 校验后合并到 `THEMES`，自动出现在主题循环里
- **GFM 表格渲染**：用 `text.window_create` 嵌入 grid Frame；表头加粗 + topbar 底色，奇偶行交替 bg/code_bg，外层 hr 色 + 1px gap 模拟边框；解析分隔行 `:---` `:---:` `---:` 三种对齐
- **最大化 / 还原**：topbar 右上 `□` / `❐` 按钮 + `F11` 快捷键；用 ctypes `SystemParametersInfoW(SPI_GETWORKAREA)` 拿到任务栏排除后的工作区，setgeometry 模拟最大化（`overrideredirect(True)` 下系统 zoomed 不可靠）；最大化时拖拽和边缘缩放自动禁用；状态持久化，下次启动恢复
- **字号 slider**：原 S/M/L/XL 档位改成连续整数 8-28，topbar 中部 `A−  N  A+` 按钮，N 是当前 body pt 值；字号上滚轮可调；快捷键 `Ctrl+=` 增大、`Ctrl+-` 减小；其它字号（h1/h2/h3/h4/code/top）由 body 用比例派生

### 改动

- **默认窗口尺寸**：~~A4 纵向 820×1100~~ → 工作区宽 ÷ 2 × 全高，靠右贴边（半屏分屏姿态），适配笔记本和外接屏
- **TOC 字体**：从 `Segoe UI` 换成 `Microsoft YaHei`。原因：Segoe UI 没有中文字形，bold 变体回退到 YaHei、regular 回退到 SimSun，同一面板里出现"黑体 + 宋体"两种字体；显式指定 YaHei 后中英文一致
- **标签栏文件名字体**：同上，`Segoe UI` → `Microsoft YaHei`，避免中文文件名出现回退混排
- **TOC 字号**：减小一档（M 时 h1=10/h2=9/h3=8 → 与 body slider 联动派生）
- **状态文件 schema**：
  - `font_size` 从字符串（`"M"`）改成整数（`13`），加 `_LEGACY_FONT` 表向后兼容老 state
  - 新增 `maximized: bool`
  - 新增 `toc_visible: bool`
  - 最大化时 `width/height/x/y` 仍存"正常态几何"（self.normal_geo），`maximized` 字段单独标记

### 移除

- `FONT_SIZES` 字典 + `FONT_SIZE_NAMES`（被 `derive_font_sizes(body)` 函数和 `MIN_FONT/MAX_FONT/DEFAULT_FONT` 常量替代）
- 单一 `_next_font_size` 循环切换方法（被 `_bump_font(delta)` 替代）
- topbar 上的固定文件名标签（被标签栏取代，topbar 只剩窗口 chrome）

### 修复

- 字号 slider 重构后状态文件兼容：老 state 里 `font_size: "M"` 通过 `_LEGACY_FONT = {"S":11,"M":13,"L":15,"XL":17}` 映射成整数，避免重启后崩溃

### 文件变化

- `md-reader.pyw`：~430 行 → ~780 行
- 新增运行时文件（自动生成）：`.md-reader.lock`、`.md-reader-pending-*.txt`
- 新增可选目录：`themes/`（用户自定义主题）

### 快捷键速查（合并最新）

| 键位 | 行为 |
|---|---|
| `Esc` | 关闭窗口 |
| `Ctrl+W` | 关闭当前标签（最后一个 = 关窗口） |
| `F5` / `Ctrl+R` | 重新加载当前标签 |
| `F11` | 最大化 / 还原 |
| `Ctrl+Tab` / `Ctrl+PgDn` | 下一个标签 |
| `Ctrl+Shift+Tab` / `Ctrl+PgUp` | 上一个标签 |
| `Ctrl+=` / `Ctrl++` | 字号增大 |
| `Ctrl+-` | 字号减小 |

## [0.3.0] - 2026-04-13

### 改动

- **彻底替换渲染层**：从 mshta + HTA + Markdig 换成纯 Python tkinter 自绘窗口。原方案虽然不是浏览器但 mshta 弹出的就是个普通系统对话框，外观仍然不够独立优雅
- **frameless 窗口 + 自定义 topbar**：参考同目录上层 `2026-04-07-桌面置顶卡片-desktop-sticky-card` 的视觉语言。`overrideredirect(True)` 去掉系统标题栏，自绘 1px 边框 + Topbar（左侧文件名、右侧主题/字号/刷新/关闭），整体呈现"独立桌面小程序"而非"弹窗"
- **5 个主题**：Light、Sepia、Morandi、Nord、Dark，点 Topbar 主题名循环切换
- **4 档字号**：S/M/L/XL，点 Topbar 字号字母循环切换
- **状态持久化**：窗口大小、位置、主题、字号写入 `.md-reader-state.json`，下次自动恢复
- **可拖拽可缩放**：从 Topbar 拖动移动窗口；右、下、右下、左下边缘可拉伸
- **滚动 + 选中 + 复制**：内容走 `tk.Text` 而非 HTML，支持鼠标滚轮、键盘 PgUp/Dn、文字选中复制
- **快捷键**：`Esc` / `Ctrl+W` 关闭，`F5` / `Ctrl+R` 重新加载文件，点击 Topbar 文件名复制完整路径
- **零外部依赖**：仅 Python 3 标准库（tkinter），不再需要 Markdig.dll / nuget 下载，完全离线
- **Markdown 解析**：内置简易解析器，支持标题(h1-h4)、段落、加粗、斜体、行内代码、删除线、链接、有序/无序/任务列表、引用、围栏代码块、分隔线

### 移除

- `Markdig.dll`（不再需要 .NET 库）
- HTA 临时文件生成逻辑
- 对 nuget.org 的运行时下载依赖

### 文件变化

- 新增：`md-reader.pyw`（主程序，~430 行 tkinter）
- 重写：`md-reader.cmd`（薄启动器，仅一行 `start "" pythonw "%~dp0md-reader.pyw" "%~f1"`）
- 新增：`.md-reader-state.json`（运行时状态文件，自动生成）

### 依赖变化

- **新增**：Python 3.x（系统已装 Python 3.12，pythonw 可用）
- **移除**：mshta.exe、Markdig.dll、网络（首次运行）

## [0.2.0] - 2026-04-13

### 改动

- **渲染器从浏览器换成 mshta**：原本生成 HTML 后用默认浏览器打开，现改为生成 HTA 文件由 Windows 内置的 `mshta.exe` 打开，呈现为独立的原生窗口（无地址栏/标签/菜单），不再像浏览器
- **合并为单文件**：原来的 `open-md.cmd` + `open-md.ps1` 两个文件合并为一个 `md-reader.cmd`（cmd + PowerShell 多语言文件），解决了 Windows "打开方式"对话框只显示 .cmd 而看不到 .ps1 导致用户困惑的问题
- **改为本地渲染**：不再依赖 jsdelivr CDN（marked.js + github-markdown-css + highlight.js），改用 .NET Markdig 库做服务端渲染。首次运行从 nuget.org 自动下载 `Markdig.dll`（约 600 KB）缓存到项目目录，之后完全离线可用
- **样式内嵌**：GitHub 风格 CSS 直接写在 .cmd 里随 HTA 一起输出，无外部样式表

### 新增

- `README.md`：项目说明、安装、使用、故障排查
- `CHANGELOG.md`：本文件

### 修复

- **iex 解析问题**：把 PS 部分通过 `iex` 直接执行时，`&` `<` 等字符在命令模式下被误判为操作符。改为先把 PS 代码提取到 `%TEMP%\md-reader-engine.ps1` 再用 `-File` 执行，脚本上下文解析正常
- **标记定位问题**：用 `IndexOf('#--PSBEGIN--')` 定位脚本起点时，cmd 命令行里出现的字面量也会被匹到，导致截取位置错误。改用 `LastIndexOf` 取最后一处出现位置
- **Markdig 依赖缺失**：Markdig 0.37.0 依赖 `System.Memory.dll`，PS 5.1 / .NET Framework 4.x 默认不带，加载时抛 `ReflectionTypeLoadException`。降级到 Markdig 0.18.3，net452 构建零依赖

### 移除

- `open-md.cmd`、`open-md.ps1`：被 `md-reader.cmd` 取代

## [0.1.0] - 2026-04-13

首个版本。

### 新增

- `open-md.ps1`：PowerShell 渲染脚本，读取 .md 文件 → base64 编码 → 嵌入 HTML 模板（marked.js + github-markdown-css + highlight.js，CDN 加载）→ 写到 `%TEMP%` → 用默认浏览器打开
- `open-md.cmd`：薄封装启动器，用于"打开方式"关联
- `test-sample.md`:测试文档，覆盖文本样式、嵌套列表、任务列表、4 种语言代码块、表格、图片、多级引用、中英混排

### 已知问题

- 用浏览器打开，不是原生窗口
- 需要联网（依赖 jsdelivr CDN）
- "打开方式"对话框里 .ps1 不显示，用户只能选 .cmd，容易误以为 .ps1 不可用
