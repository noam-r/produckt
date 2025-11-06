"""
PDF generation service using WeasyPrint.
"""

import io
import markdown
from weasyprint import HTML, CSS
from weasyprint.text.fonts import FontConfiguration


def markdown_to_pdf(markdown_content: str, title: str = "Document") -> bytes:
    """
    Convert markdown content to PDF.

    Args:
        markdown_content: Markdown text to convert
        title: Document title for metadata

    Returns:
        PDF file as bytes
    """
    # Convert markdown to HTML
    md = markdown.Markdown(extensions=['tables', 'fenced_code', 'nl2br'])
    html_body = md.convert(markdown_content)

    # Create full HTML document with styling
    html_content = f"""
    <!DOCTYPE html>
    <html>
    <head>
        <meta charset="utf-8">
        <title>{title}</title>
        <style>
            @page {{
                size: A4;
                margin: 15mm;
            }}

            body {{
                font-family: -apple-system, BlinkMacSystemFont, "Segoe UI", Helvetica, Arial, sans-serif;
                font-size: 11pt;
                line-height: 1.6;
                color: #000;
            }}

            h1 {{
                font-size: 24pt;
                font-weight: 600;
                margin-top: 12pt;
                margin-bottom: 8pt;
                color: #1976d2;
                page-break-after: avoid;
                page-break-inside: avoid;
            }}

            h2 {{
                font-size: 18pt;
                font-weight: 600;
                margin-top: 12pt;
                margin-bottom: 8pt;
                color: #000;
                page-break-after: avoid;
            }}

            h3 {{
                font-size: 14pt;
                font-weight: 500;
                margin-top: 10pt;
                margin-bottom: 6pt;
                color: #000;
                page-break-after: avoid;
            }}

            p {{
                margin-bottom: 8pt;
            }}

            ul, ol {{
                margin-bottom: 8pt;
                padding-left: 20pt;
            }}

            li {{
                margin-bottom: 4pt;
            }}

            code {{
                background-color: #f5f5f5;
                padding: 2pt 4pt;
                border-radius: 3pt;
                font-size: 10pt;
                font-family: "Courier New", Courier, monospace;
            }}

            pre {{
                background-color: #f5f5f5;
                padding: 8pt;
                border-radius: 3pt;
                overflow-x: auto;
                margin-bottom: 8pt;
            }}

            pre code {{
                background-color: transparent;
                padding: 0;
            }}

            blockquote {{
                border-left: 4pt solid #1976d2;
                padding-left: 8pt;
                margin-left: 0;
                font-style: italic;
                color: #666;
            }}

            table {{
                width: 100%;
                border-collapse: collapse;
                margin-bottom: 12pt;
                margin-top: 8pt;
                page-break-inside: auto;
            }}

            thead {{
                display: table-header-group;
            }}

            tbody {{
                display: table-row-group;
            }}

            tr {{
                page-break-inside: avoid;
                page-break-after: auto;
            }}

            th, td {{
                border: 1pt solid #ddd;
                padding: 6pt;
                text-align: left;
                vertical-align: top;
            }}

            th {{
                background-color: #f5f5f5;
                font-weight: 600;
            }}

            strong {{
                font-weight: 600;
            }}

            em {{
                font-style: italic;
            }}
        </style>
    </head>
    <body>
        {html_body}
    </body>
    </html>
    """

    # Generate PDF
    font_config = FontConfiguration()
    html = HTML(string=html_content)

    # Render to PDF
    pdf_bytes = html.write_pdf(font_config=font_config)

    return pdf_bytes
