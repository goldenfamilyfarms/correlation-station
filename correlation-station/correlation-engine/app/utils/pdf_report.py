from reportlab.lib.pagesizes import A4
from reportlab.lib.styles import ParagraphStyle, getSampleStyleSheet
from reportlab.platypus import SimpleDocTemplate, Paragraph, Spacer, PageBreak
from reportlab.lib.units import mm
from datetime import datetime
from typing import Dict


def generate_pdf_summary(errors: Dict[str, dict], output_path: str, developer_prompt: str = None) -> str:
    """Generate a richer PDF summarizing per-circuit results.

    - Adds a front page with summary and a simple table-of-contents (list of circuit keys)
    - Then writes full per-circuit sections with full traceback in monospaced font
    """
    doc = SimpleDocTemplate(output_path, pagesize=A4, leftMargin=18 * mm, rightMargin=18 * mm)
    base_styles = getSampleStyleSheet()

    # Define a code style (monospaced)
    code_style = ParagraphStyle(
        name='Code',
        parent=base_styles['Normal'],
        fontName='Courier',
        fontSize=8,
        leading=10,
    )

    heading_style = ParagraphStyle(
        name='Heading',
        parent=base_styles['Heading2'],
        spaceAfter=6,
    )

    story = []

    # Front page
    title = f"SECA Processing Report"
    story.append(Paragraph(title, base_styles['Title']))
    story.append(Spacer(1, 4 * mm))
    meta = f"Generated: {datetime.utcnow().isoformat()}Z — Total circuits: {len(errors)}"
    story.append(Paragraph(meta, base_styles['Normal']))
    story.append(Spacer(1, 6 * mm))

    # Simple Table of Contents (list circuit keys)
    story.append(Paragraph("Table of Contents", base_styles['Heading3']))
    toc_items = []
    for i, ck in enumerate(errors.keys(), start=1):
        toc_items.append(Paragraph(f"{i}. {ck}", base_styles['Normal']))
    # Limit TOC length to keep front page concise
    for p in toc_items[:200]:
        story.append(p)

    story.append(PageBreak())

    # Per-circuit detailed sections
    for ck, ed in errors.items():
        if isinstance(ed, dict):
            prod = ed.get('product_name') or ''
            svc = ed.get('service_request_type') or ''
            tb = ed.get('traceback') or '(no traceback)'
        else:
            prod = getattr(ed, 'product_name', '')
            svc = getattr(ed, 'service_request_type', '')
            tb = getattr(ed, 'traceback', '(no traceback)')

        story.append(Paragraph(f"{ck} — {prod} / {svc}", heading_style))
        story.append(Spacer(1, 2 * mm))
        # Full traceback: wrap in <pre> and use code style
        # Escape minimal HTML chars
        tb_safe = str(tb).replace('&', '&amp;').replace('<', '&lt;').replace('>', '&gt;')
        story.append(Paragraph(f"<pre>{tb_safe}</pre>", code_style))
        story.append(Spacer(1, 4 * mm))
        story.append(PageBreak())

    # Developer prompt at end
    if developer_prompt:
        story.append(Paragraph("Amazon Q Developer Prompt", base_styles['Heading2']))
        dp_safe = developer_prompt.replace('&', '&amp;').replace('<', '&lt;').replace('>', '&gt;')
        story.append(Paragraph(f"<pre>{dp_safe}</pre>", code_style))

    doc.build(story)
    return output_path
