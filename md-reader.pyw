"""
MD Reader - frameless tkinter markdown viewer with tabs
Usage: pythonw md-reader.pyw <path-to-md>
"""
import ctypes
try:
    ctypes.windll.shcore.SetProcessDpiAwareness(2)
except Exception:
    try:
        ctypes.windll.user32.SetProcessDPIAware()
    except Exception:
        pass

import tkinter as tk
import os
import sys
import re
import json
import time
import glob
import faulthandler
import unicodedata

LARGE_DOC_CHARS = 60000

SCRIPT_DIR = os.path.dirname(os.path.abspath(sys.argv[0]))
STATE_FILE = os.path.join(SCRIPT_DIR, ".md-reader-state.json")
LOCK_FILE = os.path.join(SCRIPT_DIR, ".md-reader.lock")
PENDING_GLOB = os.path.join(SCRIPT_DIR, ".md-reader-pending-*.txt")
PENDING_PREFIX = ".md-reader-pending-"

MIN_W, MIN_H = 480, 380
RESIZE_EDGE = 6
POLL_MS = 350


def get_work_area():
    """Return (x, y, w, h) of the primary monitor's work area (taskbar excluded)."""
    try:
        from ctypes import wintypes
        rect = wintypes.RECT()
        ctypes.windll.user32.SystemParametersInfoW(0x0030, 0, ctypes.byref(rect), 0)
        return (rect.left, rect.top,
                rect.right - rect.left, rect.bottom - rect.top)
    except Exception:
        return (0, 0, 1280, 720)

SERIF = "Georgia"
SANS = "Segoe UI"
MONO = "Consolas"
CJK_SANS = "Microsoft YaHei"  # consistent CJK glyphs for sidebar/tabs

MIN_FONT = 8
MAX_FONT = 28
DEFAULT_FONT = 13


def derive_font_sizes(body):
    body = max(MIN_FONT, min(MAX_FONT, int(body)))
    return {
        "body": body,
        "h1": max(body + 2, round(body * 1.85)),
        "h2": max(body + 1, round(body * 1.5)),
        "h3": max(body, round(body * 1.25)),
        "h4": max(body, round(body * 1.1)),
        "code": max(7, body - 2),
        "top": max(8, body - 3),
    }


_LEGACY_FONT = {"S": 11, "M": 13, "L": 15, "XL": 17}


# ── Win32 custom chrome (frameless + Win11 snap) ──────────
from ctypes import wintypes as _wintypes

_GWL_STYLE = -16
_GWLP_WNDPROC = -4
_WS_CAPTION = 0x00C00000
_WS_THICKFRAME = 0x00040000
_WS_MINIMIZEBOX = 0x00020000
_WS_MAXIMIZEBOX = 0x00010000
_WS_SYSMENU = 0x00080000

_WM_SIZE = 0x0005
_WM_NCCALCSIZE = 0x0083
_WM_NCHITTEST = 0x0084
_WM_NCLBUTTONDOWN = 0x00A1
_WM_NCLBUTTONUP = 0x00A2
_WM_NCLBUTTONDBLCLK = 0x00A3
_WM_SYSCOMMAND = 0x0112
_WM_ENTERSIZEMOVE = 0x0231
_WM_EXITSIZEMOVE = 0x0232

_SC_MAXIMIZE = 0xF030
_SC_RESTORE = 0xF120
_SC_MOVE = 0xF010
_SC_SIZE = 0xF000

_SIZE_RESTORED = 0
_SIZE_MAXIMIZED = 2

_HTCLIENT = 1
_HTCAPTION = 2
_HTMAXBUTTON = 9
_HTLEFT = 10
_HTRIGHT = 11
_HTTOP = 12
_HTTOPLEFT = 13
_HTTOPRIGHT = 14
_HTBOTTOM = 15
_HTBOTTOMLEFT = 16
_HTBOTTOMRIGHT = 17

_SM_CXFRAME = 32
_SM_CYFRAME = 33
_SM_CXPADDEDBORDER = 92

_SW_MAXIMIZE = 3
_SW_RESTORE = 9
_SWP_FRAMECHANGED = 0x0020
_SWP_NOMOVE = 0x0002
_SWP_NOSIZE = 0x0001
_SWP_NOZORDER = 0x0004
_SWP_NOACTIVATE = 0x0010

class _NCCALCSIZE_PARAMS(ctypes.Structure):
    _fields_ = [
        ("rgrc", _wintypes.RECT * 3),
        ("lppos", ctypes.c_void_p),
    ]


_SUBCLASSPROC_TYPE = ctypes.WINFUNCTYPE(
    ctypes.c_ssize_t,
    _wintypes.HWND, _wintypes.UINT, _wintypes.WPARAM, _wintypes.LPARAM,
    ctypes.c_size_t, ctypes.c_size_t  # uIdSubclass, dwRefData
)


def _bind_native():
    u = ctypes.windll.user32
    u.GetWindowLongW.restype = ctypes.c_long
    u.GetWindowLongW.argtypes = [_wintypes.HWND, ctypes.c_int]
    u.SetWindowLongW.restype = ctypes.c_long
    u.SetWindowLongW.argtypes = [_wintypes.HWND, ctypes.c_int, ctypes.c_long]
    u.GetWindowRect.argtypes = [_wintypes.HWND, ctypes.POINTER(_wintypes.RECT)]
    u.GetWindowRect.restype = _wintypes.BOOL
    u.IsZoomed.argtypes = [_wintypes.HWND]
    u.IsZoomed.restype = _wintypes.BOOL
    u.SetWindowPos.restype = _wintypes.BOOL
    u.SetWindowPos.argtypes = [
        _wintypes.HWND, _wintypes.HWND,
        ctypes.c_int, ctypes.c_int, ctypes.c_int, ctypes.c_int,
        ctypes.c_uint
    ]
    u.ShowWindow.argtypes = [_wintypes.HWND, ctypes.c_int]
    u.ShowWindow.restype = _wintypes.BOOL
    u.GetSystemMetrics.argtypes = [ctypes.c_int]
    u.GetSystemMetrics.restype = ctypes.c_int

    c = ctypes.windll.comctl32
    c.SetWindowSubclass.restype = ctypes.c_int  # BOOL
    c.SetWindowSubclass.argtypes = [
        _wintypes.HWND, _SUBCLASSPROC_TYPE,
        ctypes.c_size_t, ctypes.c_size_t,
    ]
    c.RemoveWindowSubclass.restype = ctypes.c_int
    c.RemoveWindowSubclass.argtypes = [
        _wintypes.HWND, _SUBCLASSPROC_TYPE, ctypes.c_size_t,
    ]
    c.DefSubclassProc.restype = ctypes.c_ssize_t
    c.DefSubclassProc.argtypes = [
        _wintypes.HWND, _wintypes.UINT,
        _wintypes.WPARAM, _wintypes.LPARAM
    ]
    return u, c


_user32, _comctl32 = _bind_native()
_CRASH_LOG = os.path.join(SCRIPT_DIR, ".md-reader-crash.log")

# Catch C-level segfaults / access violations and dump them to the log
try:
    _fh_file = open(_CRASH_LOG, "a", buffering=1, encoding="utf-8")
    _fh_file.write(f"\n=== faulthandler enabled at {time.strftime('%Y-%m-%d %H:%M:%S')} ===\n")
    faulthandler.enable(file=_fh_file)
except Exception:
    pass

