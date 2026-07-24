"""
Proposal export — Markdown → PDF (or HTML fallback).

WeasyPrint requires system dependencies (cairo, pango, etc.)
that may not be available on all systems. This module handles
that gracefully with an HTML fallback:

    PDF (WeasyPrint) → HTML file

Usage:
    filepath, size = export_to_pdf("# My Proposal...", "Stripe")
    filepath, size = export_to_markdown("# My Proposal...", "Stripe")
"""

import html
import re
from datetime import datetime, timezone
from pathlib import Path

from src.config import ProposalConfig, StorageConfig


# ──────────────────────────────────────────────
# Check WeasyPrint availability
# ──────────────────────────────────────────────

WEASYPRINT_AVAILABLE = False
try:
    from weasyprint import HTML as WeasyHTML
    WEASYPRINT_AVAILABLE = True
except (ImportError, OSError):
    # WeasyPrint needs system-level libraries (cairo, pango, gdk-pixbuf)
    # If they're missing, we gracefully fall back to HTML export
    pass


# ──────────────────────────────────────────────
# CSS Stylesheet for Professional Proposals
# ──────────────────────────────────────────────

PROPOSAL_CSS = """
@page {
    size: A4;
    margin: 2cm 2.5cm;
    @top-right {
        content: "CONFIDENTIAL";
        font-size: 8pt;
        color: #999;
    }
    @bottom-center {
        content: counter(page) " of " counter(pages);
        font-size: 8pt;
        color: #666;
    }
}

body {
    font-family: 'Helvetica Neue', Helvetica, Arial, sans-serif;
    font-size: 11pt;
    line-height: 1.6;
    color: #333;
    max-width: 800px;
    margin: 0 auto;
    padding: 20px;
}

/* Header Banner */
.proposal-header {
    background: linear-gradient(135deg, #1a1a2e 0%, #16213e 50%, #0f3460 100%);
    color: white;
    padding: 40px 30px;
    border-radius: 8px;
    margin-bottom: 30px;
    text-align: center;
}

.proposal-header h1 {
    font-size: 20pt;
    margin: 0 0 5px 0;
    color: white;
    letter-spacing: 1px;
}

.proposal-header .tagline {
    font-size: 10pt;
    color: #aab;
    margin: 0 0 20px 0;
}

.proposal-header .meta {
    font-size: 9pt;
    color: #99a;
    margin-top: 15px;
}

/* Section Headers */
h1 {
    font-size: 18pt;
    color: #1a1a2e;
    border-bottom: 3px solid #0f3460;
    padding-bottom: 8px;
    margin-top: 35px;
}

h2 {
    font-size: 14pt;
    color: #16213e;
    border-bottom: 1px solid #ddd;
    padding-bottom: 5px;
    margin-top: 25px;
}

h3 {
    font-size: 12pt;
    color: #0f3460;
    margin-top: 18px;
}

/* Lists */
ul, ol {
    padding-left: 25px;
}

li {
    margin-bottom: 5px;
}

/* Tables */
table {
    border-collapse: collapse;
    width: 100%;
    margin: 15px 0;
}

th {
    background-color: #1a1a2e;
    color: white;
    padding: 10px 12px;
    text-align: left;
    font-size: 10pt;
}

td {
    border: 1px solid #ddd;
    padding: 8px 12px;
    font-size: 10pt;
}

tr:nth-child(even) {
    background-color: #f8f9fa;
}

/* Blockquotes (callouts) */
blockquote {
    border-left: 4px solid #0f3460;
    background: #f0f4f8;
    margin: 15px 0;
    padding: 12px 20px;
    font-style: italic;
    color: #555;
}

/* Code blocks */
code {
    background: #f4f4f4;
    padding: 2px 6px;
    border-radius: 3px;
    font-size: 9pt;
}

pre {
    background: #f4f4f4;
    padding: 15px;
    border-radius: 5px;
    overflow-x: auto;
    font-size: 9pt;
}

/* Bold & Strong */
strong {
    color: #1a1a2e;
}

/* Horizontal Rule */
hr {
    border: none;
    border-top: 2px solid #eee;
    margin: 25px 0;
}

/* Page break before major sections */
.page-break {
    page-break-before: always;
}
"""


# ──────────────────────────────────────────────
# Markdown → HTML Conversion
# ──────────────────────────────────────────────

def _simple_md_to_html(text: str) -> str:
    """
    Convert basic Markdown to HTML without external dependencies.
    """
    lines = html.escape(text, quote=True).split("\n")
    html_lines = []
    in_list = False
    in_ordered_list = False
    in_blockquote = False

    for line in lines:
        stripped = line.strip()

        # Close lists if needed
        if in_list and not (stripped.startswith("- ") or stripped.startswith("* ")):
            html_lines.append("</ul>")
            in_list = False
        if in_ordered_list and not re.match(r"^\d+\.\s", stripped):
            html_lines.append("</ol>")
            in_ordered_list = False
        if in_blockquote and not stripped.startswith(">"):
            html_lines.append("</blockquote>")
            in_blockquote = False

        # Horizontal rule
        if stripped in ("---", "***", "___"):
            html_lines.append("<hr>")
            continue

        # Headers
        match = re.match(r"^(#{1,6})\s+(.+)$", stripped)
        if match:
            level = len(match.group(1))
            content = match.group(2)
            html_lines.append(f"<h{level}>{content}</h{level}>")
            continue

        # Blockquote
        if stripped.startswith("> "):
            if not in_blockquote:
                html_lines.append("<blockquote>")
                in_blockquote = True
            html_lines.append(stripped[2:])
            continue

        # Unordered list
        if stripped.startswith("- ") or stripped.startswith("* "):
            if not in_list:
                html_lines.append("<ul>")
                in_list = True
            content = stripped[2:]
            html_lines.append(f"  <li>{content}</li>")
            continue

        # Ordered list
        ol_match = re.match(r"^(\d+)\.\s+(.+)$", stripped)
        if ol_match:
            if not in_ordered_list:
                html_lines.append("<ol>")
                in_ordered_list = True
            content = ol_match.group(2)
            html_lines.append(f"  <li>{content}</li>")
            continue

        # Empty line
        if not stripped:
            html_lines.append("")
            continue

        # Regular paragraph
        html_lines.append(f"<p>{stripped}</p>")

    # Close any open lists
    if in_list: html_lines.append("</ul>")
    if in_ordered_list: html_lines.append("</ol>")
    if in_blockquote: html_lines.append("</blockquote>")

    rendered_html = "\n".join(html_lines)

    # Inline formatting
    rendered_html = re.sub(r"\*\*(.+?)\*\*", r"<strong>\1</strong>", rendered_html)
    rendered_html = re.sub(r"\*(.+?)\*", r"<em>\1</em>", rendered_html)
    rendered_html = re.sub(r"`(.+?)`", r"<code>\1</code>", rendered_html)

    return rendered_html


