**English** · **[简体中文](README.zh-CN.md)**

# MD Reader

![Banner](banner.jpg)

> A minimal desktop Markdown reader for Windows — built to read the
> `.md` files your AI coding agents keep generating, without opening
> Obsidian, a browser, or an entire IDE. Single-file, zero runtime
> dependencies, ships with a Claude Code skill and an `AGENTS.md` for
> Codex / Cursor / Aider / anyone else.

⭐ **Install the skill and Claude Code pushes the rendered window to
you the instant it finishes writing.** No copy-path, no `cd`, no
double-click — the window is already on your desktop by the time you
look up.

⭐ **Everything search → enter → a single sheet of paper.** No vault,
no IDE, no plugin. One `.md`, one window.

That's the whole product.

## Why this exists

Markdown is the heaviest file format in my daily work. Specs, weekly
reports, stray notes, whatever an agent dumps on me — all `.md`,
scattered across the disk. But "how do I actually view one" was
always awkward:

- **Notepad** doesn't render Markdown. You see `# * >` and give up.
- **Browsers** make it feel like a web page, not a document — the
  URL bar, the tab strip, the extension icons all fight for your
  attention.
- **Obsidian** looks great but insists you open a whole vault first.
  Sometimes it just spins. I wanted to read *one* file — why am I
  loading a knowledge base?
- **IDEs** (Cursor / VSCode / Qoder) render Markdown fine, but
  they're dev tools. Starting a full IDE just to read a file is
  absurd in RAM, startup time, and visual noise.

And the Claude Code case is the most painful one: CC finishes writing
a document, the cursor just sits there waiting, and now *I* have to
switch out, find the file, double-click, wait for the window. Between
the agent's speed and my speed, there are several manual steps —
that's exactly what this tool erases.

MD Reader is a tiny desktop Markdown reader built for two motions:
**Everything → enter → paper** and **Claude Code writes → window
opens → you read**. Frameless rounded window, paper-textured themes,
serif body, draggable TOC, multi-tab, split-screen editor. Fast to
launch, visually quiet — more like a desktop mini-app than a document
viewer. Need to tweak something? `Ctrl+E` pops a split editor that
auto-saves back to the file. When another process (Claude Code,
another editor) edits the same file, the reader window picks up the
change without you having to close and reopen.

## Features

- **Paper-textured themes** — Parchment / Medium / Rice / Linen / Ink
  — five themes colored "paper + ink", never pure white on pure black
- **Real paper grain** — `-bgstipple` pixel-dithered noise (a 32×32
  seeded XBM generated at startup) on the body and TOC, not a flat
  background
- **Rounded frameless window** — 18 px radius via Win32
  `CreateRoundRectRgn` + `SetWindowRgn`, one-shot and side-effect-free
- **Self-drawn chrome** — no OS title bar; custom topbar with all
  controls in one row
- **Multi-tab, single instance** — re-invoking `md-reader.exe` on a
  new file opens a new tab in the existing window via `msvcrt`
  instance lock + file-based IPC (no sockets)
- **Draggable TOC sidebar** — parses h1–h3, click to jump, width
  drag-resizable (140–600 px), persisted
- **Split-screen edit mode** — `Ctrl+E` opens a bottom editor pane
  with 250 ms debounced live re-render, 900 ms debounced autosave,
  `Ctrl+S` for immediate save