# Paper-textured palettes. All themes evoke a physical paper/ink feel:
# warm off-whites instead of pure white, ink-tone text instead of pure
# black, muted accents. Key names kept identical so _configure_tags and
# load_custom_themes still work.
THEMES = {
    "Parchment": {
        # Fresh parchment — the default paper look
        "bg": "#F3EBD6", "fg": "#3C3328", "secondary": "#8A7C66",
        "accent": "#8B3A2F", "title": "#2A231A", "hr": "#DCCEB0",
        "border": "#C9B98F", "topbar": "#ECE1C3",
        "code_bg": "#E4D7B5", "quote_fg": "#6A5D4A", "scroll": "#BDAB85",
    },
    "Medium": {
        # Medium.com white-paper — clean white, near-black ink, green accent
        "bg": "#FFFFFF", "fg": "#292929", "secondary": "#6B6B6B",
        "accent": "#1A8917", "title": "#191919", "hr": "#E6E6E6",
        "border": "#E5E5E5", "topbar": "#FAFAFA",
        "code_bg": "#F4F4F4", "quote_fg": "#6A737D", "scroll": "#D6D6D6",
    },
    "Rice": {
        # Rice paper / washi — creamy ivory, graphite ink, sage accent
        "bg": "#EEE6D0", "fg": "#45423A", "secondary": "#86826F",
        "accent": "#6E7A5A", "title": "#2B2A22", "hr": "#D2C9AD",
        "border": "#BDB293", "topbar": "#E5DCC1",
        "code_bg": "#DCD1B0", "quote_fg": "#625F4E", "scroll": "#A89E81",
    },
    "Linen": {
        # Linen weave — cool bluish off-white, prussian ink
        "bg": "#E2E0D5", "fg": "#36404A", "secondary": "#6B737C",
        "accent": "#3B5A78", "title": "#1E2731", "hr": "#C4C1B4",
        "border": "#ACA99D", "topbar": "#D8D4C7",
        "code_bg": "#CECABC", "quote_fg": "#4E5565", "scroll": "#9D9A8E",
    },
    "Ink": {
        # Dark paper / charcoal sketchpad — warm off-white on near-black
        "bg": "#22201E", "fg": "#E6DFD0", "secondary": "#8F887A",
        "accent": "#D4A757", "title": "#F5ECD4", "hr": "#3A3731",
        "border": "#4A463E", "topbar": "#1C1A17",
        "code_bg": "#2D2A26", "quote_fg": "#A39B8A", "scroll": "#4A443B",
    },
}
# Legacy theme-name migration (for users with old state files).
# - Light → Medium (both are clean white-ish with green accent)
# - Sepia → Parchment (closest warm-paper match now that Kraft is gone)
# - Kraft → Parchment (0.4.3 users who already migrated)
_LEGACY_THEME = {"Light": "Medium", "Sepia": "Parchment", "Kraft": "Parchment",
                 "Morandi": "Rice", "Nord": "Linen", "Dark": "Ink"}
def load_custom_themes():
    """Merge user themes from <project>/themes/*.json into THEMES."""
    themes_dir = os.path.join(SCRIPT_DIR, "themes")
    if not os.path.isdir(themes_dir):
        return
    required = set(THEMES["Light"].keys())
    for fp in glob.glob(os.path.join(themes_dir, "*.json")):
        try:
            with open(fp, "r", encoding="utf-8") as f:
                data = json.load(f)
            if not required.issubset(data.keys()):
                continue
            name = os.path.splitext(os.path.basename(fp))[0]
            THEMES[name] = {k: data[k] for k in required}
        except Exception:
            pass


load_custom_themes()
THEME_NAMES = list(THEMES.keys())


# ── Noise bitmap for Text bgstipple (paper-grain fake) ─────
# Pure 1-bit XBM, fixed seed → stable pattern across runs. Tk accepts
# `@path.xbm` as a stipple value; combined with a tag's `background`, it
# produces a two-color dither without any image/PIL dependency.
NOISE_XBM = os.path.join(SCRIPT_DIR, ".md-reader-noise.xbm")


def _ensure_noise_xbm(path, size=32, density=0.22, seed=0xBEEF):
    if os.path.exists(path):
        return path
    try:
        import random
        rng = random.Random(seed)
        bytes_per_row = (size + 7) // 8
        total = []
        for y in range(size):
            row_bits = [1 if rng.random() < density else 0 for _ in range(size)]
            for byte_i in range(bytes_per_row):
                byte = 0
                for bit_i in range(8):
                    idx = byte_i * 8 + bit_i
                    if idx < size and row_bits[idx]:
                        byte |= (1 << bit_i)
                total.append(byte)
        lines = [
            f"#define noise_width {size}",
            f"#define noise_height {size}",
            "static char noise_bits[] = {",
            ", ".join(f"0x{b:02x}" for b in total) + " };",
        ]
        with open(path, "w") as f:
            f.write("\n".join(lines))
        return path
    except Exception:
        return None


_ensure_noise_xbm(NOISE_XBM)


def _blend_hex(c1, c2, alpha):
    """Blend c1 towards c2 by alpha (0=c1, 1=c2)."""
    r1, g1, b1 = int(c1[1:3], 16), int(c1[3:5], 16), int(c1[5:7], 16)
    r2, g2, b2 = int(c2[1:3], 16), int(c2[3:5], 16), int(c2[5:7], 16)
    r = int(r1 * (1 - alpha) + r2 * alpha)
    g = int(g1 * (1 - alpha) + g2 * alpha)
    b = int(b1 * (1 - alpha) + b2 * alpha)
    return f"#{r:02x}{g:02x}{b:02x}"


def load_state():
    try:
        with open(STATE_FILE, "r", encoding="utf-8") as f:
            return json.load(f)
    except Exception:
        return {}


def save_state(d):
    try:
        with open(STATE_FILE, "w", encoding="utf-8") as f:
            json.dump(d, f, indent=2, ensure_ascii=False)
    except Exception:
        pass


def acquire_master_lock():
    """Try to become the single master instance.
    Returns the open file handle on success (must keep alive), or None."""
    try:
        f = open(LOCK_FILE, "w")
        import msvcrt
        msvcrt.locking(f.fileno(), msvcrt.LK_NBLCK, 1)
        return f
    except (OSError, IOError):
        try:
            f.close()
        except Exception:
            pass
        return None


def send_to_master(path):
    """Drop a uniquely-named pending file for the master to pick up."""
    fname = f"{PENDING_PREFIX}{os.getpid()}-{int(time.time() * 1000)}.txt"
    try:
        with open(os.path.join(SCRIPT_DIR, fname), "w", encoding="utf-8") as f:
            f.write(os.path.abspath(path))
    except Exception:
        pass


