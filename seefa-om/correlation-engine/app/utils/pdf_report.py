"""
PDF Report Generation for SECA Analysis

Blueprint Section 4.5 Compliance:
- Overview section with statistics
- Per-circuit details with full tracebacks
- Amazon Q Developer-ready prompts per circuit
- Structured output formatting
"""
from reportlab.lib.pagesizes import A4
from reportlab.lib.styles import ParagraphStyle, getSampleStyleSheet
from reportlab.platypus import SimpleDocTemplate, Paragraph, Spacer, PageBreak
from reportlab.lib.units import mm
from reportlab.lib.colors import HexColor
from datetime import datetime
from typing import Dict, List


def generate_amazon_q_prompt(circuit_id: str, error_data: dict) -> str:
    """
    Generate Amazon Q Developer-ready prompt for a circuit

    Blueprint Section 4.5: Format for Amazon Q Developer assistance
    """
    # Extract fields (handle both dict and object)
    if isinstance(error_data, dict):
        traceback = error_data.get('traceback', '(no traceback available)')
        service_request_type = error_data.get('service_request_type', 'Unknown')
        product_name = error_data.get('product_name', 'Unknown')
        error_message = error_data.get('error_message', 'Unknown')
        cdnc_summary = error_data.get('cdnc_summary', 'None')
    else:
        traceback = getattr(error_data, 'traceback', '(no traceback available)')
        service_request_type = getattr(error_data, 'service_request_type', 'Unknown')
        product_name = getattr(error_data, 'product_name', 'Unknown')
        error_message = getattr(error_data, 'error_message', 'Unknown')
        cdnc_summary = getattr(error_data, 'cdnc_summary', 'None')

    # Blueprint Section 4.5: Amazon Q Developer Prompt Template
    prompt = f"""You are assisting with debugging automation fallout for circuit {circuit_id}.

Here is the traceback and context extracted from the Meta Web Tool:

{traceback}

Service request type: {service_request_type}
Product name: {product_name}
Error message: {error_message}
CDNC summary: {cdnc_summary}

Given this, help identify:
- The likely failing component or module
- The most relevant code paths to inspect
- Potential fixes or mitigation steps
"""

    return prompt