- **Bidirectional sync with external editors** — when another tool
  edits the same file, the reader pulls the change into both the
  rendered body and the edit buffer (as long as your local edits
  aren't dirty)
- **File watcher** — active tab auto-reloads on external mtime
  change, scroll position preserved
- **Continuous font-size control** — 8–28 pt, `A− N A+` buttons,
  `Ctrl+=` / `Ctrl+-`, or scroll on the size number
- **English → Chinese bilingual reading** — toolbar `原/双/中`
  cycles source → bilingual → Chinese, also `Ctrl+T` or the
  `--trans bi|zh` CLI flag at launch time. No API key required
  (Google gtx public endpoint through a local proxy, default
  `http://127.0.0.1:7897`, overridable via `MD_READER_PROXY`).
  Paragraph-level caching to `%LOCALAPPDATA%\md-reader\translate-cache.json`
  — the same English paragraph is translated at most once, ever
- **Clickable links** — `[text](url)` inline links open in the
  default browser on click, hand cursor on hover
- **GFM support** — headings, paragraphs, bold/italic/strike/inline
  code, ordered/unordered/task lists, blockquotes, fenced code
  blocks, links, tables, horizontal rules
- **Theme directory** — drop `themes/*.json` files; they merge with
  the built-ins at startup
- **State persistence** — window geometry, theme, font size, TOC
  width, edit panel height, maximized state all saved and restored
- **Zero runtime dependencies** — ships a PyInstaller
  `dist/md-reader.exe` (~11 MB); clone and run, no Python needed.
  Source uses only stdlib (`tkinter` / `ctypes` / `msvcrt`)
- **Per-monitor DPI awareness** — v1

## Quick start

```bash
# 1) One-time: register .md file association (HKCU, no admin needed)
double-click install.cmd

# 2) From then on, any .md file opens in a dedicated window
```

Or invoke the exe directly from the command line:

```cmd
dist\md-reader.exe "path\to\file.md"

rem Open directly into bilingual (English + Chinese) mode
dist\md-reader.exe --trans bi "path\to\english.md"

rem Open directly into pure Chinese translation mode
dist\md-reader.exe --trans zh "path\to\english.md"
```

From source (requires Python 3.8+ with `pythonw.exe` on PATH):

```cmd
md-reader.cmd "path\to\file.md"
rem or bypass the launcher
pythonw md-reader.pyw "path\to\file.md"
```

## Keyboard shortcuts

| Keys | Action |
|---|---|
| `Esc` | Close window |
| `Ctrl+W` | Close current tab (last tab → close window) |
| `F5` / `Ctrl+R` | Reload current tab |
| `F11` / double-click topbar / click `□` | Maximize / restore |
| `Ctrl+E` / click `✎` | Toggle split-screen edit mode |
| `Ctrl+T` / click `原` / `双` / `中` | Cycle translation mode: source → bilingual → Chinese |
| `Ctrl+S` | Save current file (edit mode) |
| `Ctrl+Tab` / `Ctrl+PgDn` | Next tab |
| `Ctrl+Shift+Tab` / `Ctrl+PgUp` | Previous tab |
| `Ctrl+=` / `Ctrl++` | Increase font size |
| `Ctrl+-` | Decrease font size |

## AI agent integration

Two rules files ship with the repo so different agents can invoke
the reader naturally:

| File | For | Role |
|---|---|---|
| `skill/SKILL.md` | **Claude Code** | Drop into `~/.claude/skills/md-reader/` — Claude Code auto-loads it and fires when the user says things like "open this md" or "bilingual open this spec" |
| `AGENTS.md` (repo root) | **Codex CLI / Cursor / Aider / Continue / Jules / any [agents.md](https://agents.md/)-compatible agent** | Auto-loaded from the repo root at agent startup. Same behavior in agent-agnostic language |

With either file installed, a user can say:

- "打开这份 md" / "open this md in the reader" → plain view
- "中英对照打开" / "show me this bilingually" → `--trans bi`
- "翻译成中文打开" / "open it in Chinese" → `--trans zh`

...and the agent routes to `dist\md-reader.exe` with the right flag.
No Python install required on the user's machine — everything runs
through the shipped `dist\md-reader.exe` binary.

**Setup note**: both `skill/SKILL.md` and `AGENTS.md` contain the
author's local clone path as a placeholder. After `git clone`, do a
find-and-replace to point them at your own clone root. Both files
have a header note explaining the occurrences.

## Requirements

- Windows 10 / 11
- For source mode only: Python 3.8+ (ships with tkinter on Windows)
- For `--trans` modes: a local HTTP proxy at `http://127.0.0.1:7897`
  (Clash / V2Ray default port) or `MD_READER_PROXY` pointing at
  whatever proxy can reach `translate.googleapis.com`. Without a
  working proxy, translation silently falls back to the source text.

No pip, no venv, no Node, no .NET.

## Known limits

- **No native Win11 snap** — dragging to screen edges doesn't trigger
  snap, `Win+Arrow` doesn't respond. This is the cost of
  `overrideredirect`, and five rounds of custom Win32 chrome in 0.4.1
  convinced me it's not worth fighting.
- **Texture is body-only** — topbar / tab bar / TOC frame backgrounds
  are flat color because Tk `Frame` doesn't support `-bgstipple`
- **Translation needs a proxy** outside China/regions where
  `translate.googleapis.com` is blocked
- **No LaTeX / Mermaid / PlantUML rendering**
- **Images are local-path only** — no remote fetch

## Troubleshooting

### Double-clicking .md doesn't work / "Always use this app" is grayed out

Run `install.cmd`. Windows 10/11 won't treat `.cmd` batch files as
real apps for default-handler purposes, and even some `pythonw.exe +
.pyw` setups get UserChoice-locked. `install.cmd` registers a ProgID
in `HKCU` pointing directly at `dist\md-reader.exe` (a real PE
executable), which Windows accepts and the "Always" checkbox enables.

### Window geometry is wrong / state file got corrupted

Delete `.md-reader-state.json` and restart.

### Reader window isn't picking up external file changes

Check if you're in split-edit mode with unsaved local changes
(`edit_dirty`). When that happens, the reader keeps your local
version instead of overwriting it — `Ctrl+S` to push your version to
disk, or close edit mode to accept the external version on next
reload.

## License

MIT. See [LICENSE](LICENSE).

## More

- [CHANGELOG.md](CHANGELOG.md) — version history
- [DISCUSSION.md](DISCUSSION.md) — project decision journal (Chinese,
  kept as a time-stamped record of design debates)
- [README.zh-CN.md](README.zh-CN.md) — 中文版 README (more detail,
  includes extended architecture notes and theme customization)

---

> If you also feel that *just to read one `.md`*, you shouldn't have
> to wake up Obsidian or a full IDE — this is for you. MD Reader
> isn't trying to be your second brain. It just wants to be a sheet
> of paper that renders Markdown nicely.
