# AGENTS.md

Instructions for AI coding agents (Codex CLI, Cursor, Aider, Continue,
Jules, and any agent that reads an `AGENTS.md` at the repo root).
Claude Code has a separate skill file at `skill/SKILL.md` that encodes
the same rules in its own format — if you are Claude Code, prefer that.

## What this repo is

MD Reader — a lightweight frameless desktop Markdown reader for
Windows. Not a library, not a package. It's a single PE executable
shipped in this repo at `dist/md-reader.exe` (PyInstaller, ~11 MB, no
Python runtime required on the target machine).

## When to invoke the reader

Use the `dist/md-reader.exe` tool **whenever the user's intent is "I
want to VIEW this markdown in a dedicated window, not in chat"**. The
reader window is the deliverable; do NOT also paste the file's content
into the conversation.

Trigger phrases (Chinese + English, non-exhaustive):

- 打开 / 用阅读器打开 / 渲染一下 / 预览 / 让我看看 / 我想看这份
- open in the reader / render this markdown / show me the md / preview

For English `.md` files, two extra intents map to the `--trans` flag:

- **Bilingual / side-by-side**: 中英对照 / 双语打开 / 对照看一下 /
  bilingual / side by side → `--trans bi`
- **Pure Chinese**: 翻译成中文打开 / 用中文看 / translate to Chinese /
  render in Chinese → `--trans zh`

Do NOT invoke the reader when:

- The user asks a question about the file's content — answer in chat
  from the file directly.
- The user wants to modify the file — edit the file, don't open it.
- The user wants the raw content inlined in chat — print it yourself.
- The file isn't a `.md` / `.markdown`.
- The user wants the translation pasted into chat (not rendered in a
  window) — do the translation yourself in-conversation.

## How to invoke

Always use an **absolute path** to both the exe and the target file.

### Plain reading

```bash
"<repo-root>/dist/md-reader.exe" "<absolute-path-to-file.md>"
```

### Bilingual (English + Chinese, interleaved per paragraph)

```bash
"<repo-root>/dist/md-reader.exe" --trans bi "<absolute-path-to-file.md>"
```

### Pure Chinese

```bash
"<repo-root>/dist/md-reader.exe" --trans zh "<absolute-path-to-file.md>"
```

`--trans` must come **before** the path. The flag is forwarded through
the single-instance IPC handoff, so it works whether or not MD Reader
is already running.

`<repo-root>` is wherever the user cloned this repo. On the author's
machine it's
`D:\ClaudeCodeWorkspace\2026-04-05-AI编程学习-learning-ai-coding\2026-04-13-markdown阅读器-md-reader`
— for another user, resolve it relative to this `AGENTS.md` file (or
ask the user once and remember).

## Behavior guarantees

1. **Fire and forget.** The exe is a `--windowed` PyInstaller build
   that spawns detached from the terminal and returns immediately.
   Don't wait for it, don't tail output, don't check exit code beyond
   "did it start".
2. **Single instance with auto-tabbing.** If MD Reader is already
   running, a second invocation hands the new file path (and optional
   `--trans` mode) off to the existing window via
   `.md-reader.lock` + `.md-reader-pending-*.txt` IPC, and the file
   opens as a new tab in that window. You do not need to detect
   whether a window is already open.
3. **No meaningful return value.** Exit code 0 = the user's window
   appeared (or will appear within ~100 ms). That's all you get.

## First-time translation latency

When you pass `--trans bi` or `--trans zh` for a file whose paragraphs
haven't been translated before, the reader takes a few seconds (one
HTTP round-trip per paragraph to Google Translate's gtx endpoint,
through the user's local proxy at `127.0.0.1:7897` by default — see
`MD_READER_PROXY` env var to override). After that, every paragraph
lives in `%LOCALAPPDATA%\md-reader\translate-cache.json` keyed by sha1
and reopens instantly.

Tell the user once: "首次翻译需几秒，之后走本地缓存秒开。" / "First
translation takes a few seconds; after that it's cached locally and
opens instantly." Then drop it — don't narrate further.

## Requirements

- Windows 10 / 11.
- For `--trans` modes: a local HTTP proxy reachable at
  `http://127.0.0.1:7897` that can reach `translate.googleapis.com`.
  Override with `MD_READER_PROXY`. Without a working proxy,
  translation requests fail and the reader falls back to the original
  text (the translate button spins `…` then returns to `原`).

## Default file selection

- If you just edited or created one `.md` file in this conversation,
  open that one without asking.
- If you edited multiple, pick the most recently edited.
- If no `.md` is in the conversation context, ask "which file?".

## What you DON'T need to do

- Don't check whether Python is installed — the exe is self-contained.
- Don't check whether MD Reader is "installed" as a default handler —
  you're invoking the exe directly, not going through the `.md`
  association.
- Don't print the file's content after opening — the user is reading
  it in the window.
- Don't summarize the file unless the user explicitly asks.

## Canonical examples

**User**: "打开你刚写的 2026-04-14-周报-weekly.md"

**You**:

```bash
"<repo-root>/dist/md-reader.exe" "D:\ClaudeCodeWorkspace\2026-04-14-周报-weekly.md"
```

Then: "已用 MD Reader 打开。"

---

**User**: "中英对照打开这份英文 spec.md"

**You**:

```bash
"<repo-root>/dist/md-reader.exe" --trans bi "D:\work\spec.md"
```

Then: "已用 MD Reader 以中英对照打开。首次翻译需几秒，之后走本地缓存秒开。"

---

**User**: "translate this README to Chinese and show it to me"

Ambiguous — window or chat? If the user wants to *read* it themselves,
use `--trans zh`. If they want the Chinese text pasted into the
conversation (e.g., to copy into something else), this tool is wrong;
translate it yourself in-chat.
