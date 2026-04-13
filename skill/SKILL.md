---
name: md-reader
description: >-
  Open a Markdown file in MD Reader — a lightweight frameless desktop
  Markdown reader for Windows with paper-textured themes. Use this skill
  when the user asks to view, open, render, preview, or "look at" a .md
  file in a dedicated reader window — e.g. "打开你编辑的那份 md",
  "用阅读器看一下", "渲染一下这份 md", "让我看看你刚写的方案",
  "show me that md", "open it in the reader", "render that markdown".
  Do NOT use this skill when the user wants the file's content inlined
  into the conversation (use the Read tool) or wants to modify the file
  (use Edit / Write). Windows only.
metadata:
  requires:
    bins: ["pythonw.exe"]
  platform: Windows
  repo: https://github.com/ChenJinCloud/md-reader
---

# MD Reader

Opens a Markdown file in a dedicated desktop reader window via the
project at `D:\ClaudeCodeWorkspace\2026-04-13-markdown阅读器-md-reader\`.
MD Reader is a Python tkinter frameless app — paper themes, rounded
corners, multi-tab, split-screen editor.

## When to trigger

On any user intent that means "I want to VIEW this markdown in a
dedicated window, not in the chat":

- `打开你刚才编辑/修改/生成的 md 文档`
- `用阅读器打开` / `用 reader 看一下` / `用 md reader 打开`
- `让我看看那份方案/周报/报告` (when the output is a .md file)
- `渲染一下这个 md` / `预览这份 markdown`
- `show me the md` / `open in the reader` / `render this markdown file`
- `我想看这份文档` (context: a .md file)

Do NOT trigger when:

- User asks a question about the file's content → use Read and answer
  in the chat
- User wants to modify the file → use Edit / Write
- User wants the raw content displayed in the conversation → use Read
- The file isn't a .md / .markdown

## How to invoke

One shell command. Always pass an **absolute path**. Resolve relative
paths to absolute before invoking.

```bash
D:\ClaudeCodeWorkspace\2026-04-13-markdown阅读器-md-reader\md-reader.cmd "<absolute-path-to-md-file>"
```

Behavior guarantees:

1. **Single instance with auto-tabbing.** If MD Reader is already
   running, this command hands the new file path off to the existing
   window via `.md-reader.lock` + `.md-reader-pending-*.txt` IPC, and
   the file opens as a new tab in that window. You do NOT need to check
   whether a window is already open — just run the command.
2. **Fire-and-forget.** The launcher uses `start ""` to spawn
   `pythonw.exe` detached. The command returns immediately. Don't wait
   for it and don't tail its output.
3. **No return value worth reading.** If the command exits 0, you're
   done. The user's window appeared on their desktop.

## Default file selection

- If you just edited or created one `.md` file in this conversation →
  open that one without asking.
- If you edited multiple → pick the most recently edited.
- If no `.md` is in the conversation context → ask "which file?".

## What you DON'T need to do

- Don't check if `pythonw.exe` exists — the `.cmd` launcher handles
  errors and the user is on Windows.
- Don't check if MD Reader is "installed" — it runs directly from the
  script path, no install step.
- Don't print the file's content to the user after opening — they're
  going to read it in the reader window.

## One-line example

User: "打开你刚写的 2026-04-14-周报-weekly.md"

You:

```bash
D:\ClaudeCodeWorkspace\2026-04-13-markdown阅读器-md-reader\md-reader.cmd "D:\ClaudeCodeWorkspace\2026-04-14-周报-weekly.md"
```

Then reply in one short sentence: "已用 MD Reader 打开。"

Don't Read the file, don't summarize it, don't paste its content —
the user is reading it themselves in the window.
