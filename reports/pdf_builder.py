"""
reports/pdf_builder.py
Generates downloadable PDF reports using ReportLab.
"""
from io import BytesIO
from django.http import HttpResponse

try:
    from reportlab.lib.pagesizes import A4, landscape
    from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
    from reportlab.lib.units import cm
    from reportlab.lib import colors
    from reportlab.platypus import (
        SimpleDocTemplate, Paragraph, Spacer, Table, TableStyle, HRFlowable
    )
    from reportlab.lib.enums import TA_CENTER, TA_RIGHT, TA_LEFT
    REPORTLAB_AVAILABLE = True
except ImportError:
    REPORTLAB_AVAILABLE = False


def _get_shop_name():
    try:
        from accounts.utils import get_shop
        shop = get_shop()
        return shop.name if shop else "Ericus Electrical & Home Appliances"
    except Exception:
        return "Ericus Electrical & Home Appliances"


def _base_styles():
    styles = getSampleStyleSheet()
    styles.add(ParagraphStyle(
        'ShopName', parent=styles['Heading1'],
        fontSize=16, alignment=TA_CENTER, spaceAfter=4,
        textColor=colors.HexColor('#0d6efd'),
    ))
    styles.add(ParagraphStyle(
        'ReportTitle', parent=styles['Heading2'],
        fontSize=13, alignment=TA_CENTER, spaceAfter=4,
    ))
    styles.add(ParagraphStyle(
        'SubTitle', parent=styles['Normal'],
        fontSize=9, alignment=TA_CENTER, spaceAfter=12,
        textColor=colors.grey,
    ))
    styles.add(ParagraphStyle(
        'SectionHeader', parent=styles['Heading3'],
        fontSize=11, spaceAfter=6, spaceBefore=12,
        textColor=colors.HexColor('#0d6efd'),
    ))
    styles.add(ParagraphStyle(
        'TableHeader', parent=styles['Normal'],
        fontSize=8, fontName='Helvetica-Bold',
    ))
    styles.add(ParagraphStyle(
        'Cell', parent=styles['Normal'],
        fontSize=8,
    ))
    styles.add(ParagraphStyle(
        'CellRight', parent=styles['Normal'],
        fontSize=8, alignment=TA_RIGHT,
    ))
    return styles


def _header_elements(styles, report_title, date_from=None, date_to=None):
    elements = []
    elements.append(Paragraph(_get_shop_name(), styles['ShopName']))
    elements.append(Paragraph(report_title, styles['ReportTitle']))
    if date_from and date_to:
        elements.append(Paragraph(
            f"Period: {date_from.strftime('%d %b %Y')} — {date_to.strftime('%d %b %Y')}",
            styles['SubTitle']
        ))
    else:
        from datetime import date
        elements.append(Paragraph(
            f"Generated: {date.today().strftime('%d %b %Y')}",
            styles['SubTitle']
        ))
    elements.append(HRFlowable(width='100%', thickness=1, color=colors.HexColor('#0d6efd')))
    elements.append(Spacer(1, 0.3 * cm))
    return elements


def _table_style(header_color=colors.HexColor('#0d6efd')):
    return TableStyle([
        ('BACKGROUND', (0, 0), (-1, 0), header_color),
        ('TEXTCOLOR', (0, 0), (-1, 0), colors.white),
        ('FONTNAME', (0, 0), (-1, 0), 'Helvetica-Bold'),
        ('FONTSIZE', (0, 0), (-1, 0), 8),
        ('FONTSIZE', (0, 1), (-1, -1), 8),
        ('ROWBACKGROUNDS', (0, 1), (-1, -1), [colors.white, colors.HexColor('#f8f9fa')]),
        ('GRID', (0, 0), (-1, -1), 0.25, colors.HexColor('#dee2e6')),
        ('VALIGN', (0, 0), (-1, -1), 'MIDDLE'),
        ('TOPPADDING', (0, 0), (-1, -1), 4),
        ('BOTTOMPADDING', (0, 0), (-1, -1), 4),
        ('LEFTPADDING', (0, 0), (-1, -1), 6),
        ('RIGHTPADDING', (0, 0), (-1, -1), 6),
    ])


def _summary_table(data_pairs, styles):
    """Creates a 2-column key-value summary table."""
    table_data = [[
        Paragraph(str(k), styles['TableHeader']),
        Paragraph(str(v), styles['CellRight'])
    ] for k, v in data_pairs]
    t = Table(table_data, colWidths=[9 * cm, 8 * cm])
    t.setStyle(TableStyle([
        ('GRID', (0, 0), (-1, -1), 0.25, colors.HexColor('#dee2e6')),
        ('ROWBACKGROUNDS', (0, 0), (-1, -1), [colors.white, colors.HexColor('#f8f9fa')]),
        ('TOPPADDING', (0, 0), (-1, -1), 5),
        ('BOTTOMPADDING', (0, 0), (-1, -1), 5),
        ('LEFTPADDING', (0, 0), (-1, -1), 8),
        ('RIGHTPADDING', (0, 0), (-1, -1), 8),
    ]))
    return t


