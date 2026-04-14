# Markdown Reader Translation Test

This document verifies the English-to-Chinese translation feature in MD Reader.

## Features Under Test

The translator should handle the following elements cleanly:

- **Bold text** and *italic text*
- Inline `code` snippets
- Links like [GitHub](https://github.com)
- Nested lists and task items

### Task List

- [ ] Paragraph translation
- [ ] Heading translation
- [x] Setup complete

## Code Block (should stay verbatim)

```python
def greet(name):
    return f"Hello, {name}!"
```

## Blockquote

> The best way to predict the future is to invent it.

## Long Paragraph

Software engineering is the systematic application of engineering approaches to the development of software. It involves the careful design, construction, testing, and maintenance of software systems, balancing competing constraints of performance, cost, and time.

## Table (should stay verbatim)

| Column A | Column B |
| -------- | -------- |
| value 1  | value 2  |

That's the end of the sample.
