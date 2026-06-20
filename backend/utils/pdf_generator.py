import io
import re
from reportlab.lib.pagesizes import letter  # type: ignore
from reportlab.lib import colors  # type: ignore
from reportlab.lib.units import inch  # type: ignore
from reportlab.platypus import SimpleDocTemplate, Paragraph, Spacer, Table, TableStyle, PageBreak, KeepTogether  # type: ignore
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle  # type: ignore
from reportlab.lib.enums import TA_CENTER, TA_LEFT, TA_RIGHT  # type: ignore

def clean_text(text: str) -> str:
    """Converts basic markdown formatting into ReportLab HTML tags."""
    if not text:
        return ""
    # Convert markdown bold to bold HTML tags
    text = re.sub(r"\*\*(.*?)\*\*", r"<b>\1</b>", text)
    text = re.sub(r"\*(.*?)\*", r"<i>\1</i>", text)
    # Replace single newlines with spaces and double newlines with breaks
    text = text.replace("\r\n", "\n").replace("\r", "\n")
    paragraphs_list = text.split("\n\n")
    cleaned_paragraphs = []
    for p in paragraphs_list:
        p_clean = p.replace("\n", " ").strip()
        if p_clean:
            cleaned_paragraphs.append(p_clean)
    return "<br/><br/>".join(cleaned_paragraphs)

