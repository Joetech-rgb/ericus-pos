"""
sales/pdf_builder.py

Generates PDF receipts, warranty cards, and wholesale invoices
using ReportLab.

Usage:
    from sales.pdf_builder import build_receipt_pdf, build_invoice_pdf
    response = build_receipt_pdf(sale)   # returns HttpResponse with PDF
"""

from io import BytesIO
from decimal import Decimal

from django.http import HttpResponse
from django.utils import timezone


def _get_shop():
    """Safely fetch ShopProfile."""
    try:
        from accounts.models import ShopProfile
        return ShopProfile.objects.first()
    except Exception:
        return None


def build_receipt_pdf(sale):
    """
    Generate a PDF receipt for a completed sale.
    Returns an HttpResponse with content_type='application/pdf'.
    """
    try:
        from reportlab.lib.pagesizes import A5
        from reportlab.lib.units import mm
        from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
        from reportlab.lib.enums import TA_CENTER, TA_RIGHT, TA_LEFT
        from reportlab.platypus import (
            SimpleDocTemplate, Paragraph, Spacer, Table, TableStyle, HRFlowable
        )
        from reportlab.lib import colors
    except ImportError:
        return HttpResponse(
            "ReportLab is not installed. Run: pip install reportlab",
            status=500
        )

    buffer = BytesIO()
    shop = _get_shop()

    doc = SimpleDocTemplate(
        buffer,
        pagesize=A5,
        topMargin=10 * mm,
        bottomMargin=10 * mm,
        leftMargin=12 * mm,
        rightMargin=12 * mm,
    )

    styles = getSampleStyleSheet()
    center = ParagraphStyle('center', parent=styles['Normal'], alignment=TA_CENTER)
    right = ParagraphStyle('right', parent=styles['Normal'], alignment=TA_RIGHT)
    bold_center = ParagraphStyle('bold_center', parent=center, fontName='Helvetica-Bold', fontSize=12)
    small = ParagraphStyle('small', parent=styles['Normal'], fontSize=8)
    small_center = ParagraphStyle('small_center', parent=small, alignment=TA_CENTER)

    story = []

    # ── Header ────────────────────────────────────────────────────────────────
    shop_name = shop.name if shop else "Ericus Electrical & Home Appliances"
    story.append(Paragraph(shop_name, bold_center))
    if shop and shop.address:
        story.append(Paragraph(shop.address, small_center))
    if shop and shop.phone:
        story.append(Paragraph(f"Tel: {shop.phone}", small_center))
    story.append(Spacer(1, 4 * mm))
    story.append(HRFlowable(width="100%", thickness=1))
    story.append(Spacer(1, 2 * mm))

    # ── Receipt info ──────────────────────────────────────────────────────────
    story.append(Paragraph(f"<b>Receipt: {sale.receipt_number}</b>", center))
    story.append(Paragraph(
        f"Date: {sale.created_at.strftime('%d %b %Y  %H:%M')}",
        small_center
    ))
    story.append(Paragraph(f"Attendant: {sale.attendant_username}", small_center))
    if sale.customer_name:
        story.append(Paragraph(f"Customer: {sale.customer_name}", small_center))
    story.append(Spacer(1, 3 * mm))
    story.append(HRFlowable(width="100%", thickness=0.5))
    story.append(Spacer(1, 2 * mm))

    # ── Items table ───────────────────────────────────────────────────────────
    items = sale.items.all()
    data = [['Item', 'Qty', 'Unit Price', 'Total']]
    for item in items:
        data.append([
            Paragraph(f"{item.product_name}<br/><font size=7>{item.serial_number}</font>",
                      styles['Normal']),
            str(item.quantity),
            f"GH₵{item.unit_price:,.2f}",
            f"GH₵{item.subtotal:,.2f}",
        ])

    item_table = Table(data, colWidths=[70 * mm, 12 * mm, 28 * mm, 28 * mm])
    item_table.setStyle(TableStyle([
        ('FONTNAME', (0, 0), (-1, 0), 'Helvetica-Bold'),
        ('FONTSIZE', (0, 0), (-1, -1), 8),
        ('ALIGN', (1, 0), (-1, -1), 'RIGHT'),
        ('LINEBELOW', (0, 0), (-1, 0), 0.5, colors.black),
        ('ROWBACKGROUNDS', (0, 1), (-1, -1), [colors.white, colors.HexColor('#f5f5f5')]),
        ('TOPPADDING', (0, 0), (-1, -1), 2),
        ('BOTTOMPADDING', (0, 0), (-1, -1), 2),
    ]))
    story.append(item_table)
    story.append(Spacer(1, 2 * mm))
    story.append(HRFlowable(width="100%", thickness=0.5))

    # ── Totals ────────────────────────────────────────────────────────────────
    totals_data = []
    if sale.discount_amount:
        totals_data.append(['Subtotal:', f"GH₵{sale.subtotal:,.2f}"])
        totals_data.append([f'Discount ({sale.discount_code_used}):', f"- GH₵{sale.discount_amount:,.2f}"])
    if sale.installation_fee:
        totals_data.append(['Installation Fee:', f"GH₵{sale.installation_fee:,.2f}"])
    if sale.delivery_fee:
        totals_data.append(['Delivery Fee:', f"GH₵{sale.delivery_fee:,.2f}"])
    totals_data.append(['TOTAL:', f"GH₵{sale.total:,.2f}"])
    if sale.payment_method != 'credit':
        totals_data.append([f'Paid ({sale.get_payment_method_display()}):', f"GH₵{sale.amount_paid:,.2f}"])
    if sale.change_given:
        totals_data.append(['Change:', f"GH₵{sale.change_given:,.2f}"])
    if sale.is_credit:
        totals_data.append(['Balance Due:', f"GH₵{sale.balance_due:,.2f}"])
        if sale.credit_due_date:
            totals_data.append(['Due Date:', sale.credit_due_date.strftime('%d %b %Y')])

    totals_table = Table(totals_data, colWidths=[100 * mm, 38 * mm])
    totals_style = [
        ('FONTSIZE', (0, 0), (-1, -1), 8),
        ('ALIGN', (1, 0), (-1, -1), 'RIGHT'),
        ('TOPPADDING', (0, 0), (-1, -1), 1),
        ('BOTTOMPADDING', (0, 0), (-1, -1), 1),
    ]
    # Bold the TOTAL row
    total_row = next(i for i, r in enumerate(totals_data) if r[0] == 'TOTAL:')
    totals_style.append(('FONTNAME', (0, total_row), (-1, total_row), 'Helvetica-Bold'))
    totals_style.append(('FONTSIZE', (0, total_row), (-1, total_row), 10))
    totals_table.setStyle(TableStyle(totals_style))
    story.append(totals_table)

    # ── Footer ────────────────────────────────────────────────────────────────
    story.append(Spacer(1, 4 * mm))
    story.append(HRFlowable(width="100%", thickness=0.5))
    story.append(Spacer(1, 2 * mm))
    story.append(Paragraph("Thank you for shopping with us!", small_center))
    if shop and shop.whatsapp:
        story.append(Paragraph(f"WhatsApp: {shop.whatsapp}", small_center))

    doc.build(story)

    buffer.seek(0)
    response = HttpResponse(buffer, content_type='application/pdf')
    response['Content-Disposition'] = (
        f'filename="receipt_{sale.receipt_number}.pdf"'
    )
    return response


