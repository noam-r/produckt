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
                @bottom-center {{
                    content: "Generated with ProDuckt, your friendly Product Product";
                    font-size: 9pt;
                    color: #666;
                    font-style: italic;
                }}
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


def scorecard_to_pdf(
    initiative_title: str,
    rice_score: float,
    rice_data: dict,
    rice_reasoning: dict,
    fdv_score: float,
    fdv_data: dict,
    fdv_reasoning: dict
) -> bytes:
    """
    Convert scorecard data to PDF.

    Args:
        initiative_title: Title of the initiative
        rice_score: RICE score value
        rice_data: Dict with reach, impact, confidence, effort
        rice_reasoning: Dict with reasoning for each RICE component
        fdv_score: FDV score value
        fdv_data: Dict with feasibility, desirability, viability
        fdv_reasoning: Dict with reasoning for each FDV component

    Returns:
        PDF file as bytes
    """
    # Helper to format reasoning text
    def format_reasoning(text):
        if not text:
            return ""
        # Escape HTML and preserve line breaks
        import html as html_module
        escaped = html_module.escape(text)
        return escaped.replace('\n', '<br>')

    # Pre-format values to avoid f-string evaluation issues with None
    rice_score_display = f"{rice_score:.1f}" if rice_score is not None else '—'
    fdv_score_display = f"{fdv_score:.1f}" if fdv_score is not None else '—'

    reach_display = rice_data.get('reach') if rice_data.get('reach') is not None else '—'
    impact_display = f"{rice_data.get('impact', 0):.1f}" if rice_data.get('impact') is not None else '—'
    confidence_display = f"{rice_data.get('confidence')}%" if rice_data.get('confidence') is not None else '—'
    effort_display = f"{rice_data.get('effort', 0):.1f}" if rice_data.get('effort') is not None else '—'

    # Build HTML content
    html_content = f"""
    <!DOCTYPE html>
    <html>
    <head>
        <meta charset="utf-8">
        <title>Scorecard - {initiative_title}</title>
        <style>
            @page {{
                size: A4;
                margin: 15mm;
                @bottom-center {{
                    content: "Generated with ProDuckt, your friendly Product Product";
                    font-size: 9pt;
                    color: #666;
                    font-style: italic;
                }}
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
                margin-top: 0;
                margin-bottom: 8pt;
                color: #1976d2;
                page-break-after: avoid;
            }}

            h2 {{
                font-size: 18pt;
                font-weight: 600;
                margin-top: 20pt;
                margin-bottom: 12pt;
                color: #000;
                page-break-after: avoid;
                border-bottom: 2pt solid #1976d2;
                padding-bottom: 4pt;
            }}

            h3 {{
                font-size: 14pt;
                font-weight: 600;
                margin-top: 12pt;
                margin-bottom: 8pt;
                color: #1976d2;
                page-break-after: avoid;
            }}

            .score-summary {{
                background-color: #f5f5f5;
                padding: 16pt;
                border-radius: 4pt;
                margin-bottom: 16pt;
                text-align: center;
                page-break-inside: avoid;
            }}

            .score-value {{
                font-size: 32pt;
                font-weight: 600;
                color: #1976d2;
                margin: 8pt 0;
            }}

            .score-label {{
                font-size: 12pt;
                color: #666;
                text-transform: uppercase;
                letter-spacing: 1pt;
            }}

            .score-formula {{
                font-size: 10pt;
                color: #666;
                margin-top: 8pt;
            }}

            .metrics-grid {{
                display: table;
                width: 100%;
                margin-bottom: 16pt;
                border-collapse: separate;
                border-spacing: 8pt;
            }}

            .metric-item {{
                display: table-cell;
                width: 25%;
                padding: 12pt;
                background-color: #f9f9f9;
                border-radius: 4pt;
                text-align: center;
                vertical-align: top;
            }}

            .metric-label {{
                font-size: 10pt;
                color: #666;
                text-transform: uppercase;
                margin-bottom: 4pt;
            }}

            .metric-value {{
                font-size: 20pt;
                font-weight: 600;
                color: #000;
                margin: 4pt 0;
            }}

            .metric-unit {{
                font-size: 9pt;
                color: #666;
            }}

            .reasoning-section {{
                margin-top: 16pt;
                page-break-inside: avoid;
            }}

            .reasoning-item {{
                margin-bottom: 12pt;
                padding: 8pt;
                background-color: #fafafa;
                border-left: 3pt solid #1976d2;
            }}

            .reasoning-title {{
                font-weight: 600;
                color: #1976d2;
                margin-bottom: 4pt;
            }}

            .reasoning-text {{
                color: #333;
                font-size: 10pt;
                line-height: 1.5;
            }}

            .fdv-metrics-grid {{
                display: table;
                width: 100%;
                margin-bottom: 16pt;
                border-collapse: separate;
                border-spacing: 8pt;
            }}

            .fdv-metric-item {{
                display: table-cell;
                width: 33.33%;
                padding: 12pt;
                background-color: #f9f9f9;
                border-radius: 4pt;
                text-align: center;
                vertical-align: top;
            }}

            .progress-bar {{
                width: 100%;
                height: 8pt;
                background-color: #e0e0e0;
                border-radius: 4pt;
                margin: 8pt 0;
                overflow: hidden;
            }}

            .progress-fill {{
                height: 100%;
                background-color: #1976d2;
                border-radius: 4pt;
            }}

            .footer {{
                margin-top: 32pt;
                padding-top: 16pt;
                border-top: 1pt solid #ddd;
                text-align: center;
                font-size: 9pt;
                color: #666;
                font-style: italic;
            }}
        </style>
    </head>
    <body>
        <h1>Initiative Scorecard</h1>
        <p style="font-size: 14pt; color: #666; margin-bottom: 24pt;">{initiative_title}</p>

        <!-- RICE Score -->
        <h2>RICE Score</h2>
        <div class="score-summary">
            <div class="score-label">RICE Score</div>
            <div class="score-value">{rice_score_display}</div>
            <div class="score-formula">(Reach × Impact × Confidence) / Effort</div>
        </div>

        <div class="metrics-grid">
            <div class="metric-item">
                <div class="metric-label">Reach</div>
                <div class="metric-value">{reach_display}</div>
                <div class="metric-unit">per quarter</div>
            </div>
            <div class="metric-item">
                <div class="metric-label">Impact</div>
                <div class="metric-value">{impact_display}</div>
                <div class="metric-unit">scale: 0.25-3.0</div>
            </div>
            <div class="metric-item">
                <div class="metric-label">Confidence</div>
                <div class="metric-value">{confidence_display}</div>
                <div class="metric-unit">certainty level</div>
            </div>
            <div class="metric-item">
                <div class="metric-label">Effort</div>
                <div class="metric-value">{effort_display}</div>
                <div class="metric-unit">person-months</div>
            </div>
        </div>

        <h3>Scoring Rationale</h3>
        <div class="reasoning-section">
            {f'<div class="reasoning-item"><div class="reasoning-title">Reach</div><div class="reasoning-text">{format_reasoning(rice_reasoning.get("reach", ""))}</div></div>' if rice_reasoning.get('reach') else ''}
            {f'<div class="reasoning-item"><div class="reasoning-title">Impact</div><div class="reasoning-text">{format_reasoning(rice_reasoning.get("impact", ""))}</div></div>' if rice_reasoning.get('impact') else ''}
            {f'<div class="reasoning-item"><div class="reasoning-title">Confidence</div><div class="reasoning-text">{format_reasoning(rice_reasoning.get("confidence", ""))}</div></div>' if rice_reasoning.get('confidence') else ''}
            {f'<div class="reasoning-item"><div class="reasoning-title">Effort</div><div class="reasoning-text">{format_reasoning(rice_reasoning.get("effort", ""))}</div></div>' if rice_reasoning.get('effort') else ''}
        </div>

        <!-- FDV Score -->
        <h2 style="page-break-before: always;">FDV Score</h2>
        <div class="score-summary">
            <div class="score-label">FDV Score</div>
            <div class="score-value">{fdv_score_display}</div>
            <div class="score-formula">(Feasibility + Desirability + Viability) / 3</div>
        </div>

        <div class="fdv-metrics-grid">
            <div class="fdv-metric-item">
                <div class="metric-label">Feasibility</div>
                <div class="metric-value">{fdv_data.get('feasibility', 0)}/10</div>
                <div class="progress-bar">
                    <div class="progress-fill" style="width: {(fdv_data.get('feasibility', 0) / 10) * 100}%;"></div>
                </div>
                <div class="metric-unit">Can we build it?</div>
            </div>
            <div class="fdv-metric-item">
                <div class="metric-label">Desirability</div>
                <div class="metric-value">{fdv_data.get('desirability', 0)}/10</div>
                <div class="progress-bar">
                    <div class="progress-fill" style="width: {(fdv_data.get('desirability', 0) / 10) * 100}%;"></div>
                </div>
                <div class="metric-unit">Do users want it?</div>
            </div>
            <div class="fdv-metric-item">
                <div class="metric-label">Viability</div>
                <div class="metric-value">{fdv_data.get('viability', 0)}/10</div>
                <div class="progress-bar">
                    <div class="progress-fill" style="width: {(fdv_data.get('viability', 0) / 10) * 100}%;"></div>
                </div>
                <div class="metric-unit">Is it sustainable?</div>
            </div>
        </div>

        <h3>Scoring Rationale</h3>
        <div class="reasoning-section">
            {f'<div class="reasoning-item"><div class="reasoning-title">Feasibility</div><div class="reasoning-text">{format_reasoning(fdv_reasoning.get("feasibility", ""))}</div></div>' if fdv_reasoning.get('feasibility') else ''}
            {f'<div class="reasoning-item"><div class="reasoning-title">Desirability</div><div class="reasoning-text">{format_reasoning(fdv_reasoning.get("desirability", ""))}</div></div>' if fdv_reasoning.get('desirability') else ''}
            {f'<div class="reasoning-item"><div class="reasoning-title">Viability</div><div class="reasoning-text">{format_reasoning(fdv_reasoning.get("viability", ""))}</div></div>' if fdv_reasoning.get('viability') else ''}
        </div>
    </body>
    </html>
    """

    # Generate PDF
    font_config = FontConfiguration()
    html = HTML(string=html_content)

    # Render to PDF
    pdf_bytes = html.write_pdf(font_config=font_config)

    return pdf_bytes
