"""Sanitizer strips tutorial UI and code dumps from extracted bodies."""

from __future__ import annotations

from core.article_content_sanitize import sanitize_extracted_article_body
from core.rss_extract import html_to_text


def test_sanitize_removes_copy_code_widget_and_python_run() -> None:
    raw = """In this tutorial, we build VOID. Check out the Full Codes Copy Code Copied Use a different Browser import os, sys
from pathlib import Path

def run(cmd, check=True):
    print(f"running")
    return subprocess.run(cmd, shell=True)

We set up the environment and clone the repo. Also, feel free to follow us on Twitter. The post My Title appeared first on MarkTechPost."""
    out = sanitize_extracted_article_body(raw)
    assert "import os" not in out
    assert "def run(" not in out
    assert "Copy Code" not in out
    assert "Check out the Full Codes" not in out
    assert "MarkTechPost" not in out
    assert "VOID" in out or "tutorial" in out.lower()
    assert "We set up the environment" in out


def test_html_to_text_drops_pre_blocks() -> None:
    html = "<p>Hello intro.</p><pre>import torch\ntorch.nn</pre><p>Bye.</p>"
    plain = html_to_text(html)
    assert "import torch" not in plain
    assert "Hello intro" in plain.replace(".", "")
    assert "Bye" in plain