def markdown_to_html(markdown_text: str, company_name: str) -> str:
    """
    Convert proposal Markdown to a full styled HTML document.
    """
    body_html = _simple_md_to_html(markdown_text)
    now = datetime.now(timezone.utc).strftime("%B %d, %Y")
    safe_company_name = html.escape(company_name, quote=True)
    safe_brand_name = html.escape(ProposalConfig.YOUR_COMPANY_NAME, quote=True)
    safe_tagline = html.escape(ProposalConfig.YOUR_COMPANY_TAGLINE, quote=True)

    return f"""<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>Business Proposal — {safe_company_name}</title>
    <style>
{PROPOSAL_CSS}
    </style>
</head>
<body>
    <div class="proposal-header">
        <h1>{safe_brand_name}</h1>
        <p class="tagline">{safe_tagline}</p>
        <hr style="border-color: rgba(255,255,255,0.2); margin: 15px 60px;">
        <p class="meta">Business Proposal for <strong>{safe_company_name}</strong></p>
        <p class="meta">Prepared: {now}</p>
    </div>

    {body_html}

    <hr>
    <p style="text-align: center; color: #999; font-size: 9pt;">
        This document is confidential and intended solely for the named recipient.
        <br>© {datetime.now().year} {safe_brand_name}. All rights reserved.
    </p>
</body>
</html>"""


# ──────────────────────────────────────────────
# Export Functions
# ──────────────────────────────────────────────

def _generate_filename(company_name: str, extension: str, custom_name: str = "") -> str:
    """Generate a filename that cannot escape the configured output directory."""
    if custom_name:
        # Drop directory components and normalize the stem to prevent path traversal.
        raw_name = Path(custom_name).name
        expected_suffix = f".{extension}"
        stem = (
            raw_name[: -len(expected_suffix)]
            if raw_name.lower().endswith(expected_suffix)
            else raw_name
        )
        safe_stem = re.sub(r"[^\w\s-]", "", stem).strip().replace(" ", "_")
        if not safe_stem:
            raise ValueError("Custom filename must contain at least one letter or number")
        return f"{safe_stem}.{extension}"

    safe_name = re.sub(r"[^\w\s-]", "", company_name).strip().replace(" ", "_").lower()
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    return f"{safe_name}_proposal_{timestamp}.{extension}"


def export_to_pdf(
    markdown_text: str,
    company_name: str,
    filename: str = "",
) -> tuple[str, int]:
    """
    Export proposal to PDF using WeasyPrint. Falls back to HTML if unavailable.
    """
    output_dir = StorageConfig.OUTPUT_DIR
    output_dir.mkdir(parents=True, exist_ok=True)

    html_content = markdown_to_html(markdown_text, company_name)

    if WEASYPRINT_AVAILABLE:
        fname = _generate_filename(company_name, "pdf", filename)
        filepath = output_dir / fname

        doc = WeasyHTML(string=html_content)
        doc.write_pdf(str(filepath))

        size = filepath.stat().st_size
        return str(filepath), size
    else:
        return export_to_html(markdown_text, company_name, filename)


def export_to_html(
    markdown_text: str,
    company_name: str,
    filename: str = "",
) -> tuple[str, int]:
    """
    Export proposal as a styled HTML file.
    """
    output_dir = StorageConfig.OUTPUT_DIR
    output_dir.mkdir(parents=True, exist_ok=True)

    html_content = markdown_to_html(markdown_text, company_name)
    fname = _generate_filename(company_name, "html", filename)
    filepath = output_dir / fname

    filepath.write_text(html_content, encoding="utf-8")
    size = filepath.stat().st_size
    return str(filepath), size


def export_to_markdown(
    markdown_text: str,
    company_name: str,
    filename: str = "",
) -> tuple[str, int]:
    """
    Export proposal as a Markdown file.
    """
    output_dir = StorageConfig.OUTPUT_DIR
    output_dir.mkdir(parents=True, exist_ok=True)

    full_content = markdown_text
    fname = _generate_filename(company_name, "md", filename)
    filepath = output_dir / fname

    filepath.write_text(full_content, encoding="utf-8")
    size = filepath.stat().st_size
    return str(filepath), size


def get_export_capabilities() -> dict:
    """Return which export formats are available."""
    return {
        "pdf": WEASYPRINT_AVAILABLE,
        "html": True,
        "markdown": True,
    }
