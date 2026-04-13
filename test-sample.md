# Markdown 阅读器测试文档

这是一份用来验证 `open-md.cmd` 渲染效果的样例文档，覆盖常用 GFM 语法。

## 1. 文本样式

支持 **粗体**、*斜体*、~~删除线~~、`行内代码`，以及 [外链](https://github.com)。

> 引用块：山不在高，有仙则名；水不在深,有龙则灵。
>
> —— 刘禹锡《陋室铭》

## 2. 列表

无序列表：

- 苹果
  - 红富士
  - 嘎啦
- 香蕉
- 橙子

有序列表：

1. 打开 Everything
2. 搜索 `.md`
3. 右键 → 打开方式 → `open-md.cmd`
4. 享受阅读

任务列表：

- [x] 创建项目文件夹
- [x] 写 PowerShell 渲染脚本
- [x] 写 cmd 启动器
- [ ] 关联到默认打开方式
- [ ] 验证离线模式

## 3. 代码块

行内：使用 `marked.parse(md)` 渲染。

JavaScript：

```javascript
function greet(name) {
  const msg = `Hello, ${name}!`;
  console.log(msg);
  return msg;
}

greet("Markdown Viewer");
```

PowerShell：

```powershell
param([string]$Path)
$bytes = [System.IO.File]::ReadAllBytes($Path)
$b64   = [Convert]::ToBase64String($bytes)
Write-Host "Encoded $($bytes.Length) bytes"
```

Python：

```python
def fib(n):
    a, b = 0, 1
    for _ in range(n):
        yield a
        a, b = b, a + b

print(list(fib(10)))
```

## 4. 表格

| 特性          | 是否支持 | 说明                          |
| ------------- | :------: | ----------------------------- |
| GFM 语法      |    ✅    | gfm: true                     |
| 代码高亮      |    ✅    | highlight.js 自动检测         |
| 任务列表      |    ✅    | `- [ ]` / `- [x]`             |
| LaTeX 数学    |    ❌    | 未集成 KaTeX，需要可加        |
| Mermaid 图表  |    ❌    | 未集成，需要可加              |

## 5. 分隔线与图片

---

![占位图片](https://placehold.co/600x120/png?text=Markdown+Viewer+OK)

## 6. 中英文混排

This document mixes 中文 and English to verify that **UTF-8** decoding works end-to-end through the base64 → `TextDecoder('utf-8')` pipeline. 如果你看到这段文字渲染正常，说明编码链路没问题。

## 7. 引用嵌套

> 第一层引用
>
> > 第二层引用
> >
> > > 第三层引用：到此为止。

---

文档结束 ✅

## 8. 自动重载测试

如果你看到这一节，说明文件 watcher 在工作。