class MDReader:
    def __init__(self, initial_path):
        self.root = tk.Tk()
        self.root.title("MD Reader")
        self.root.withdraw()
        self.root.attributes("-alpha", 0.98)
        # Frameless + stable. Manual drag/resize via Tk bindings, same as
        # the sticky-card reference project. Drops Win11 native snap but
        # nothing else works if the window keeps crashing.
        self.root.overrideredirect(True)

        st = load_state()
        self.theme_name = st.get("theme", "Parchment")
        # Migrate legacy theme names (Light/Sepia/Morandi/Nord/Dark).
        self.theme_name = _LEGACY_THEME.get(self.theme_name, self.theme_name)
        if self.theme_name not in THEMES:
            self.theme_name = "Parchment"
        fs_raw = st.get("font_size", DEFAULT_FONT)
        if isinstance(fs_raw, str):
            fs_raw = _LEGACY_FONT.get(fs_raw, DEFAULT_FONT)
        self.font_size = max(MIN_FONT, min(MAX_FONT, int(fs_raw)))
        self._sizes = derive_font_sizes(self.font_size)
        self.toc_visible = st.get("toc_visible", True)
        self.toc_width = max(140, min(600, int(st.get("toc_width", 240))))
        self.edit_visible = st.get("edit_visible", False)
        self.edit_height = max(120, min(900, int(st.get("edit_height", 280))))
        self.edit_dirty = False
        self._edit_after_id = None
        self._edit_save_after_id = None
        self._edit_sync_guard = False  # prevents re-entry while we write
        self.maximized = st.get("maximized", False)
        self.normal_geo = None
        self._toc_drag = {"active": False, "x": 0, "w": 0}
        self._edit_drag = {"active": False, "y": 0, "h": 0}

        wa_x, wa_y, wa_w, wa_h = get_work_area()
        sw = self.root.winfo_screenwidth()
        sh = self.root.winfo_screenheight()

        # Default: half-screen on the right side, full height of work area
        default_w = wa_w // 2
        default_h = wa_h
        default_x = wa_x + wa_w - default_w
        default_y = wa_y

        w = max(MIN_W, st.get("width", default_w))
        h = max(MIN_H, st.get("height", default_h))
        x = st.get("x", default_x)
        y = st.get("y", default_y)
        x = max(0, min(x, sw - 100))
        y = max(0, min(y, sh - 100))

        self.root.configure(bg=self.t("border"))

        if self.maximized:
            self.normal_geo = f"{w}x{h}+{x}+{y}"
            self.root.geometry(f"{wa_w}x{wa_h}+{wa_x}+{wa_y}")
        else:
            self.root.geometry(f"{w}x{h}+{x}+{y}")

        self.tabs = []         # [{path, name, scroll}]
        self.active = -1
        self.drag_data = {"x": 0, "y": 0}
        self.resize_data = {"active": False, "edge": None}
        self._topbar_buttons = []
        self._wndproc_ref = None
        self._original_wndproc = None
        self.hwnd = None
        self._topbar_h_cached = 0
        self._rebuild_after_id = None
        self._hit_log_count = 0
        self._tab_click_widgets = []

        self._build_ui()
        self._open_tab(initial_path)

        # Resize-edge bindings on root (sticky-card style)
        self.root.bind("<Motion>", self._resize_cursor)
        self.root.bind("<Button-1>", self._resize_start, add="+")
        self.root.bind("<B1-Motion>", self._resize_move, add="+")
        self.root.bind("<ButtonRelease-1>", self._resize_end, add="+")

        self.root.bind("<Escape>", lambda e: self._on_close())
        self.root.bind("<F11>", lambda e: self._toggle_max())
        self.root.bind("<F5>", lambda e: self._reload_active())
        self.root.bind("<Control-equal>", lambda e: self._bump_font(1))
        self.root.bind("<Control-plus>", lambda e: self._bump_font(1))
        self.root.bind("<Control-minus>", lambda e: self._bump_font(-1))
        self.root.bind("<Control-r>", lambda e: self._reload_active())
        self.root.bind("<Control-w>", lambda e: self._close_tab(self.active))
        self.root.bind("<Control-Tab>", lambda e: self._cycle_tab(1))
        self.root.bind("<Control-Shift-Tab>", lambda e: self._cycle_tab(-1))
        self.root.bind("<Control-Prior>", lambda e: self._cycle_tab(-1))
        self.root.bind("<Control-Next>", lambda e: self._cycle_tab(1))
        self.root.bind("<Control-e>", lambda e: self._toggle_edit())
        self.root.bind("<Control-s>", lambda e: self._save_edit_buffer() or "break")
        self.root.protocol("WM_DELETE_WINDOW", self._on_close)
        # If the previous session had the editor open, load the active
        # file into the edit buffer now that _open_tab has populated it.
        if self.edit_visible:
            self._load_edit_buffer_from_active()
        self.root.after(80, self._show_window)
        self.root.after(POLL_MS, self._poll_pending)
        self.root.after(900, self._poll_file_changes)
        self.root.mainloop()

    def t(self, key):
        return THEMES[self.theme_name][key]

    def fs(self, key):
        return self._sizes[key]

    def _show_window(self):
        try:
            self.root.deiconify()
        except Exception:
            pass
        self.root.lift()
        self.root.focus_force()
        self._apply_round_rect()

    def _log_crash(self, label):
        try:
            import traceback
            with open(_CRASH_LOG, "a", encoding="utf-8") as f:
                f.write(f"--- {label} ---\n")
                traceback.print_exc(file=f)
                f.write("\n")
        except Exception:
            pass

    # ── UI ────────────────────────────────────────────
    def _build_ui(self):
        self._topbar_buttons = []

        self.outer = tk.Frame(self.root, bg=self.t("border"), padx=1, pady=1)
        self.outer.pack(fill="both", expand=True)

        self.card = tk.Frame(self.outer, bg=self.t("bg"))
        self.card.pack(fill="both", expand=True)

        # ── Topbar (window chrome only) ──
        topbar = tk.Frame(self.card, bg=self.t("topbar"))
        topbar.pack(fill="x")
        self._topbar_widget = topbar
        topbar_inner = tk.Frame(topbar, bg=self.t("topbar"))
        topbar_inner.pack(fill="x", padx=14, pady=(8, 7))

        dot = tk.Label(
            topbar_inner, text="\u25cf", font=(SANS, 9),
            bg=self.t("topbar"), fg=self.t("accent")
        )
        dot.pack(side="left")

        hint = tk.Label(
            topbar_inner, text="  MD Reader", font=(SANS, self.fs("top")),
            bg=self.t("topbar"), fg=self.t("secondary")
        )
        hint.pack(side="left")

        # Right controls
        close_btn = tk.Label(
            topbar_inner, text="\u2715", font=(SANS, self.fs("top") + 2),
            bg=self.t("topbar"), fg=self.t("secondary"), cursor="hand2"
        )
        close_btn.pack(side="right")
        close_btn.bind("<Button-1>", lambda e: self._on_close())
        close_btn.bind("<Enter>", lambda e: close_btn.configure(fg="#E74C3C"))
        close_btn.bind("<Leave>", lambda e: close_btn.configure(fg=self.t("secondary")))
        self._topbar_buttons.append((close_btn, "btn"))

        max_btn = tk.Label(
            topbar_inner,
            text="\u2750" if self.maximized else "\u25a1",
            font=(SANS, self.fs("top") + 1),
            bg=self.t("topbar"), fg=self.t("secondary"), cursor="hand2"
        )
        max_btn.pack(side="right", padx=(0, 12))
        max_btn.bind("<Button-1>", lambda e: self._toggle_max())
        max_btn.bind("<Enter>", lambda e: max_btn.configure(fg=self.t("accent")))
        max_btn.bind("<Leave>", lambda e: max_btn.configure(fg=self.t("secondary")))
        self._max_btn = max_btn
        self._topbar_buttons.append((max_btn, "max"))

        size_plus = tk.Label(
            topbar_inner, text="A+", font=(SANS, self.fs("top")),
            bg=self.t("topbar"), fg=self.t("secondary"), cursor="hand2"
        )
        size_plus.pack(side="right", padx=(0, 6))
        size_plus.bind("<Button-1>", lambda e: self._bump_font(1))
        size_plus.bind("<Enter>", lambda e: size_plus.configure(fg=self.t("accent")))
        size_plus.bind("<Leave>", lambda e: size_plus.configure(fg=self.t("secondary")))
        self._topbar_buttons.append((size_plus, "btn"))

        size_lbl = tk.Label(
            topbar_inner, text=str(self.font_size),
            font=(SANS, self.fs("top")),
            bg=self.t("topbar"), fg=self.t("fg"), width=3,
        )
        size_lbl.pack(side="right", padx=(0, 0))
        size_lbl.bind("<MouseWheel>", lambda e: self._bump_font(1 if e.delta > 0 else -1))
        self._topbar_buttons.append((size_lbl, "btn"))

        size_minus = tk.Label(
            topbar_inner, text="A\u2212", font=(SANS, self.fs("top")),
            bg=self.t("topbar"), fg=self.t("secondary"), cursor="hand2"
        )
        size_minus.pack(side="right", padx=(0, 4))
        size_minus.bind("<Button-1>", lambda e: self._bump_font(-1))
        size_minus.bind("<Enter>", lambda e: size_minus.configure(fg=self.t("accent")))
        size_minus.bind("<Leave>", lambda e: size_minus.configure(fg=self.t("secondary")))
        self._topbar_buttons.append((size_minus, "btn"))

        theme_btn = tk.Label(
            topbar_inner, text=self.theme_name, font=(SANS, self.fs("top")),
            bg=self.t("topbar"), fg=self.t("secondary"), cursor="hand2"
        )
        theme_btn.pack(side="right", padx=(0, 8))
        theme_btn.bind("<Button-1>", self._next_theme)
        theme_btn.bind("<Enter>", lambda e: theme_btn.configure(fg=self.t("accent")))
        theme_btn.bind("<Leave>", lambda e: theme_btn.configure(fg=self.t("secondary")))
        self._topbar_buttons.append((theme_btn, "btn"))

        reload_btn = tk.Label(
            topbar_inner, text="\u21bb", font=(SANS, self.fs("top") + 3),
            bg=self.t("topbar"), fg=self.t("secondary"), cursor="hand2"
        )
        reload_btn.pack(side="right", padx=(0, 10))
        reload_btn.bind("<Button-1>", lambda e: self._reload_active())
        reload_btn.bind("<Enter>", lambda e: reload_btn.configure(fg=self.t("accent")))
        reload_btn.bind("<Leave>", lambda e: reload_btn.configure(fg=self.t("secondary")))
        self._topbar_buttons.append((reload_btn, "btn"))

        edit_btn = tk.Label(
            topbar_inner, text="\u270e", font=(SANS, self.fs("top") + 2),
            bg=self.t("topbar"),
            fg=self.t("accent") if self.edit_visible else self.t("secondary"),
            cursor="hand2"
        )
        edit_btn.pack(side="right", padx=(0, 10))
        edit_btn.bind("<Button-1>", lambda e: self._toggle_edit())
        edit_btn.bind("<Enter>", lambda e: edit_btn.configure(fg=self.t("fg")))
        edit_btn.bind("<Leave>", lambda e: edit_btn.configure(
            fg=self.t("accent") if self.edit_visible else self.t("secondary")))
        self._edit_btn = edit_btn
        self._topbar_buttons.append((edit_btn, "btn"))

        toc_btn = tk.Label(
            topbar_inner, text="\u2630", font=(SANS, self.fs("top") + 2),
            bg=self.t("topbar"),
            fg=self.t("accent") if self.toc_visible else self.t("secondary"),
            cursor="hand2"
        )
        toc_btn.pack(side="right", padx=(0, 10))
        toc_btn.bind("<Button-1>", lambda e: self._toggle_toc())
        toc_btn.bind("<Enter>", lambda e: toc_btn.configure(fg=self.t("fg")))
        toc_btn.bind("<Leave>", lambda e: toc_btn.configure(
            fg=self.t("accent") if self.toc_visible else self.t("secondary")))
        self._topbar_buttons.append((toc_btn, "btn"))

        tk.Frame(self.card, bg=self.t("hr"), height=1).pack(fill="x")

        # ── Tab bar (placeholder; populated by _populate_tabs) ──
        self.tab_holder = tk.Frame(self.card, bg=self.t("topbar"))
        self.tab_holder.pack(fill="x")
        self.tab_divider = tk.Frame(self.card, bg=self.t("hr"), height=1)
        self.tab_divider.pack(fill="x")

        # Drag bindings on the bare top-chrome (topbar + inner + tab_holder).
        # Tab labels and topbar buttons have their own Button-1 bindings
        # which take precedence over these Tk widget-level ones.
        for w in (topbar, topbar_inner, self.tab_holder):
            w.configure(cursor="fleur")
            w.bind("<Button-1>", self._drag_start)
            w.bind("<B1-Motion>", self._drag_move)
            w.bind("<Double-Button-1>", self._toggle_max)

        # ── Content pane wraps main (TOC + body) + optional edit pane ──
        self.content_pane = tk.Frame(self.card, bg=self.t("bg"))
        self.content_pane.pack(fill="both", expand=True)

        # Edit pane (bottom, fixed height, toggled). Built unconditionally
        # so state sticks between toggles; packed/unpacked in _toggle_edit.
        self.edit_pane = tk.Frame(self.content_pane, height=self.edit_height,
                                  bg=self.t("code_bg"))
        self.edit_pane.pack_propagate(False)
        self.edit_divider = tk.Frame(self.content_pane, height=5,
                                     bg=self.t("hr"),
                                     cursor="sb_v_double_arrow")
        self.edit_divider.bind("<Button-1>", self._edit_resize_start)
        self.edit_divider.bind("<B1-Motion>", self._edit_resize_move)
        self.edit_divider.bind("<ButtonRelease-1>", self._edit_resize_end)

        self.edit_text = tk.Text(
            self.edit_pane, bg=self.t("code_bg"), fg=self.t("fg"),
            wrap="word", relief="flat", borderwidth=0, highlightthickness=0,
            padx=24, pady=14,
            font=(MONO, max(9, self.fs("body") - 1)),
            insertbackground=self.t("fg"),
            selectbackground=self.t("hr"),
            undo=True,
        )
        self.edit_text.pack(fill="both", expand=True)
        self.edit_text.bind("<<Modified>>", self._on_edit_modified)
        self.edit_text.bind("<Control-s>",
                            lambda e: self._save_edit_buffer() or "break")

        # Pack edit pieces BEFORE main so pack-order gives main the rest.
        if self.edit_visible:
            self.edit_pane.pack(side="bottom", fill="x")
            self.edit_divider.pack(side="bottom", fill="x")

        main = tk.Frame(self.content_pane, bg=self.t("bg"))
        main.pack(side="top", fill="both", expand=True)

        self.toc_pane = tk.Frame(main, bg=self.t("topbar"), width=self.toc_width)
        # 5-px wide draggable splitter. Cursor changes on hover.
        self.toc_divider = tk.Frame(main, bg=self.t("hr"), width=5,
                                    cursor="sb_h_double_arrow")
        self.toc_divider.bind("<Button-1>", self._toc_resize_start)
        self.toc_divider.bind("<B1-Motion>", self._toc_resize_move)
        self.toc_divider.bind("<ButtonRelease-1>", self._toc_resize_end)
        if self.toc_visible:
            self.toc_pane.pack(side="left", fill="y")
            self.toc_pane.pack_propagate(False)
            self.toc_divider.pack(side="left", fill="y")

        self.toc_text = tk.Text(
            self.toc_pane, bg=self.t("topbar"), fg=self.t("fg"),
            wrap="word", relief="flat", borderwidth=0, highlightthickness=0,
            padx=16, pady=18, cursor="arrow",
            font=(CJK_SANS, max(7, self.fs("top") - 1)),
            selectbackground=self.t("hr"),
            insertbackground=self.t("topbar"),
        )
        self.toc_text.pack(fill="both", expand=True)
        self.toc_text.bind("<MouseWheel>", lambda e: self.toc_text.yview_scroll(int(-e.delta / 120), "units"))

        body = tk.Frame(main, bg=self.t("bg"))
        body.pack(side="left", fill="both", expand=True)

        self.text = tk.Text(
            body, bg=self.t("bg"), fg=self.t("fg"),
            wrap="word", relief="flat", borderwidth=0, highlightthickness=0,
            padx=64, pady=36, cursor="arrow",
            font=(SERIF, self.fs("body")),
            selectbackground=self.t("hr"),
            insertbackground=self.t("fg"),
        )
        self.text.pack(side="left", fill="both", expand=True)

        sb = tk.Scrollbar(
            body, command=self._text_yview, width=10,
            bg=self.t("bg"), troughcolor=self.t("bg"),
            activebackground=self.t("scroll"),
            borderwidth=0, highlightthickness=0, relief="flat",
        )
        sb.pack(side="right", fill="y")
        self.text.configure(yscrollcommand=sb.set)

        self._configure_tags()
        self.root.bind("<MouseWheel>", lambda e: self._wheel(e))

        # Read-only but selectable: keep state="normal" so mouse selection
        # and Ctrl+C work, but swallow any key that would mutate content.
        # state="disabled" would block selection entirely.
        self.text.bind("<Key>", self._readonly_keypress)
        self.text.bind("<<Paste>>", lambda e: "break")
        self.text.bind("<<Cut>>", lambda e: "break")

    @staticmethod
    def _readonly_keypress(e):
        # Allow copy, select-all, and navigation; block everything else.
        ctrl = bool(e.state & 0x4)
        if ctrl and e.keysym.lower() in ("c", "a", "insert", "home", "end"):
            return None
        if e.keysym in (
            "Left", "Right", "Up", "Down",
            "Home", "End", "Prior", "Next",
            "Shift_L", "Shift_R", "Control_L", "Control_R",
        ):
            return None
        return "break"

    def _text_yview(self, *args):
        self.text.yview(*args)
        if 0 <= self.active < len(self.tabs):
            self.tabs[self.active]["scroll"] = self.text.yview()[0]

    def _configure_tags(self):
        t = self.text
        body = self.fs("body")

        t.configure(spacing1=0, spacing3=0)

        # Paper-grain tag: configured FIRST so it has the lowest priority
        # (later tags override bg/font). Applied globally to the text range
        # after every render → visible per-pixel dither between widget bg
        # and this tag's darker speck color. Tags with explicit bg (code /
        # codeblock) paint over it normally.
        speck = _blend_hex(self.t("bg"), self.t("fg"), 0.09)
        if os.path.exists(NOISE_XBM):
            t.tag_configure("paper", background=speck,
                            bgstipple=f"@{NOISE_XBM}")
        else:
            t.tag_configure("paper", background=speck)

        t.tag_configure("p", font=(SERIF, body), foreground=self.t("fg"),
                        spacing1=4, spacing3=8, lmargin1=0, lmargin2=0)
        t.tag_configure("h1", font=(SERIF, self.fs("h1"), "bold"),
                        foreground=self.t("title"), spacing1=22, spacing3=12)
        t.tag_configure("h2", font=(SERIF, self.fs("h2"), "bold"),
                        foreground=self.t("title"), spacing1=18, spacing3=10)
        t.tag_configure("h3", font=(SERIF, self.fs("h3"), "bold"),
                        foreground=self.t("title"), spacing1=14, spacing3=8)
        t.tag_configure("h4", font=(SERIF, self.fs("h4"), "bold"),
                        foreground=self.t("title"), spacing1=10, spacing3=6)
        t.tag_configure("bold", font=(SERIF, body, "bold"))
        t.tag_configure("italic", font=(SERIF, body, "italic"))
        t.tag_configure("strike", font=(SERIF, body, "overstrike"),
                        foreground=self.t("secondary"))
        t.tag_configure("code", font=(MONO, self.fs("code")),
                        background=self.t("code_bg"))
        t.tag_configure("codeblock", font=(MONO, self.fs("code")),
                        background=self.t("code_bg"),
                        lmargin1=24, lmargin2=24, rmargin=24,
                        spacing1=10, spacing3=10)
        t.tag_configure("link", foreground=self.t("accent"), underline=True)
        t.tag_configure("quote", font=(SERIF, body, "italic"),
                        foreground=self.t("quote_fg"),
                        lmargin1=28, lmargin2=28, spacing1=4, spacing3=4)
        t.tag_configure("listmark", font=(SERIF, body),
                        foreground=self.t("secondary"))
        t.tag_configure("hr_line", justify="center",
                        foreground=self.t("hr"), spacing1=10, spacing3=10)
        t.tag_configure("task", font=(SANS, body),
                        foreground=self.t("accent"))
        t.tag_configure("task_done_text", font=(SERIF, body, "overstrike"),
                        foreground=self.t("secondary"))
        t.tag_configure("table_head", font=(MONO, body, "bold"),
                        background=self.t("topbar"), foreground=self.t("title"),
                        spacing1=4, spacing3=2, lmargin1=4, lmargin2=4)
        t.tag_configure("table_row", font=(MONO, body),
                        foreground=self.t("fg"),
                        spacing1=1, spacing3=1, lmargin1=4, lmargin2=4)
        t.tag_configure("table_row_alt", font=(MONO, body),
                        background=self.t("code_bg"), foreground=self.t("fg"),
                        spacing1=1, spacing3=1, lmargin1=4, lmargin2=4)

    # ── Tab bar ───────────────────────────────────────
    def _populate_tabs(self):
        for w in self.tab_holder.winfo_children():
            w.destroy()
        self.tab_holder.configure(bg=self.t("topbar"))
        self._tab_click_widgets = []

        if not self.tabs:
            return

        inner = tk.Frame(self.tab_holder, bg=self.t("topbar"))
        inner.pack(fill="x", padx=10, pady=0)

        for idx, tab in enumerate(self.tabs):
            is_active = (idx == self.active)
            container = tk.Frame(inner, bg=self.t("topbar"))
            container.pack(side="left", padx=(0, 1))

            # Top accent strip — visible only on active tab
            accent = tk.Frame(
                container, height=2,
                bg=self.t("accent") if is_active else self.t("topbar")
            )
            accent.pack(fill="x")

            row = tk.Frame(container, bg=self.t("bg") if is_active else self.t("topbar"))
            row.pack()

            name = tab["name"]
            if len(name) > 28:
                name = name[:25] + "..."

            # Active state is already marked by the 2px accent strip and
            # the bg color change — no need for bold+darkest, which reads
            # as jarring black text on a paper theme.
            lbl = tk.Label(
                row, text=" " + name, font=(CJK_SANS, self.fs("top")),
                bg=row["bg"],
                fg=self.t("fg") if is_active else self.t("secondary"),
                cursor="hand2", padx=4, pady=6
            )
            lbl.pack(side="left")
            lbl.bind("<Button-1>", lambda e, i=idx: self._switch_tab(i))
            if not is_active:
                lbl.bind("<Enter>", lambda e, w=lbl: w.configure(fg=self.t("fg")))
                lbl.bind("<Leave>", lambda e, w=lbl: w.configure(fg=self.t("secondary")))
            self._tab_click_widgets.append(lbl)

            x = tk.Label(
                row, text="\u2715 ", font=(SANS, self.fs("top")),
                bg=row["bg"],
                fg=self.t("secondary"),
                cursor="hand2", padx=4, pady=6
            )
            x.pack(side="left")
            x.bind("<Button-1>", lambda e, i=idx: self._close_tab(i))
            x.bind("<Enter>", lambda e, w=x: w.configure(fg="#E74C3C"))
            x.bind("<Leave>", lambda e, w=x: w.configure(fg=self.t("secondary")))
            self._tab_click_widgets.append(x)

    # ── TOC sidebar ───────────────────────────────────
    def _populate_toc(self):
        if not hasattr(self, "toc_text"):
            return
        self.toc_text.configure(state="normal")
        self.toc_text.delete("1.0", "end")

        # Paper tag first (lowest priority); applied to full range later.
        toc_speck = _blend_hex(self.t("topbar"), self.t("fg"), 0.08)
        if os.path.exists(NOISE_XBM):
            self.toc_text.tag_configure("paper", background=toc_speck,
                                        bgstipple=f"@{NOISE_XBM}")
        else:
            self.toc_text.tag_configure("paper", background=toc_speck)

        base = max(7, self.fs("top") - 1)
        self.toc_text.tag_configure("h1_toc", font=(CJK_SANS, base + 1, "bold"),
                                    foreground=self.t("title"),
                                    spacing1=8, spacing3=2)
        self.toc_text.tag_configure("h2_toc", font=(CJK_SANS, base),
                                    foreground=self.t("fg"),
                                    lmargin1=14, lmargin2=14,
                                    spacing1=2, spacing3=2)
        self.toc_text.tag_configure("h3_toc", font=(CJK_SANS, max(6, base - 1)),
                                    foreground=self.t("secondary"),
                                    lmargin1=26, lmargin2=26,
                                    spacing1=1, spacing3=1)
        self.toc_text.tag_configure("toc_empty", font=(CJK_SANS, base, "italic"),
                                    foreground=self.t("secondary"))

        if not (0 <= self.active < len(self.tabs)):
            self.toc_text.configure(state="disabled")
            return

        headings = self.tabs[self.active].get("headings", [])
        if not headings:
            self.toc_text.insert("end", "  no headings", "toc_empty")
            self.toc_text.configure(state="disabled")
            return

        for n, hd in enumerate(headings):
            level = hd["level"]
            if level > 3:
                continue
            tag = f"h{level}_toc"
            click_tag = f"toc_click_{n}"
            self.toc_text.tag_configure(click_tag)
            self.toc_text.tag_bind(click_tag, "<Button-1>",
                                   lambda e, m=hd["mark"]: self._jump_to(m))
            self.toc_text.tag_bind(click_tag, "<Enter>",
                                   lambda e: self.toc_text.configure(cursor="hand2"))
            self.toc_text.tag_bind(click_tag, "<Leave>",
                                   lambda e: self.toc_text.configure(cursor="arrow"))
            self.toc_text.insert("end", hd["title"] + "\n", (tag, click_tag))

        try:
            self.toc_text.tag_add("paper", "1.0", "end")
            self.toc_text.tag_lower("paper")
        except Exception:
            pass
        self.toc_text.configure(state="disabled")

    def _jump_to(self, mark):
        try:
            idx = self.text.index(mark)
            line = int(idx.split('.')[0])
            end = int(self.text.index('end').split('.')[0])
            frac = max(0.0, min(1.0, (line - 1) / max(1, end - 1)))
            self.text.yview_moveto(frac)
            if 0 <= self.active < len(self.tabs):
                self.tabs[self.active]["scroll"] = frac
        except Exception:
            pass

    def _toggle_toc(self):
        self.toc_visible = not self.toc_visible
        self._rebuild()

    # ── Edit mode ─────────────────────────────────────
    def _toggle_edit(self):
        if self.edit_visible:
            # Leaving edit mode: flush unsaved changes to file first.
            if self.edit_dirty:
                self._save_edit_buffer()
            self.edit_divider.pack_forget()
            self.edit_pane.pack_forget()
            self.edit_visible = False
        else:
            self.edit_pane.configure(height=self.edit_height)
            self.edit_pane.pack(side="bottom", fill="x")
            self.edit_divider.pack(side="bottom", fill="x", before=self.edit_pane)
            self.edit_visible = True
            self._load_edit_buffer_from_active()
        if hasattr(self, "_edit_btn"):
            self._edit_btn.configure(
                fg=self.t("accent") if self.edit_visible else self.t("secondary")
            )
        self._save_state()

    def _load_edit_buffer_from_active(self):
        """Pull the active tab's file content into the edit buffer."""
        if not (0 <= self.active < len(self.tabs)):
            return
        path = self.tabs[self.active]["path"]
        try:
            with open(path, "r", encoding="utf-8") as f:
                src = f.read()
        except Exception:
            src = ""
        self._edit_sync_guard = True
        try:
            self.edit_text.delete("1.0", "end")
            self.edit_text.insert("1.0", src)
            self.edit_text.edit_modified(False)
            self.edit_text.edit_reset()  # clear undo stack for the new file
        finally:
            self._edit_sync_guard = False
        self.edit_dirty = False

    def _on_edit_modified(self, e=None):
        # <<Modified>> fires on any change (including our own inserts).
        # Guard against programmatic loads.
        if self._edit_sync_guard:
            try:
                self.edit_text.edit_modified(False)
            except Exception:
                pass
            return
        if not self.edit_text.edit_modified():
            return
        self.edit_text.edit_modified(False)
        self.edit_dirty = True
        # Debounced live re-render of the body pane (fast).
        if self._edit_after_id is not None:
            try:
                self.root.after_cancel(self._edit_after_id)
            except Exception:
                pass
        # Scale debounce with document size: on large docs a full re-render
        # is expensive, so coalesce more aggressively to keep typing smooth.
        try:
            doc_chars = len(self.edit_text.get("1.0", "end-1c"))
        except Exception:
            doc_chars = 0
        if doc_chars > LARGE_DOC_CHARS:
            live_ms = 900
        elif doc_chars > LARGE_DOC_CHARS // 2:
            live_ms = 500
        else:
            live_ms = 250
        self._edit_after_id = self.root.after(live_ms, self._live_render_from_edit)
        # Debounced auto-save back to file (slower — coalesce keystrokes).
        if self._edit_save_after_id is not None:
            try:
                self.root.after_cancel(self._edit_save_after_id)
            except Exception:
                pass
        self._edit_save_after_id = self.root.after(max(900, live_ms + 200), self._auto_save_edit)

    def _auto_save_edit(self):
        self._edit_save_after_id = None
        if self.edit_dirty and self.edit_visible:
            self._save_edit_buffer()

    def _live_render_from_edit(self):
        self._edit_after_id = None
        if not (0 <= self.active < len(self.tabs)):
            return
        try:
            src = self.edit_text.get("1.0", "end-1c")
        except Exception:
            return
        self._render_active(src_override=src)

    def _save_edit_buffer(self):
        """Write current edit buffer back to the active tab's file.
        Bumps the tab's mtime so the file watcher ignores the echo."""
        if not (0 <= self.active < len(self.tabs)):
            return
        if not self.edit_visible:
            return
        tab = self.tabs[self.active]
        path = tab["path"]
        try:
            src = self.edit_text.get("1.0", "end-1c")
            with open(path, "w", encoding="utf-8") as f:
                f.write(src)
            try:
                tab["mtime"] = os.path.getmtime(path)
            except Exception:
                pass
            self.edit_dirty = False
        except Exception:
            self._log_crash("save_edit_buffer")

    # ── Edit-pane vertical splitter ──────────────────
    def _edit_resize_start(self, e):
        self._edit_drag = {
            "active": True,
            "y": e.y_root,
            "h": self.edit_pane.winfo_height(),
        }
        return "break"

    def _edit_resize_move(self, e):
        if not self._edit_drag.get("active"):
            return
        dy = e.y_root - self._edit_drag["y"]
        # Dragging divider UP grows edit pane (dy negative → larger edit).
        new_h = max(120, min(900, self._edit_drag["h"] - dy))
        self.edit_pane.configure(height=new_h)
        self.edit_height = new_h
        return "break"

    def _edit_resize_end(self, e):
        if self._edit_drag.get("active"):
            self._edit_drag["active"] = False
            self._save_state()
        return "break"

    def _toggle_max(self, e=None):
        try:
            if self.maximized:
                if self.normal_geo:
                    self.root.geometry(self.normal_geo)
                self.maximized = False
            else:
                self.normal_geo = self.root.geometry()
                wa_x, wa_y, wa_w, wa_h = get_work_area()
                self.root.geometry(f"{wa_w}x{wa_h}+{wa_x}+{wa_y}")
                self.maximized = True
            if hasattr(self, "_max_btn"):
                self._max_btn.configure(text="\u2750" if self.maximized else "\u25a1")
            self._save_state()
            self._apply_round_rect()
        except Exception:
            self._log_crash("_toggle_max")
        return "break"

    def _wheel(self, e):
        # Forward wheel to whichever pane the mouse is over
        try:
            wx = e.x_root - self.toc_pane.winfo_rootx()
            ww = self.toc_pane.winfo_width()
            if self.toc_visible and 0 <= wx < ww:
                self.toc_text.yview_scroll(int(-e.delta / 120), "units")
                return
        except Exception:
            pass
        self.text.yview_scroll(int(-e.delta / 120), "units")

    # ── File watcher ──────────────────────────────────
    def _poll_file_changes(self):
        try:
            if 0 <= self.active < len(self.tabs):
                tab = self.tabs[self.active]
                try:
                    cur = os.path.getmtime(tab["path"])
                    if "mtime" in tab and cur != tab["mtime"]:
                        if not self.edit_visible:
                            # Viewer mode — straightforward reload.
                            self._render_active()
                        elif not self.edit_dirty:
                            # Edit mode but buffer is clean → external
                            # process (Claude Code, another editor, etc.)
                            # changed the file. Pull it into the edit
                            # buffer AND re-render the body.
                            try:
                                with open(tab["path"], "r",
                                          encoding="utf-8") as f:
                                    src = f.read()
                                self._edit_sync_guard = True
                                try:
                                    self.edit_text.delete("1.0", "end")
                                    self.edit_text.insert("1.0", src)
                                    self.edit_text.edit_modified(False)
                                finally:
                                    self._edit_sync_guard = False
                                tab["mtime"] = cur
                                self._render_active(src_override=src)
                            except Exception:
                                tab["mtime"] = cur
                        else:
                            # Edit mode AND buffer is dirty. Keep local
                            # edits; log the conflict. User has to resolve
                            # by saving (overwriting external) or closing
                            # edit mode (accepting external on next
                            # reload).
                            self._log_crash(
                                f"external_edit_conflict path={tab['path']}"
                            )
                            tab["mtime"] = cur
                except Exception:
                    pass
        except Exception:
            pass
        self.root.after(900, self._poll_file_changes)

    # ── Tab operations ────────────────────────────────
    def _open_tab(self, path):
        path = os.path.abspath(path)
        # Already open? just switch
        for idx, tab in enumerate(self.tabs):
            if os.path.normcase(tab["path"]) == os.path.normcase(path):
                self._switch_tab(idx)
                return
        self.tabs.append({
            "path": path,
            "name": os.path.basename(path),
            "scroll": 0.0,
        })
        self._switch_tab(len(self.tabs) - 1)

    def _switch_tab(self, idx):
        if idx < 0 or idx >= len(self.tabs):
            return
        # Save scroll of current tab before switching
        if 0 <= self.active < len(self.tabs):
            try:
                self.tabs[self.active]["scroll"] = self.text.yview()[0]
            except Exception:
                pass
        # If edit mode is on and current buffer is dirty, flush it first.
        if self.edit_visible and self.edit_dirty:
            self._save_edit_buffer()
        self.active = idx
        self._populate_tabs()
        self._render_active()
        if self.edit_visible:
            self._load_edit_buffer_from_active()
        self.root.title(f"MD Reader - {self.tabs[idx]['name']}")

    def _close_tab(self, idx):
        if idx < 0 or idx >= len(self.tabs):
            return
        del self.tabs[idx]
        if not self.tabs:
            self._on_close()
            return
        if self.active >= len(self.tabs):
            self.active = len(self.tabs) - 1
        elif idx < self.active:
            self.active -= 1
        elif idx == self.active:
            self.active = min(idx, len(self.tabs) - 1)
        self._populate_tabs()
        self._render_active()
        self.root.title(f"MD Reader - {self.tabs[self.active]['name']}")

    def _cycle_tab(self, delta):
        if not self.tabs:
            return
        self._switch_tab((self.active + delta) % len(self.tabs))

    def _reload_active(self):
        if 0 <= self.active < len(self.tabs):
            self._render_active()

    # ── Markdown rendering ───────────────────────────
    def _render_active(self, src_override=None):
        """Render the active tab's body pane.

        If `src_override` is given, render from that string (used by edit
        mode's live preview) and SKIP the file read and mtime update —
        the file on disk hasn't changed yet.
        """
        if not (0 <= self.active < len(self.tabs)):
            return
        tab = self.tabs[self.active]
        path = tab["path"]
        if src_override is not None:
            src = src_override
        else:
            try:
                with open(path, "r", encoding="utf-8") as f:
                    src = f.read()
                try:
                    tab["mtime"] = os.path.getmtime(path)
                except Exception:
                    pass
            except FileNotFoundError:
                src = f"# File Not Found\n\n`{path}`"
            except Exception as e:
                src = f"# Error\n\n```\n{e}\n```"

        self._cur_headings = []
        self.text.delete("1.0", "end")
        self._render(src)
        # Skip paper-grain stipple on large docs — bgstipple redraw is the
        # main scroll-jank source. Small docs keep the texture.
        if len(src) < LARGE_DOC_CHARS:
            try:
                self.text.tag_add("paper", "1.0", "end")
                self.text.tag_lower("paper")
            except Exception:
                pass
        tab["headings"] = self._cur_headings
        self._populate_toc()
        self.text.yview_moveto(tab.get("scroll", 0.0))

    _inline_re = re.compile(
        r'(`[^`\n]+`)'
        r'|(\*\*[^*\n]+\*\*)'
        r'|(__[^_\n]+__)'
        r'|(\*[^*\n]+\*)'
        r'|(~~[^~\n]+~~)'
        r'|(\[[^\]\n]+\]\([^)\n]+\))'
    )

    @staticmethod
    def _display_width(s):
        w = 0
        for ch in s:
            ea = unicodedata.east_asian_width(ch)
            w += 2 if ea in ("W", "F") else 1
        return w

    @staticmethod
    def _pad_cell(cell, width, align):
        cur = MDReader._display_width(cell)
        fill = max(0, width - cur)
        if align == "r":
            return " " * fill + cell
        if align == "c":
            l = fill // 2
            return " " * l + cell + " " * (fill - l)
        return cell + " " * fill

    def _render(self, md):
        """Build the entire body as one string + a list of tag spans, then
        do a single insert and batched tag_add. Keeps Tk round-trips O(#spans)
        instead of O(#segments), which is the big win on large docs."""
        lines = md.replace("\r\n", "\n").replace("\r", "\n").split("\n")
        n = len(lines)

        parts = []            # text chunks to concatenate
        spans = []            # (start_char, end_char, tag_or_tuple)
        cursor = [0]          # running char offset
        heading_todo = []     # (char_offset, mark_key)

        def emit(text, tag=None):
            if not text:
                return
            start = cursor[0]
            parts.append(text)
            cursor[0] = start + len(text)
            if tag:
                spans.append((start, cursor[0], tag))

        inline_re = self._inline_re

        def emit_inline(text, base):
            base_t = tuple(base) if not isinstance(base, tuple) else base
            pos = 0
            for m in inline_re.finditer(text):
                if m.start() > pos:
                    emit(text[pos:m.start()], base_t)
                seg = m.group(0)
                if m.group(1):
                    emit(" " + seg[1:-1] + " ", base_t + ("code",))
                elif m.group(2) or m.group(3):
                    emit(seg[2:-2], base_t + ("bold",))
                elif m.group(4):
                    emit(seg[1:-1], base_t + ("italic",))
                elif m.group(5):
                    emit(seg[2:-2], base_t + ("strike",))
                elif m.group(6):
                    lm = re.match(r'\[([^\]]+)\]\(([^)]+)\)', seg)
                    if lm:
                        emit(lm.group(1), base_t + ("link",))
                pos = m.end()
            if pos < len(text):
                emit(text[pos:], base_t)

        def emit_table(header_line, sep_line, row_lines):
            def split_cells(s):
                s = s.strip()
                if s.startswith("|"):
                    s = s[1:]
                if s.endswith("|"):
                    s = s[:-1]
                return [c.strip() for c in s.split("|")]

            headers = split_cells(header_line)
            sep_cells = split_cells(sep_line)
            rows = [split_cells(r) for r in row_lines]
            ncols = len(headers)

            aligns = []
            for s in sep_cells[:ncols]:
                left = s.startswith(":")
                right = s.endswith(":")
                if left and right:
                    aligns.append("c")
                elif right:
                    aligns.append("r")
                else:
                    aligns.append("l")
            while len(aligns) < ncols:
                aligns.append("l")

            widths = [self._display_width(h) for h in headers]
            for row in rows:
                for c in range(ncols):
                    cell = row[c] if c < len(row) else ""
                    cw = self._display_width(cell)
                    if cw > widths[c]:
                        widths[c] = cw

            def fmt(cells):
                out = []
                for c in range(ncols):
                    cell = cells[c] if c < len(cells) else ""
                    out.append(self._pad_cell(cell, widths[c], aligns[c]))
                return "  ".join(out)

            emit("\n")
            emit(fmt(headers) + "\n", "table_head")
            for ri, row in enumerate(rows):
                emit(fmt(row) + "\n", "table_row_alt" if ri % 2 else "table_row")
            emit("\n")

        i = 0
        in_code = False
        code_buf = []
        special_re = re.compile(r'^(#{1,6}\s|```|>\s|\s*[-*+]\s|\s*\d+\.\s|---+\s*$|\*\*\*\s*$|___\s*$)')

        while i < n:
            line = lines[i]

            m = re.match(r'^```(\w*)\s*$', line)
            if m:
                if not in_code:
                    in_code = True
                    code_buf = []
                else:
                    in_code = False
                    emit("\n".join(code_buf) + "\n", "codeblock")
                i += 1
                continue
            if in_code:
                code_buf.append(line)
                i += 1
                continue

            stripped = line.strip()

            if re.match(r'^(-{3,}|\*{3,}|_{3,})\s*$', stripped):
                emit("─" * 36 + "\n", "hr_line")
                i += 1
                continue

            m = re.match(r'^(#{1,4})\s+(.*)$', line)
            if m:
                level = len(m.group(1))
                title = m.group(2).strip()
                tag = f"h{level}"
                if level <= 3:
                    mark_key = f"hd_{len(self._cur_headings)}"
                    heading_todo.append((cursor[0], mark_key))
                    self._cur_headings.append({"level": level, "title": title, "mark": mark_key})
                emit(title + "\n", tag)
                i += 1
                continue

            if stripped.startswith(">"):
                buf = []
                while i < n and lines[i].strip().startswith(">"):
                    buf.append(re.sub(r'^\s*>\s?', '', lines[i]))
                    i += 1
                emit_inline(" ".join(s.strip() for s in buf if s.strip()), ("quote",))
                emit("\n", "quote")
                continue

            m = re.match(r'^(\s*)[-*+]\s+\[([ xX])\]\s+(.*)$', line)
            if m:
                indent, mark, content = m.group(1), m.group(2), m.group(3)
                pad = "    " * (len(indent) // 2)
                box = "\u2611  " if mark.lower() == "x" else "\u2610  "
                emit(pad + box, "task")
                if mark.lower() == "x":
                    emit(content + "\n", "task_done_text")
                else:
                    emit_inline(content, ("p",))
                    emit("\n", "p")
                i += 1
                continue

            m = re.match(r'^(\s*)[-*+]\s+(.*)$', line)
            if m:
                indent, content = m.group(1), m.group(2)
                pad = "    " * (len(indent) // 2)
                emit(pad + "•  ", "listmark")
                emit_inline(content, ("p",))
                emit("\n", "p")
                i += 1
                continue

            m = re.match(r'^(\s*)(\d+)\.\s+(.*)$', line)
            if m:
                indent, num, content = m.group(1), m.group(2), m.group(3)
                pad = "    " * (len(indent) // 2)
                emit(f"{pad}{num}.  ", "listmark")
                emit_inline(content, ("p",))
                emit("\n", "p")
                i += 1
                continue

            if "|" in line and i + 1 < n:
                sep = lines[i + 1].strip()
                if re.match(r'^\|?\s*:?-{2,}:?\s*(\|\s*:?-{2,}:?\s*)*\|?\s*$', sep):
                    rows = []
                    j = i + 2
                    while j < n and "|" in lines[j] and lines[j].strip():
                        rows.append(lines[j])
                        j += 1
                    emit_table(line, lines[i + 1], rows)
                    i = j
                    continue

            if not stripped:
                emit("\n")
                i += 1
                continue

            para = [line]
            j = i + 1
            while j < n and lines[j].strip() and not special_re.match(lines[j]) and "|" not in lines[j]:
                para.append(lines[j])
                j += 1
            emit_inline(" ".join(s.strip() for s in para), ("p",))
            emit("\n", "p")
            i = j

        # Single batch insert
        big = "".join(parts)
        if big:
            self.text.insert("1.0", big)

        # Merge adjacent same-tag spans to reduce tag_add calls
        merged = []
        for start, end, tag in spans:
            if merged and merged[-1][2] == tag and merged[-1][1] == start:
                prev = merged[-1]
                merged[-1] = (prev[0], end, tag)
            else:
                merged.append((start, end, tag))

        # Apply tags via char offsets
        for start, end, tag in merged:
            s_idx = f"1.0 + {start} chars"
            e_idx = f"1.0 + {end} chars"
            if isinstance(tag, tuple):
                for tg in tag:
                    self.text.tag_add(tg, s_idx, e_idx)
            else:
                self.text.tag_add(tag, s_idx, e_idx)

        # Place heading marks
        for off, mark_key in heading_todo:
            self.text.mark_set(mark_key, f"1.0 + {off} chars")
            self.text.mark_gravity(mark_key, "left")

    # ── Theme / size ─────────────────────────────────
    def _next_theme(self, e=None):
        idx = THEME_NAMES.index(self.theme_name)
        self.theme_name = THEME_NAMES[(idx + 1) % len(THEME_NAMES)]
        self._rebuild()
        return "break"

    def _bump_font(self, delta):
        new = max(MIN_FONT, min(MAX_FONT, self.font_size + delta))
        if new == self.font_size:
            return "break"
        self.font_size = new
        self._sizes = derive_font_sizes(self.font_size)
        # Update the size label immediately for responsive feedback,
        # then debounce the heavy rebuild so rapid clicks coalesce.
        try:
            for w, _ in self._topbar_buttons:
                if isinstance(w, tk.Label) and w.cget("text").isdigit():
                    w.configure(text=str(self.font_size))
                    break
        except Exception:
            pass
        if self._rebuild_after_id is not None:
            try:
                self.root.after_cancel(self._rebuild_after_id)
            except Exception:
                pass
        self._rebuild_after_id = self.root.after(180, self._rebuild_now)
        return "break"

    def _rebuild_now(self):
        self._rebuild_after_id = None
        self._rebuild()

    def _rebuild(self):
        # Save current scroll
        if 0 <= self.active < len(self.tabs):
            try:
                self.tabs[self.active]["scroll"] = self.text.yview()[0]
            except Exception:
                pass
        # Snapshot the edit buffer BEFORE destroy so theme/font switches
        # don't wipe unsaved edits. Preserve dirty state too.
        preserved_edit = None
        preserved_dirty = False
        if self.edit_visible and hasattr(self, "edit_text"):
            try:
                preserved_edit = self.edit_text.get("1.0", "end-1c")
                preserved_dirty = self.edit_dirty
            except Exception:
                preserved_edit = None
        self.root.configure(bg=self.t("border"))
        self.outer.destroy()
        self._build_ui()
        self._populate_tabs()
        if self.edit_visible and preserved_edit is not None:
            # Push the preserved buffer back into the new edit_text and
            # render the body from it (not from disk — disk may be stale).
            self._edit_sync_guard = True
            try:
                self.edit_text.delete("1.0", "end")
                self.edit_text.insert("1.0", preserved_edit)
                self.edit_text.edit_modified(False)
                self.edit_text.edit_reset()
            finally:
                self._edit_sync_guard = False
            self.edit_dirty = preserved_dirty
            self._render_active(src_override=preserved_edit)
        else:
            self._render_active()
        self._save_state()

    # ── Drag (move window) ───────────────────────────
    def _drag_start(self, e):
        if self.maximized:
            return
        self.drag_data = {"x": e.x_root - self.root.winfo_x(),
                          "y": e.y_root - self.root.winfo_y()}

    def _drag_move(self, e):
        if self.maximized:
            return
        nx = e.x_root - self.drag_data["x"]
        ny = e.y_root - self.drag_data["y"]
        self.root.geometry(f"+{nx}+{ny}")

    # ── Resize ───────────────────────────────────────
    def _get_edge(self, e):
        w = self.root.winfo_width()
        h = self.root.winfo_height()
        x = e.x_root - self.root.winfo_x()
        y = e.y_root - self.root.winfo_y()
        edges = []
        if x >= w - RESIZE_EDGE:
            edges.append("e")
        elif x <= RESIZE_EDGE:
            edges.append("w")
        if y >= h - RESIZE_EDGE:
            edges.append("s")
        return "".join(edges) if edges else None

    def _resize_cursor(self, e):
        if self.maximized or self.resize_data["active"]:
            self.root.configure(cursor="")
            return
        edge = self._get_edge(e)
        cursors = {
            "e": "sb_h_double_arrow", "w": "sb_h_double_arrow",
            "s": "sb_v_double_arrow",
            "se": "size_nw_se", "sw": "size_ne_sw",
        }
        self.root.configure(cursor=cursors.get(edge, ""))

    def _resize_start(self, e):
        if self.maximized:
            return
        edge = self._get_edge(e)
        if edge:
            self.resize_data = {
                "active": True, "edge": edge,
                "x": e.x_root, "y": e.y_root,
                "w": self.root.winfo_width(), "h": self.root.winfo_height(),
                "rx": self.root.winfo_x(), "ry": self.root.winfo_y(),
            }

    def _resize_move(self, e):
        if not self.resize_data["active"]:
            return
        d = self.resize_data
        dx = e.x_root - d["x"]
        dy = e.y_root - d["y"]
        edge = d["edge"]
        new_w, new_h, new_x = d["w"], d["h"], d["rx"]
        if "e" in edge:
            new_w = max(MIN_W, d["w"] + dx)
        if "w" in edge:
            new_w = max(MIN_W, d["w"] - dx)
            new_x = d["rx"] + d["w"] - new_w
        if "s" in edge:
            new_h = max(MIN_H, d["h"] + dy)
        self.root.geometry(f"{new_w}x{new_h}+{new_x}+{d['ry']}")
        self._apply_round_rect()

    def _resize_end(self, e):
        if self.resize_data["active"]:
            self.resize_data["active"] = False
            self._save_state()
            self._apply_round_rect()

    # ── TOC splitter drag ────────────────────────────
    def _toc_resize_start(self, e):
        self._toc_drag = {
            "active": True,
            "x": e.x_root,
            "w": self.toc_pane.winfo_width(),
        }
        return "break"

    def _toc_resize_move(self, e):
        if not self._toc_drag.get("active"):
            return
        dx = e.x_root - self._toc_drag["x"]
        new_w = max(140, min(600, self._toc_drag["w"] + dx))
        self.toc_pane.configure(width=new_w)
        self.toc_width = new_w
        return "break"

    def _toc_resize_end(self, e):
        if self._toc_drag.get("active"):
            self._toc_drag["active"] = False
            self._save_state()
        return "break"

    # ── Rounded window corners ───────────────────────
    def _apply_round_rect(self):
        """Clip the window to a rounded rectangle via Win32 SetWindowRgn.
        Must be re-applied after every geometry change (the region is
        tied to pixel dimensions, not relative)."""
        try:
            self.root.update_idletasks()
            w = self.root.winfo_width()
            h = self.root.winfo_height()
            if w < 10 or h < 10:
                return
            hwnd = int(self.root.wm_frame(), 16)
            gdi = ctypes.windll.gdi32
            gdi.CreateRoundRectRgn.restype = ctypes.c_void_p
            gdi.CreateRoundRectRgn.argtypes = [
                ctypes.c_int, ctypes.c_int,
                ctypes.c_int, ctypes.c_int,
                ctypes.c_int, ctypes.c_int,
            ]
            radius = 18
            rgn = gdi.CreateRoundRectRgn(0, 0, w + 1, h + 1, radius, radius)
            # SetWindowRgn takes ownership of the region handle.
            _user32.SetWindowRgn(hwnd, rgn, True)
        except Exception:
            pass

    # ── IPC: poll for new file requests ──────────────
    def _poll_pending(self):
        try:
            for fp in glob.glob(PENDING_GLOB):
                try:
                    with open(fp, "r", encoding="utf-8") as f:
                        path = f.read().strip()
                except Exception:
                    path = ""
                try:
                    os.remove(fp)
                except Exception:
                    pass
                if path and os.path.exists(path):
                    self._open_tab(path)
                    self._show_window()
        except Exception:
            pass
        self.root.after(POLL_MS, self._poll_pending)

    # ── State ────────────────────────────────────────
    def _save_state(self):
        # Always persist the *normal* (non-maximized) geometry under width/h/x/y.
        geo = self.normal_geo if (self.maximized and self.normal_geo) else self.root.geometry()
        m = re.match(r'(\d+)x(\d+)\+(-?\d+)\+(-?\d+)', geo)
        if not m:
            return
        save_state({
            "width": int(m.group(1)),
            "height": int(m.group(2)),
            "x": int(m.group(3)),
            "y": int(m.group(4)),
            "theme": self.theme_name,
            "font_size": self.font_size,
            "toc_visible": self.toc_visible,
            "toc_width": self.toc_width,
            "edit_visible": self.edit_visible,
            "edit_height": self.edit_height,
            "maximized": self.maximized,
        })

    def _on_close(self):
        if self.edit_visible and self.edit_dirty:
            self._save_edit_buffer()
        self._save_state()
        # Best-effort cleanup of leftover pending files (edge cases)
        try:
            for fp in glob.glob(PENDING_GLOB):
                try:
                    os.remove(fp)
                except Exception:
                    pass
        except Exception:
            pass
        self.root.destroy()


def _error_dialog(msg):
    r = tk.Tk()
    r.withdraw()
    import tkinter.messagebox as mb
    mb.showerror("MD Reader", msg)
    r.destroy()


if __name__ == "__main__":
    if len(sys.argv) < 2:
        _error_dialog("Usage: md-reader.pyw <path-to-file.md>")
        sys.exit(0)
    md_path = sys.argv[1]
    if not os.path.exists(md_path):
        _error_dialog(f"File not found:\n{md_path}")
        sys.exit(1)

    lock = acquire_master_lock()
    if lock is None:
        # Another instance is running — hand off and exit
        send_to_master(md_path)
        sys.exit(0)

    # We are the master
    try:
        MDReader(md_path)
    finally:
        try:
            lock.close()
        except Exception:
            pass
