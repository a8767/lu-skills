---
name: markitdown
description: Convert user-provided documents and data files to Markdown with Microsoft's MarkItDown. Use when extracting text or structure from PDF, Office, HTML, CSV, JSON, XML, images, audio, ZIP, EPUB, or YouTube sources; avoid for high-fidelity visual document reproduction.
metadata:
  short-description: Convert files to Markdown with MarkItDown
---

# MarkItDown

Use Microsoft's MarkItDown when the user wants document contents extracted into Markdown for reading, search, or analysis.

## Workflow

1. Identify the exact input and requested output location. Prefer a local file the user supplied. For URLs, process only the specific URL the user requested.
2. Check whether the `markitdown` command is available. If not, explain that the Python package is separate from this skill and give the smallest relevant install command; do not install packages unless asked.
3. Convert with `markitdown <input> -o <output.md>`. For stdout or a pipeline, omit `-o` as needed. Use format extras only when the chosen converter requires them, such as `pip install 'markitdown[pdf]'` or `pip install 'markitdown[docx,pptx,xlsx]'`; use `[all]` only when the user needs broad format coverage.
4. Check that the output exists and is non-empty, then inspect enough of it to confirm the expected text and structure were captured. Report conversion failures and missing optional dependencies plainly.

## Constraints

- MarkItDown preserves useful text structure such as headings, lists, tables, and links; it is not a layout-faithful converter for human-ready document reproduction.
- Conversion support depends on optional dependencies. Match extras to the requested format instead of installing everything by default.
- MarkItDown performs I/O with the current process's privileges. For untrusted inputs, use the narrowest conversion method and do not process arbitrary paths or URLs embedded in the input.
- Plugins are disabled by default. Enable them only when the user requests a plugin-based conversion and the plugin is installed.

For current supported formats, installation details, and security guidance, consult the [official MarkItDown README](https://github.com/microsoft/markitdown#readme).