def generate_clinical_pdf(
    physician_name: str,
    license_number: str,
    patient_query: str,
    edited_synthesis: str,
    approved_trials: list,
    approved_genomics: list,
    approved_literature: list
) -> bytes:
    """
    Generates a professional PDF report containing the verified clinical matches.
    Returns the PDF content as bytes.
    """
    buffer = io.BytesIO()
    doc = SimpleDocTemplate(
        buffer,
        pagesize=letter,
        rightMargin=54,
        leftMargin=54,
        topMargin=54,
        bottomMargin=54
    )

    styles = getSampleStyleSheet()
    
    # Custom styles to fit dark/sleek theme or medical aesthetic
    title_style = ParagraphStyle(
        'DocTitle',
        parent=styles['Heading1'],
        fontName='Helvetica-Bold',
        fontSize=20,
        leading=24,
        textColor=colors.HexColor('#0f172a'),
        alignment=TA_LEFT,
        spaceAfter=15
    )
    
    section_heading = ParagraphStyle(
        'SectionHeading',
        parent=styles['Heading2'],
        fontName='Helvetica-Bold',
        fontSize=12,
        leading=16,
        textColor=colors.HexColor('#0284c7'),
        spaceBefore=15,
        spaceAfter=8,
        keepWithNext=True
    )
    
    body_style = ParagraphStyle(
        'BodyCustom',
        parent=styles['Normal'],
        fontName='Helvetica',
        fontSize=9.5,
        leading=14,
        textColor=colors.HexColor('#334155'),
        spaceAfter=10
    )

    metadata_label = ParagraphStyle(
        'MetaLabel',
        parent=styles['Normal'],
        fontName='Helvetica-Bold',
        fontSize=9,
        leading=12,
        textColor=colors.HexColor('#475569')
    )

    metadata_value = ParagraphStyle(
        'MetaVal',
        parent=styles['Normal'],
        fontName='Helvetica',
        fontSize=9,
        leading=12,
        textColor=colors.HexColor('#0f172a')
    )

    table_header_style = ParagraphStyle(
        'TableHeader',
        parent=styles['Normal'],
        fontName='Helvetica-Bold',
        fontSize=8.5,
        leading=11,
        textColor=colors.white
    )

    table_body_style = ParagraphStyle(
        'TableBody',
        parent=styles['Normal'],
        fontName='Helvetica',
        fontSize=8,
        leading=11,
        textColor=colors.HexColor('#1e293b')
    )

    story = []

    # 1. Title/Header Banner
    story.append(Paragraph("ClinicaAgent &mdash; Verified Clinical Report", title_style))
    story.append(Spacer(1, 10))

    # 2. Medical / Physician metadata block
    meta_data = [
        [Paragraph("Verified By:", metadata_label), Paragraph(physician_name or "N/A", metadata_value),
         Paragraph("License Number:", metadata_label), Paragraph(license_number or "N/A", metadata_value)],
        [Paragraph("Original Query:", metadata_label), Paragraph(patient_query or "N/A", metadata_value),
         Paragraph("Document Status:", metadata_label), Paragraph("Verified / Clinically Signed Off", metadata_value)]
    ]
    meta_table = Table(meta_data, colWidths=[1.1*inch, 2.4*inch, 1.1*inch, 2.4*inch])
    meta_table.setStyle(TableStyle([
        ('VALIGN', (0,0), (-1,-1), 'TOP'),
        ('TOPPADDING', (0,0), (-1,-1), 4),
        ('BOTTOMPADDING', (0,0), (-1,-1), 4),
        ('BACKGROUND', (0,0), (-1,-1), colors.HexColor('#f8fafc')),
        ('BOX', (0,0), (-1,-1), 0.5, colors.HexColor('#e2e8f0')),
        ('INNERGRID', (0,0), (-1,-1), 0.25, colors.HexColor('#f1f5f9')),
    ]))
    story.append(meta_table)
    story.append(Spacer(1, 15))

    # 3. Clinical Synthesis Report Section
    story.append(Paragraph("Orchestrator Medical Report", section_heading))
    cleaned_synthesis = clean_text(edited_synthesis)
    story.append(Paragraph(cleaned_synthesis, body_style))
    story.append(Spacer(1, 10))

    # 4. Genomic Variations Section
    if approved_genomics:
        story.append(Paragraph("Verified Genomic Variations", section_heading))
        genomic_table_data = [[
            Paragraph("Variant", table_header_style),
            Paragraph("Gene", table_header_style),
            Paragraph("Clinical Significance", table_header_style),
            Paragraph("ClinVar ID / Title", table_header_style)
        ]]
        for g in approved_genomics:
            genomic_table_data.append([
                Paragraph(g.get("variant", "N/A"), table_body_style),
                Paragraph(g.get("gene", "N/A"), table_body_style),
                Paragraph(g.get("clinical_significance", "N/A"), table_body_style),
                Paragraph(f"{g.get('clinvar_id', 'N/A')}<br/>{g.get('title', '')}", table_body_style)
            ])
        gen_table = Table(genomic_table_data, colWidths=[1.2*inch, 1.0*inch, 1.6*inch, 3.2*inch])
        gen_table.setStyle(TableStyle([
            ('BACKGROUND', (0,0), (-1,0), colors.HexColor('#0284c7')),
            ('VALIGN', (0,0), (-1,-1), 'TOP'),
            ('BOTTOMPADDING', (0,0), (-1,-1), 6),
            ('TOPPADDING', (0,0), (-1,-1), 6),
            ('BOX', (0,0), (-1,-1), 0.5, colors.HexColor('#cbd5e1')),
            ('INNERGRID', (0,0), (-1,-1), 0.5, colors.HexColor('#e2e8f0')),
            ('ROWBACKGROUNDS', (0,1), (-1,-1), [colors.white, colors.HexColor('#f8fafc')])
        ]))
        story.append(gen_table)
        story.append(Spacer(1, 15))

    # 5. Clinical Trials Section
    if approved_trials:
        story.append(Paragraph("Verified Matching Clinical Trials", section_heading))
        trials_table_data = [[
            Paragraph("NCT ID / Phase", table_header_style),
            Paragraph("Trial Title / Sponsor", table_header_style),
            Paragraph("Locations / Criteria", table_header_style)
        ]]
        for t in approved_trials:
            locations = ", ".join(t.get("locations", [])) or "N/A"
            criteria = f"Age: {t.get('age_range', 'N/A')} | Sex: {t.get('gender_requirement', 'N/A')}"
            trials_table_data.append([
                Paragraph(f"<b>{t.get('nct_id', 'N/A')}</b><br/>{t.get('phase', 'N/A')}", table_body_style),
                Paragraph(f"<b>{t.get('title', 'N/A')}</b><br/>Sponsor: {t.get('sponsor', 'N/A')}", table_body_style),
                Paragraph(f"<b>Locations:</b> {locations}<br/><b>Eligibility:</b> {criteria}", table_body_style)
            ])
        trials_table = Table(trials_table_data, colWidths=[1.5*inch, 2.7*inch, 2.8*inch])
        trials_table.setStyle(TableStyle([
            ('BACKGROUND', (0,0), (-1,0), colors.HexColor('#0f766e')),
            ('VALIGN', (0,0), (-1,-1), 'TOP'),
            ('BOTTOMPADDING', (0,0), (-1,-1), 6),
            ('TOPPADDING', (0,0), (-1,-1), 6),
            ('BOX', (0,0), (-1,-1), 0.5, colors.HexColor('#cbd5e1')),
            ('INNERGRID', (0,0), (-1,-1), 0.5, colors.HexColor('#e2e8f0')),
            ('ROWBACKGROUNDS', (0,1), (-1,-1), [colors.white, colors.HexColor('#f8fafc')])
        ]))
        story.append(trials_table)
        story.append(Spacer(1, 15))

    # 6. PubMed Articles Section
    if approved_literature:
        story.append(Paragraph("Verified Literature & References", section_heading))
        lit_table_data = [[
            Paragraph("PMID", table_header_style),
            Paragraph("Title", table_header_style),
            Paragraph("Source / Date", table_header_style)
        ]]
        for l in approved_literature:
            lit_table_data.append([
                Paragraph(l.get("pmid", "N/A"), table_body_style),
                Paragraph(l.get("title", "N/A"), table_body_style),
                Paragraph(f"{l.get('journal', 'N/A')} ({l.get('date', 'N/A')})<br/>{l.get('authors', '')}", table_body_style)
            ])
        lit_table = Table(lit_table_data, colWidths=[1.0*inch, 3.5*inch, 2.5*inch])
        lit_table.setStyle(TableStyle([
            ('BACKGROUND', (0,0), (-1,0), colors.HexColor('#475569')),
            ('VALIGN', (0,0), (-1,-1), 'TOP'),
            ('BOTTOMPADDING', (0,0), (-1,-1), 6),
            ('TOPPADDING', (0,0), (-1,-1), 6),
            ('BOX', (0,0), (-1,-1), 0.5, colors.HexColor('#cbd5e1')),
            ('INNERGRID', (0,0), (-1,-1), 0.5, colors.HexColor('#e2e8f0')),
            ('ROWBACKGROUNDS', (0,1), (-1,-1), [colors.white, colors.HexColor('#f8fafc')])
        ]))
        story.append(lit_table)
        story.append(Spacer(1, 20))

    # 7. Signature Block
    sig_block = []
    sig_block.append(Spacer(1, 10))
    sig_data = [
        [Paragraph(f"<b>Physician Signature:</b> ___________________________", metadata_label),
         Paragraph(f"<b>Date:</b> ___________________________", metadata_label)],
        [Paragraph(f"Name: {physician_name or 'N/A'}", metadata_value),
         Paragraph(f"License #: {license_number or 'N/A'}", metadata_value)]
    ]
    sig_table = Table(sig_data, colWidths=[3.5*inch, 3.5*inch])
    sig_table.setStyle(TableStyle([
        ('VALIGN', (0,0), (-1,-1), 'TOP'),
        ('BOTTOMPADDING', (0,0), (-1,-1), 4),
    ]))
    sig_block.append(sig_table)
    
    # Force the signature block to stay together and try to keep it on the same page
    story.append(KeepTogether(sig_block))

    # Build the document
    doc.build(story)
    
    pdf_bytes = buffer.getvalue()
    buffer.close()
    return pdf_bytes