def build_warranty_card_pdf(sale_item):
    """
    Generate a warranty card PDF for a single sale item.
    """
    try:
        from reportlab.lib.pagesizes import A6
        from reportlab.lib.units import mm
        from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
        from reportlab.lib.enums import TA_CENTER
        from reportlab.platypus import SimpleDocTemplate, Paragraph, Spacer, HRFlowable
        from reportlab.lib import colors
    except ImportError:
        return HttpResponse("ReportLab not installed.", status=500)

    buffer = BytesIO()
    shop = _get_shop()

    doc = SimpleDocTemplate(buffer, pagesize=A6,
                             topMargin=8 * mm, bottomMargin=8 * mm,
                             leftMargin=10 * mm, rightMargin=10 * mm)

    styles = getSampleStyleSheet()
    center = ParagraphStyle('c', parent=styles['Normal'], alignment=TA_CENTER)
    bold_center = ParagraphStyle('bc', parent=center, fontName='Helvetica-Bold', fontSize=11)
    small_center = ParagraphStyle('sc', parent=center, fontSize=8)

    story = [
        Paragraph("WARRANTY CARD", bold_center),
        Paragraph(shop.name if shop else "Ericus Electrical", small_center),
        Spacer(1, 3 * mm),
        HRFlowable(width="100%"),
        Spacer(1, 3 * mm),
        Paragraph(f"<b>Product:</b> {sale_item.product_name}", styles['Normal']),
        Paragraph(f"<b>Brand:</b> {sale_item.product_brand}", styles['Normal']),
        Paragraph(f"<b>Model:</b> {sale_item.product_model}", styles['Normal']),
        Paragraph(f"<b>Serial No:</b> {sale_item.serial_number or 'N/A'}", styles['Normal']),
        Spacer(1, 2 * mm),
        Paragraph(
            f"<b>Warranty Period:</b> {sale_item.product.warranty_display}",
            styles['Normal']
        ),
        Paragraph(
            f"<b>Purchase Date:</b> {sale_item.sale.created_at.strftime('%d %b %Y')}",
            styles['Normal']
        ),
        Paragraph(
            f"<b>Receipt No:</b> {sale_item.sale.receipt_number}",
            styles['Normal']
        ),
        Spacer(1, 3 * mm),
        HRFlowable(width="100%"),
        Spacer(1, 2 * mm),
        Paragraph("Keep this card — required for warranty claims.", small_center),
        Paragraph(shop.phone if shop else "", small_center),
    ]

    doc.build(story)
    buffer.seek(0)
    response = HttpResponse(buffer, content_type='application/pdf')
    response['Content-Disposition'] = (
        f'filename="warranty_{sale_item.serial_number or sale_item.pk}.pdf"'
    )
    return response