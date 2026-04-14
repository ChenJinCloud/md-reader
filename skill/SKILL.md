---
name: md-reader
description: >-
  Open a Markdown file in MD Reader — a lightweight frameless desktop
  Markdown reader for Windows with paper-textured themes and optional
  English-to-Chinese translation / bilingual view. Use this skill when
  the user asks to view, open, render, preview, or "look at" a .md file
  in a dedicated reader window — e.g. "打开你编辑的那份 md",
  "用阅读器看一下", "渲染一下这份 md", "让我看看你刚写的方案",
  "show me that md", "open it in the reader", "render that markdown".
  ALSO use this skill for bilingual / translation intent on English md
  files — "中英对照打开", "对照看一下", "双语打开", "英中对照",
  "open bilingually", "show me side by side in Chinese" → pass
  `--trans bi`. "翻译成中文打开", "用中文看", "translate to Chinese"
  → pass `--trans zh`. Do NOT use this skill when the user wants the
  file's content inlined into the conversation (use the Read tool) or
  wants to modify the file (use Edit / Write). Windows only.
metadata:
  requires:
    bins: []
  platform: Windows
  repo: https://github.com/ChenJinCloud/md-reader
---

<!--
  NOTE TO USERS COPYING THIS SKILL:
  The absolute path below points at the author's local clone. After you
  `git clone` this repo, replace every occurrence of
    D:\ClaudeCodeWorkspace\2026-04-05-AI编程学习-learning-ai-coding\2026-04-13-markdown阅读器-md-reader
  with your own clone path, then copy this file to
    ~/.claude/skills/md-reader/SKILL.md
  The skill calls the PyInstaller-built exe at <clone>\dist\md-reader.exe
  which is shipped in the repo — no Python required.
-->

# MD Reader

Opens a Markdown file in a dedicated desktop reader window via the
project at `D:\ClaudeCodeWorkspace\2026-04-05-AI编程学习-learning-ai-coding\2026-04-13-markdown阅读器-md-reader\`.
MD Reader is a Python tkinter frameless app — paper themes, rounded
corners, multi-tab, split-screen editor — shipped as a PyInstaller
single-file exe at `dist\md-reader.exe`.

## When to trigger

On any user intent that means "I want to VIEW this markdown in a
dedicated window, not in the chat":

- `打开你刚才编辑/修改/生成的 md 文档`
- `用阅读器打开` / `用 reader 看一下` / `用 md reader 打开`
- `让我看看那份方案/周报/报告` (when the output is a .md file)
- `渲染一下这个 md` / `预览这份 markdown`
- `show me the md` / `open in the reader` / `render this markdown file`
- `我想看这份文档` (context: a .md file)

Also on bilingual / translation intent for English `.md` files — route
these to the same skill with a `--trans` flag:

- `中英对照打开` / `双语打开` / `对照看一下` / `英中对照` / `bilingual` /
  `side by side` → add `--trans bi`
- `翻译成中文打开` / `用中文看这份 md` / `translate this md to Chinese` /
  `render in Chinese` → add `--trans zh`

Do NOT trigger when:

- User asks a question about the file's content → use Read and answer
  in the chat
- User wants to modify the file → use Edit / Write
- User wants the raw content displayed in the conversation → use Read
- The file isn't a .md / .markdown
- User wants the translated text pasted into the chat → use Read + do
  the translation in-conversation (this skill only renders in a window)

## How to invoke

One shell command. Always pass an **absolute path**. Resolve relative
paths to absolute before invoking.

Plain reading (default):

```bash
"D:\ClaudeCodeWorkspace\2026-04-05-AI编程学习-learning-ai-coding\2026-04-13-markdown阅读器-md-reader\dist\md-reader.exe" "<absolute-path-to-md-file>"
```

Bilingual (English + Chinese interleaved per paragraph):

```bash
"D:\ClaudeCodeWorkspace\2026-04-05-AI编程学习-learning-ai-coding\2026-04-13-markdown阅读器-md-reader\dist\md-reader.exe" --trans bi "<absolute-path-to-md-file>"
```

Pure Chinese:

```bash
"D:\ClaudeCodeWorkspace\2026-04-05-AI编程学习-learning-ai-coding\2026-04-13-markdown阅读器-md-reader\dist\md-reader.exe" --trans zh "<absolute-path-to-md-file>"
```

`--trans` goes **before** the path. The flag is forwarded to the running
master instance via the `.md-reader-pending-*.txt` IPC file, so it works
whether or not MD Reader is already open. First-time translation of a
given paragraph takes a few seconds (Google gtx via local proxy); after
that everything is cached in `%LOCALAPPDATA%\md-reader\translate-cache.json`
and opens instantly.

Behavior guarantees:

1. **Single instance with auto-tabbing.** If MD Reader is already
   running, this command hands the new file path off to the existing
   window via `.md-reader.lock` + `.md-reader-pending-*.txt` IPC, and
   the file opens as a new tab in that window. You do NOT need to check
   whether a window is already open — just run the command.
2. **Fire-and-forget.** The exe is a `--windowed` PyInstaller build, so
   it spawns detached from the terminal and the command returns
   immediately. Don't wait for it and don't tail its output.
3. **No return value worth reading.** If the command exits 0, you're
   done. The user's window appeared on their desktop.

## Default file selection

- If you just edited or created one `.md` file in this conversation →
  open that one without asking.
- If you edited multiple → pick the most recently edited.
- If no `.md` is in the conversation context → ask "which file?".

## What you DON'T need to do

- Don't check if Python is installed — the exe is self-contained and
  needs no runtime.
- Don't check if MD Reader is "installed" — it runs directly from the
  exe path, no install step.
- Don't print the file's content to the user after opening — they're
  going to read it in the reader window.

## One-line examples

User: "打开你刚写的 2026-04-14-周报-weekly.md"

You:

```bash
"D:\ClaudeCodeWorkspace\2026-04-05-AI编程学习-learning-ai-coding\2026-04-13-markdown阅读器-md-reader\dist\md-reader.exe" "D:\ClaudeCodeWorkspace\2026-04-14-周报-weekly.md"
```

Then reply: "已用 MD Reader 打开。"

---

User: "中英对照打开这份英文 spec.md"

You (after resolving to absolute path):

```bash
"D:\ClaudeCodeWorkspace\2026-04-05-AI编程学习-learning-ai-coding\2026-04-13-markdown阅读器-md-reader\dist\md-reader.exe" --trans bi "D:\work\spec.md"
```

Then reply: "已用 MD Reader 以中英对照打开。首次翻译需几秒，之后会走本地缓存秒开。"

---

User: "把这份英文 readme 翻译成中文给我看"

If they want to READ it themselves in a window → use `--trans zh`. If
they want the translation inlined in chat → this skill is wrong, use
Read + answer in chat.

```bash
"D:\ClaudeCodeWorkspace\2026-04-05-AI编程学习-learning-ai-coding\2026-04-13-markdown阅读器-md-reader\dist\md-reader.exe" --trans zh "D:\work\README.md"
```

Don't Read the file, don't summarize it, don't paste its content —
the user is reading it themselves in the window.
