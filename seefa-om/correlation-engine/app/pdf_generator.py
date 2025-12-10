"""
PDF Report Generator for SECA Analysis
Generates formatted PDF with error findings and Amazon Q debug prompts
"""
from typing import Dict, List
from datetime import datetime
from reportlab.lib.pagesizes import letter
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from reportlab.lib.units import inch
from reportlab.platypus import SimpleDocTemplate, Paragraph, Spacer, Table, TableStyle, PageBreak
from reportlab.lib import colors
from reportlab.lib.enums import TA_LEFT, TA_CENTER
import structlog

logger = structlog.get_logger()


class SECAPDFGenerator:
    """Generate PDF reports for SECA error analysis"""

    def __init__(self, output_path: str):
        self.output_path = output_path
        self.doc = SimpleDocTemplate(output_path, pagesize=letter)
        self.styles = getSampleStyleSheet()
        self.story = []

        # Custom styles
        self.title_style = ParagraphStyle(
            'CustomTitle',
            parent=self.styles['Heading1'],
            fontSize=24,
            textColor=colors.HexColor('#FF6B35'),  # Grafana orange
            spaceAfter=30,
            alignment=TA_CENTER
        )

        self.heading_style = ParagraphStyle(
            'CustomHeading',
            parent=self.styles['Heading2'],
            fontSize=16,
            textColor=colors.HexColor('#1F77B4'),  # Grafana blue
            spaceAfter=12,
            spaceBefore=12
        )

        self.code_style = ParagraphStyle(
            'Code',
            parent=self.styles['Code'],
            fontSize=9,
            fontName='Courier',
            textColor=colors.black,
            backColor=colors.HexColor('#F5F5F5'),
            leftIndent=20,
            rightIndent=20,
            spaceAfter=10
        )

    def add_title(self, title: str):
        """Add report title"""
        self.story.append(Paragraph(title, self.title_style))
        self.story.append(Spacer(1, 0.2 * inch))

    def add_metadata(self, total_errors: int, error_groups: int, date: str):
        """Add report metadata"""
        metadata = f"""
        <b>Report Generated:</b> {date}<br/>
        <b>Total Errors:</b> {total_errors}<br/>
        <b>Error Groups:</b> {error_groups}<br/>
        """
        self.story.append(Paragraph(metadata, self.styles['Normal']))
        self.story.append(Spacer(1, 0.3 * inch))

    def add_section(self, title: str):
        """Add section heading"""
        self.story.append(Paragraph(title, self.heading_style))

    def add_error_summary_table(self, error_groups: Dict[str, List[str]]):
        """Add table summarizing error groups"""
        self.add_section("Error Summary by Type")

        # Prepare table data
        data = [['Error Type', 'Count', 'Circuits']]

        for error_type, circuits in sorted(error_groups.items(), key=lambda x: len(x[1]), reverse=True):
            count = len(circuits)
            circuit_list = ', '.join(circuits[:3])  # Show first 3
            if count > 3:
                circuit_list += f' ... (+{count - 3} more)'

            data.append([
                error_type,
                str(count),
                circuit_list
            ])

        # Create table
        table = Table(data, colWidths=[2.5 * inch, 0.8 * inch, 3.2 * inch])
        table.setStyle(TableStyle([
            ('BACKGROUND', (0, 0), (-1, 0), colors.HexColor('#FF6B35')),
            ('TEXTCOLOR', (0, 0), (-1, 0), colors.whitesmoke),
            ('ALIGN', (0, 0), (-1, -1), 'LEFT'),
            ('FONTNAME', (0, 0), (-1, 0), 'Helvetica-Bold'),
            ('FONTSIZE', (0, 0), (-1, 0), 12),
            ('BOTTOMPADDING', (0, 0), (-1, 0), 12),
            ('BACKGROUND', (0, 1), (-1, -1), colors.beige),
            ('GRID', (0, 0), (-1, -1), 1, colors.black),
            ('VALIGN', (0, 0), (-1, -1), 'TOP'),
        ]))

        self.story.append(table)
        self.story.append(Spacer(1, 0.3 * inch))

    def add_traceback(self, circuit_id: str, traceback: str):
        """Add traceback for a specific circuit"""
        self.add_section(f"Circuit: {circuit_id}")

        # Format traceback
        traceback_lines = traceback.split('\n')
        formatted_traceback = '<br/>'.join(traceback_lines)

        self.story.append(Paragraph(formatted_traceback, self.code_style))
        self.story.append(Spacer(1, 0.2 * inch))

    def add_amazon_q_prompt(self, error_type: str, traceback: str, affected_files: List[str]):
        """Generate Amazon Q debug prompt"""
        self.add_section("Amazon Q Debug Prompt")

        prompt = f"""
        <b>Error Type:</b> {error_type}<br/><br/>
        
        <b>Prompt for Amazon Q in VS Code:</b><br/><br/>
        
        <i>I'm debugging a {error_type} error in our MDSO system. Here's the traceback:</i><br/><br/>
        
        <font name="Courier" size="8">{traceback[:500]}...</font><br/><br/>
        
        <i>The error affects these files:</i><br/>
        """

        for file in affected_files[:5]:
            prompt += f"<font name=\"Courier\" size=\"8\">- {file}</font><br/>"

        prompt += """<br/>
        <i>Can you help me:</i><br/>
        1. Identify the root cause<br/>
        2. Suggest a fix<br/>
        3. Recommend preventive measures<br/>
        """

        self.story.append(Paragraph(prompt, self.styles['Normal']))
        self.story.append(Spacer(1, 0.3 * inch))

    def add_page_break(self):
        """Add page break"""
        self.story.append(PageBreak())

    def generate(self):
        """Build and save PDF"""
        logger.info("Generating PDF report", output_path=self.output_path)

        self.doc.build(self.story)

        logger.info("PDF report generated", output_path=self.output_path)
        return self.output_path


def generate_seca_report(
    output_path: str,
    errors: Dict[str, Dict],
    error_groups: Dict[str, List[str]]
) -> str:
    """
    Generate complete SECA PDF report
    
    Args:
        output_path: Path to save PDF
        errors: Dictionary of circuit errors with tracebacks
        error_groups: Dictionary mapping error types to circuit IDs
    
    Returns:
        Path to generated PDF
    """
    generator = SECAPDFGenerator(output_path)

    # Add title
    generator.add_title("SECA Error Analysis Report")

    # Add metadata
    generator.add_metadata(
        total_errors=len(errors),
        error_groups=len(error_groups),
        date=datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    )

    # Add error summary table
    generator.add_error_summary_table(error_groups)

    # Add detailed tracebacks (first 10)
    generator.add_section("Detailed Error Tracebacks")

    count = 0
    for circuit_id, error_data in list(errors.items())[:10]:
        if error_data.get('traceback'):
            generator.add_traceback(circuit_id, error_data['traceback'])

            # Add Amazon Q prompt for first error
            if count == 0:
                generator.add_amazon_q_prompt(
                    error_type=error_data.get('categorized_error', 'Unknown'),
                    traceback=error_data['traceback'],
                    affected_files=error_data.get('affected_files', [])
                )

            count += 1

            if count >= 10:
                break

    # Generate PDF
    return generator.generate()