def build_sales_summary_pdf(data):
    if not REPORTLAB_AVAILABLE:
        return None
    buffer = BytesIO()
    doc = SimpleDocTemplate(buffer, pagesize=A4,
                             leftMargin=1.5*cm, rightMargin=1.5*cm,
                             topMargin=1.5*cm, bottomMargin=1.5*cm)
    styles = _base_styles()
    elements = _header_elements(styles, 'Sales Summary Report', data['date_from'], data['date_to'])

    # Summary cards
    elements.append(Paragraph('Summary', styles['SectionHeader']))
    ghs = lambda v: f"GH₵ {v:,.2f}"
    summary_pairs = [
        ('Total Transactions', str(data['total_transactions'])),
        ('Gross Revenue', ghs(data['gross_revenue'])),
        ('Total Discounts Given', ghs(data['total_discounts'] or 0)),
        ('Gross Profit', ghs(data['gross_profit'])),
    ]
    elements.append(_summary_table(summary_pairs, styles))
    elements.append(Spacer(1, 0.4 * cm))

    # Daily breakdown table
    if data.get('daily_breakdown'):
        elements.append(Paragraph('Daily Breakdown', styles['SectionHeader']))
        headers = ['Date', 'Transactions', 'Revenue (GH₵)']
        rows = [headers]
        for row in data['daily_breakdown']:
            rows.append([
                str(row['created_at__date']),
                str(row['count']),
                f"{row['revenue']:,.2f}",
            ])
        t = Table(rows, colWidths=[5*cm, 5*cm, 7*cm])
        t.setStyle(_table_style())
        elements.append(t)

    doc.build(elements)
    buffer.seek(0)
    return buffer


def build_profit_loss_pdf(data):
    if not REPORTLAB_AVAILABLE:
        return None
    buffer = BytesIO()
    doc = SimpleDocTemplate(buffer, pagesize=A4,
                             leftMargin=1.5*cm, rightMargin=1.5*cm,
                             topMargin=1.5*cm, bottomMargin=1.5*cm)
    styles = _base_styles()
    elements = _header_elements(styles, 'Profit & Loss Report', data['date_from'], data['date_to'])
    ghs = lambda v: f"GH₵ {v:,.2f}"

    rows = [
        ['Revenue', ghs(data['revenue'])],
        ['Discounts Given', f"(GH₵ {data['discounts_given']:,.2f})"],
        ['Net Revenue', ghs(data['net_revenue'])],
        ['Cost of Goods Sold (COGS)', f"(GH₵ {data['cogs']:,.2f})"],
        ['Gross Profit', ghs(data['gross_profit'])],
        ['Gross Margin', f"{data['gross_margin_pct']}%"],
        ['Operating Expenses', f"(GH₵ {data['operating_expenses']:,.2f})"],
        ['Net Profit', ghs(data['net_profit'])],
        ['Net Margin', f"{data['net_margin_pct']}%"],
    ]
    t = Table(rows, colWidths=[10*cm, 7*cm])
    t.setStyle(TableStyle([
        ('GRID', (0, 0), (-1, -1), 0.25, colors.HexColor('#dee2e6')),
        ('ROWBACKGROUNDS', (0, 0), (-1, -1), [colors.white, colors.HexColor('#f8f9fa')]),
        ('FONTNAME', (0, 6), (1, 6), 'Helvetica-Bold'),
        ('FONTNAME', (0, 7), (1, 7), 'Helvetica-Bold'),
        ('BACKGROUND', (0, 7), (1, 7), colors.HexColor('#e8f5e9')),
        ('TOPPADDING', (0, 0), (-1, -1), 6),
        ('BOTTOMPADDING', (0, 0), (-1, -1), 6),
        ('LEFTPADDING', (0, 0), (-1, -1), 8),
        ('RIGHTPADDING', (0, 0), (-1, -1), 8),
        ('FONTSIZE', (0, 0), (-1, -1), 9),
    ]))
    elements.append(t)
    doc.build(elements)
    buffer.seek(0)
    return buffer


def build_inventory_pdf(data):
    if not REPORTLAB_AVAILABLE:
        return None
    buffer = BytesIO()
    doc = SimpleDocTemplate(buffer, pagesize=landscape(A4),
                             leftMargin=1.5*cm, rightMargin=1.5*cm,
                             topMargin=1.5*cm, bottomMargin=1.5*cm)
    styles = _base_styles()
    elements = _header_elements(styles, 'Inventory Status Report')

    elements.append(Paragraph(
        f"Total Stock Value: GH₵ {data['total_value']:,.2f} | "
        f"Low Stock Items: {data['low_stock_count']}",
        styles['SubTitle']
    ))
    elements.append(Spacer(1, 0.3 * cm))

    headers = ['Product', 'Category', 'In Stock', 'Reorder Point', 'Status', 'Stock Value (GH₵)']
    rows = [headers]
    for row in data['rows']:
        p = row['product']
        rows.append([
            p.name,
            p.category.name if p.category else '—',
            str(row['current_qty']),
            str(row['reorder_point']),
            'LOW STOCK' if row['is_low'] else 'OK',
            f"{row['stock_value']:,.2f}",
        ])

    col_widths = [7*cm, 4*cm, 2.5*cm, 3*cm, 3*cm, 4*cm]
    t = Table(rows, colWidths=col_widths)
    style = _table_style()
    # Highlight low stock rows in red
    for i, row in enumerate(data['rows'], start=1):
        if row['is_low']:
            style.add('BACKGROUND', (0, i), (-1, i), colors.HexColor('#fff3cd'))
    t.setStyle(style)
    elements.append(t)
    doc.build(elements)
    buffer.seek(0)
    return buffer


def pdf_response(buffer, filename):
    response = HttpResponse(buffer.read(), content_type='application/pdf')
    response['Content-Disposition'] = f'attachment; filename="{filename}"'
    return response