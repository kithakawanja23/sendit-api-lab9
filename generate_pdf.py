from reportlab.lib.pagesizes import letter
from reportlab.lib import colors
from reportlab.platypus import SimpleDocTemplate, Paragraph, Spacer, Table, TableStyle, HRFlowable, KeepTogether
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle

def generate_report():
    pdf_filename = "SendIt_API_Test_Report.pdf"
    doc = SimpleDocTemplate(
        pdf_filename,
        pagesize=letter,
        rightMargin=40,
        leftMargin=40,
        topMargin=40,
        bottomMargin=40
    )
    
    styles = getSampleStyleSheet()
    
    title_style = ParagraphStyle(
        'DocTitle', parent=styles['Heading1'],
        fontName='Helvetica-Bold', fontSize=20, leading=24,
        textColor=colors.HexColor('#0F172A'), spaceAfter=4
    )
    subtitle_style = ParagraphStyle(
        'DocSubtitle', parent=styles['Normal'],
        fontName='Helvetica', fontSize=11, leading=15,
        textColor=colors.HexColor('#475569'), spaceAfter=15
    )
    h2_style = ParagraphStyle(
        'SectionH2', parent=styles['Heading2'],
        fontName='Helvetica-Bold', fontSize=13, leading=16,
        textColor=colors.HexColor('#1E293B'), spaceBefore=12, spaceAfter=6
    )
    body_style = ParagraphStyle(
        'BodyDark', parent=styles['Normal'],
        fontName='Helvetica', fontSize=9.5, leading=14,
        textColor=colors.HexColor('#334155')
    )
    code_style = ParagraphStyle(
        'CodeStyle', parent=styles['Normal'],
        fontName='Courier', fontSize=8.5, leading=11,
        textColor=colors.HexColor('#0F172A')
    )
    table_text = ParagraphStyle(
        'TableText', parent=styles['Normal'],
        fontName='Helvetica', fontSize=9, leading=12,
        textColor=colors.HexColor('#1E293B')
    )
    table_header = ParagraphStyle(
        'TableHeader', parent=styles['Normal'],
        fontName='Helvetica-Bold', fontSize=9, leading=12,
        textColor=colors.white
    )

    story = []
    story.append(Paragraph("SendIt API — End-to-End Test & Verification Suite", title_style))
    story.append(Paragraph("Interactive Swagger UI Testing Walkthrough, Verification Signals, and RBAC Matrix", subtitle_style))
    story.append(HRFlowable(width="100%", thickness=1.5, color=colors.HexColor('#2563EB'), spaceAfter=15))

    story.append(Paragraph("1. Test Account Credentials & RBAC Matrix", h2_style))
    cred_data = [
        [Paragraph("Role", table_header), Paragraph("Username", table_header), Paragraph("Password", table_header), Paragraph("Access Rights", table_header)],
        [Paragraph("Admin", table_text), Paragraph("admin_user", table_text), Paragraph("AdminPass123!", table_text), Paragraph("Full System Control, Webhook Reg, All Documents", table_text)],
        [Paragraph("Manager", table_text), Paragraph("manager_nyeri", table_text), Paragraph("ManagerPass123!", table_text), Paragraph("Manual Weather Enrichment, Search All Docs", table_text)],
        [Paragraph("Staff", table_text), Paragraph("staff_rider", table_text), Paragraph("StaffPass123!", table_text), Paragraph("Upload Documents, Search Own Documents", table_text)],
    ]
    t_cred = Table(cred_data, colWidths=[65, 85, 95, 287])
    t_cred.setStyle(TableStyle([
        ('BACKGROUND', (0, 0), (-1, 0), colors.HexColor('#1E293B')),
        ('VALIGN', (0, 0), (-1, -1), 'MIDDLE'),
        ('GRID', (0, 0), (-1, -1), 0.5, colors.HexColor('#E2E8F0')),
        ('ROWBACKGROUNDS', (0, 1), (-1, -1), [colors.white, colors.HexColor('#F8FAFC')]),
        ('BOTTOMPADDING', (0, 0), (-1, -1), 6),
        ('TOPPADDING', (0, 0), (-1, -1), 6),
    ]))
    story.append(t_cred)
    story.append(Spacer(1, 15))

    tests = [
        {
            "num": "Test 1", "name": "User Authentication & JWT Authorization",
            "scope": "Verifies bcrypt password checking, token creation, and Swagger UI Bearer header injection.",
            "steps": "1. Open http://localhost:8000/docs\n2. Click green 'Authorize' button\n3. Enter Username: staff_rider, Password: StaffPass123!\n4. Click 'Authorize' and 'Close'",
            "expected_code": "200 OK", "response": '{\n  "access_token": "eyJhbGciOiJIUzI1Ni...",\n  "token_type": "bearer"\n}'
        },
        {
            "num": "Test 2", "name": "Document Upload & Automatic Weather Enrichment",
            "scope": "Verifies rate limiting (10/hr), file disk storage, geocoding, and Open-Meteo weather API fetch.",
            "steps": "1. Expand POST /documents/upload\n2. Attach waybill file (.pdf, .png, or .docx)\n3. Enter city: Nyeri, country: Kenya\n4. Description: 'Waybill for coffee transport'\n5. Click Execute",
            "expected_code": "201 Created", "response": '{\n  "message": "Upload complete",\n  "document_id": 1,\n  "status": "enriched"\n}'
        },
        {
            "num": "Test 3", "name": "Exercise 1 — Multi-Criteria Document Search",
            "scope": "Verifies query filtering (q, city, status, date range) and user data isolation for Staff role.",
            "steps": "1. Expand GET /documents/search\n2. Set q: 'coffee' and city: 'Nyeri'\n3. Click Execute",
            "expected_code": "200 OK", "response": '[\n  {\n    "id": 1,\n    "original_filename": "waybill.pdf",\n    "city": "Nyeri",\n    "status": "enriched",\n    "weather_data": "{\\"temperature\\": 21.5, \\"windspeed\\": 12.3}"\n  }\n]'
        },
        {
            "num": "Test 4", "name": "Exercise 2 — Document Version Control",
            "scope": "Verifies document revision incrementing and automatic toggling of is_latest status flag.",
            "steps": "1. Expand POST /documents/upload/versioned\n2. Select file with SAME filename as Test 2\n3. Set city: 'Nyeri'\n4. Click Execute",
            "expected_code": "200 OK", "response": '{\n  "message": "Version uploaded",\n  "version": 2,\n  "document_id": 2\n}'
        },
        {
            "num": "Test 5", "name": "Exercise 3 & RBAC — Webhook Registration Security",
            "scope": "Verifies Role-Based Access Control blocking non-admin users from registering webhooks.",
            "steps": "1. Expand POST /webhooks/register\n2. Set webhook_url: 'https://webhook.site/test'\n3. Set event_type: 'document.enriched'\n4. Click Execute (while authenticated as staff_rider)",
            "expected_code": "403 Forbidden", "response": '{\n  "detail": "Admin authorization required"\n}'
        }
    ]

    story.append(Paragraph("2. Detailed Interactive Test Execution Suite", h2_style))
    for test in tests:
        test_content = []
        test_content.append(Paragraph(f"{test['num']}: {test['name']}", ParagraphStyle('TH', parent=styles['Heading3'], fontName='Helvetica-Bold', fontSize=11, leading=14, textColor=colors.HexColor('#1E293B'), spaceBefore=8, spaceAfter=4)))
        detail_data = [
            [Paragraph("Scope & Purpose:", table_text), Paragraph(test['scope'], table_text)],
            [Paragraph("Swagger UI Steps:", table_text), Paragraph(test['steps'].replace('\n', ''), table_text)],
            [Paragraph("Expected Status:", table_text), Paragraph(f"{test['expected_code']}", table_text)],
            [Paragraph("Sample Payload:", table_text), Paragraph(test['response'].replace('\n', '').replace(' ', ' '), code_style)],
        ]
        t_detail = Table(detail_data, colWidths=[110, 422])
        t_detail.setStyle(TableStyle([
            ('BACKGROUND', (0, 0), (0, -1), colors.HexColor('#F1F5F9')),
            ('VALIGN', (0, 0), (-1, -1), 'TOP'),
            ('GRID', (0, 0), (-1, -1), 0.5, colors.HexColor('#CBD5E1')),
            ('BOTTOMPADDING', (0, 0), (-1, -1), 5),
            ('TOPPADDING', (0, 0), (-1, -1), 5),
        ]))
        test_content.append(t_detail)
        test_content.append(Spacer(1, 10))
        story.append(KeepTogether(test_content))

    doc.build(story)
    print("SUCCESS: SendIt_API_Test_Report.pdf created!")

if __name__ == "__main__":
    generate_report()