def generate_pdf_summary(errors: Dict[str, dict], output_path: str, developer_prompt: str = None) -> str:
    """
    Generate comprehensive PDF summarizing SECA circuit errors

    Blueprint Section 4.5 Compliance:
    - Overview page with statistics
    - Table of contents
    - Per-circuit sections with:
      - Circuit details
      - Full traceback
      - Amazon Q Developer prompt
    - Global developer prompt at end (if provided)

    Args:
        errors: Dictionary of circuit_key -> error data
        output_path: Path to save PDF
        developer_prompt: Optional global developer prompt

    Returns:
        Path to generated PDF
    """
    doc = SimpleDocTemplate(output_path, pagesize=A4, leftMargin=18 * mm, rightMargin=18 * mm)
    base_styles = getSampleStyleSheet()

    # Define custom styles
    code_style = ParagraphStyle(
        name='Code',
        parent=base_styles['Normal'],
        fontName='Courier',
        fontSize=7,
        leading=9,
        leftIndent=10,
        rightIndent=10,
    )

    prompt_style = ParagraphStyle(
        name='Prompt',
        parent=base_styles['Normal'],
        fontName='Courier',
        fontSize=8,
        leading=10,
        leftIndent=10,
        rightIndent=10,
        backColor=HexColor('#F0F0F0'),
    )

    heading_style = ParagraphStyle(
        name='Heading',
        parent=base_styles['Heading2'],
        spaceAfter=6,
    )

    subheading_style = ParagraphStyle(
        name='Subheading',
        parent=base_styles['Heading3'],
        spaceAfter=4,
        textColor=HexColor('#0066CC'),
    )

    story = []

    # ===== OVERVIEW PAGE (Blueprint 4.5) =====
    title = "SECA Processing Report"
    story.append(Paragraph(title, base_styles['Title']))
    story.append(Spacer(1, 6 * mm))

    # Statistics
    timestamp = datetime.utcnow().strftime("%Y-%m-%d %H:%M:%S UTC")
    total_circuits = len(errors)

    # Count circuits by status
    circuits_with_traceback = sum(1 for e in errors.values() if (
        (isinstance(e, dict) and e.get('traceback')) or
        (hasattr(e, 'traceback') and e.traceback)
    ))
    circuits_without_traceback = total_circuits - circuits_with_traceback

    overview_text = f"""<b>Analysis Overview</b>
<br/>
<br/>Timestamp of analysis: {timestamp}
<br/>Total circuits processed: {total_circuits}
<br/>Circuits with traceback: {circuits_with_traceback}
<br/>Circuits without traceback: {circuits_without_traceback}
<br/>
<br/><i>This report contains detailed traceback analysis and Amazon Q Developer prompts
<br/>for each circuit to assist with root cause identification and remediation.</i>
"""
    story.append(Paragraph(overview_text, base_styles['Normal']))
    story.append(Spacer(1, 8 * mm))

    # Table of Contents
    story.append(Paragraph("Table of Contents", base_styles['Heading3']))
    story.append(Spacer(1, 2 * mm))

    toc_items = []
    for i, ck in enumerate(errors.keys(), start=1):
        # Get product name for TOC
        ed = errors[ck]
        prod = (ed.get('product_name') if isinstance(ed, dict) else getattr(ed, 'product_name', '')) or 'Unknown'
        toc_items.append(Paragraph(f"{i}. <b>{ck}</b> — {prod}", base_styles['Normal']))

    # Limit TOC to keep front page readable
    for p in toc_items[:100]:
        story.append(p)

    if len(toc_items) > 100:
        story.append(Paragraph(f"<i>... and {len(toc_items) - 100} more circuits</i>", base_styles['Normal']))

    story.append(PageBreak())

    # ===== PER-CIRCUIT DETAILED SECTIONS (Blueprint 4.5) =====
    for i, (ck, ed) in enumerate(errors.items(), start=1):
        # Extract fields (handle both dict and object)
        if isinstance(ed, dict):
            circuit_id = ed.get('circuit_id', ck)
            product_name = ed.get('product_name', 'Unknown')
            service_request_type = ed.get('service_request_type', 'Unknown')
            error_message = ed.get('error_message', 'Unknown')
            cdnc_summary = ed.get('cdnc_summary', 'None')
            traceback = ed.get('traceback', '(no traceback)')
            affected_files = ed.get('affected_files', [])
        else:
            circuit_id = getattr(ed, 'circuit_id', ck)
            product_name = getattr(ed, 'product_name', 'Unknown')
            service_request_type = getattr(ed, 'service_request_type', 'Unknown')
            error_message = getattr(ed, 'error_message', 'Unknown')
            cdnc_summary = getattr(ed, 'cdnc_summary', 'None')
            traceback = getattr(ed, 'traceback', '(no traceback)')
            affected_files = getattr(ed, 'affected_files', [])

        # Circuit Header
        story.append(Paragraph(f"Circuit {i}/{total_circuits}: {ck}", heading_style))
        story.append(Spacer(1, 2 * mm))

        # Circuit Details
        details = f"""<b>Circuit ID:</b> {circuit_id}
<br/><b>Product Name:</b> {product_name}
<br/><b>Service Request Type:</b> {service_request_type}
<br/><b>Error Message:</b> {error_message}
<br/><b>CDNC Summary:</b> {cdnc_summary}
"""
        story.append(Paragraph(details, base_styles['Normal']))
        story.append(Spacer(1, 4 * mm))

        # Affected Files Section (if available)
        if affected_files and isinstance(affected_files, list):
            story.append(Paragraph("Affected Files:", subheading_style))
            for af in affected_files:
                if isinstance(af, dict):
                    source = af.get('source', 'unknown')
                    log_file = af.get('log_file', 'N/A')
                    status = af.get('selenium_status', 'unknown')
                    file_info = f"• <b>{source}</b>: {log_file} (status: {status})"
                    story.append(Paragraph(file_info, base_styles['Normal']))
            story.append(Spacer(1, 3 * mm))

        # Full Traceback
        story.append(Paragraph("Full Traceback:", subheading_style))
        tb_safe = str(traceback).replace('&', '&amp;').replace('<', '&lt;').replace('>', '&gt;')
        story.append(Paragraph(f"<pre>{tb_safe}</pre>", code_style))
        story.append(Spacer(1, 4 * mm))

        # BLUEPRINT 4.5: Amazon Q Developer Prompt
        story.append(Paragraph("Amazon Q Developer Prompt:", subheading_style))
        story.append(Spacer(1, 2 * mm))

        amazon_q_prompt = generate_amazon_q_prompt(circuit_id, ed)
        prompt_safe = amazon_q_prompt.replace('&', '&amp;').replace('<', '&lt;').replace('>', '&gt;')
        story.append(Paragraph(f"<pre>{prompt_safe}</pre>", prompt_style))

        story.append(Spacer(1, 6 * mm))
        story.append(PageBreak())

    # ===== GLOBAL DEVELOPER PROMPT (if provided) =====
    if developer_prompt:
        story.append(Paragraph("Global Amazon Q Developer Prompt", base_styles['Heading2']))
        story.append(Spacer(1, 4 * mm))

        global_prompt_text = """<i>You can use this global prompt with Amazon Q Developer to get a comprehensive analysis
<br/>of all circuits in this report. Copy the prompt below and paste it into Amazon Q Developer.</i>
"""
        story.append(Paragraph(global_prompt_text, base_styles['Normal']))
        story.append(Spacer(1, 4 * mm))

        dp_safe = developer_prompt.replace('&', '&amp;').replace('<', '&lt;').replace('>', '&gt;')
        story.append(Paragraph(f"<pre>{dp_safe}</pre>", prompt_style))

    # Build PDF
    doc.build(story)
    return output_path
