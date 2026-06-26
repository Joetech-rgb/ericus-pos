"""
sales/views.py

POS screen, cart management, checkout, sale history.
"""

from decimal import Decimal

from django.contrib import messages
from django.contrib.auth.decorators import login_required
from django.core.paginator import Paginator
from django.db.models import Q
from django.http import JsonResponse
from django.shortcuts import get_object_or_404, redirect, render
from django.views.decorators.http import require_POST, require_GET

from accounts.decorators import owner_required
from audit.utils import log_sale
from products.models import Product, ProductUnit, Category

from .forms import (
    AddToCartForm, ApplyDiscountForm, CheckoutForm,
    SaleFilterForm, UpdateCartItemForm,
)
from .models import CartSession, Sale, SaleItem
from .utils import (
    build_sale_from_cart, clear_cart, get_cash_position,
    get_daily_summary, get_or_create_cart, get_recent_sales,
)


# ─── POS Screen ───────────────────────────────────────────────────────────────

@login_required
def pos_screen(request):
    """
    Main POS screen. Shows the product search and live cart.
    Cart is loaded from the session.
    """
    cart = get_or_create_cart(request)
    categories = Category.objects.all()

    return render(request, 'sales/pos.html', {
        'cart': cart,
        'categories': categories,
        'checkout_form': CheckoutForm(),
    })


# ─── Product Search (AJAX) ────────────────────────────────────────────────────

@login_required
def product_search(request):
    """
    AJAX endpoint for the live POS search bar.
    Returns matching products as JSON.
    Accepts ?q= (name/brand/barcode/SKU).
    """
    q = request.GET.get('q', '').strip()
    sale_type = request.GET.get('sale_type', 'retail')

    cat_id = request.GET.get('cat', '').strip()

    products = (
        Product.objects
        .select_related('category')
        .prefetch_related('stock_level')
        .filter(is_active=True)
    )
    if q:
        products = products.filter(
            Q(name__icontains=q) |
            Q(brand__icontains=q) |
            Q(barcode__iexact=q) |
            Q(sku__icontains=q) |
            Q(model_number__icontains=q)
        )
    if cat_id:
        products = products.filter(category_id=cat_id)
    if not q and not cat_id:
        pass  # show all when All tab clicked
    products = products[:30]

    results = []
    for p in products:
        try:
            stock = p.stock_level.quantity
        except Exception:
            stock = 0

        price = float(p.wholesale_price if sale_type == 'wholesale' else p.selling_price)

        results.append({
            'id': p.pk,
            'name': p.name,
            'brand': p.brand or '',
            'model': p.model_number or '',
            'sku': p.sku or '',
            'barcode': p.barcode or '',
            'price': price,
            'cost_price': float(p.cost_price),
            'stock': stock,
            'category': p.category.name if p.category else '',
            'image_url': p.image.url if p.image else '',
            'has_serial': p.units.filter(status='in_stock').exists(),
        })

    return JsonResponse({'results': results})


@login_required
def barcode_lookup(request):
    """AJAX — scan a barcode and return the product instantly."""
    barcode = request.GET.get('barcode', '').strip()
    if not barcode:
        return JsonResponse({'found': False})

    try:
        product = Product.objects.get(barcode=barcode, is_active=True)
        try:
            stock = product.stock_level.quantity
        except Exception:
            stock = 0
        return JsonResponse({
            'found': True,
            'id': product.pk,
            'name': product.name,
            'brand': product.brand or '',
            'price': float(product.selling_price),
            'cost_price': float(product.cost_price),
            'stock': stock,
        })
    except Product.DoesNotExist:
        return JsonResponse({'found': False, 'error': 'No product found for this barcode.'})


# ─── Cart Management (AJAX) ───────────────────────────────────────────────────

@login_required
@require_POST
def cart_add(request):
    """Add a product to the cart."""
    form = AddToCartForm(request.POST)
    if not form.is_valid():
        return JsonResponse({'ok': False, 'errors': form.errors}, status=400)

    product = get_object_or_404(Product, pk=form.cleaned_data['product_id'], is_active=True)
    cart = get_or_create_cart(request)

    # Stock check
    try:
        current_stock = product.stock_level.quantity
    except Exception:
        current_stock = 0

    qty = form.cleaned_data['quantity']
    already_in_cart = sum(
        i['quantity'] for i in cart.items_json
        if i['product_id'] == product.pk
    )
    if (already_in_cart + qty) > current_stock:
        return JsonResponse({
            'ok': False,
            'error': f"Only {current_stock} unit(s) in stock. Already {already_in_cart} in cart."
        }, status=400)

    product_unit = None
    if form.cleaned_data.get('product_unit_id'):
        product_unit = get_object_or_404(
            ProductUnit, pk=form.cleaned_data['product_unit_id'],
            product=product, status='in_stock'
        )

    unit_price = form.cleaned_data.get('unit_price') or product.selling_price
    cart.add_item(product, qty, unit_price=unit_price, product_unit=product_unit)

    return JsonResponse({
        'ok': True,
        'cart_count': cart.item_count,
        'cart_total': float(cart.total),
        'subtotal': float(cart.subtotal),
    })


@login_required
@require_POST
def cart_update(request):
    """Update quantity of an item in the cart."""
    form = UpdateCartItemForm(request.POST)
    if not form.is_valid():
        return JsonResponse({'ok': False, 'errors': form.errors}, status=400)

    cart = get_or_create_cart(request)
    cart.update_quantity(
        form.cleaned_data['product_id'],
        form.cleaned_data['quantity'],
        form.cleaned_data.get('product_unit_id'),
    )
    return JsonResponse({
        'ok': True,
        'cart_count': cart.item_count,
        'cart_total': float(cart.total),
    })


@login_required
@require_POST
def cart_remove(request):
    """Remove an item from the cart."""
    product_id = request.POST.get('product_id')
    product_unit_id = request.POST.get('product_unit_id')
    if not product_id:
        return JsonResponse({'ok': False}, status=400)

    cart = get_or_create_cart(request)
    cart.remove_item(
        int(product_id),
        int(product_unit_id) if product_unit_id else None,
    )
    return JsonResponse({
        'ok': True,
        'cart_count': cart.item_count,
        'cart_total': float(cart.total),
    })


@login_required
@require_POST
def cart_clear(request):
    """Clear the entire cart."""
    cart = get_or_create_cart(request)
    cart.clear()
    return JsonResponse({'ok': True})


@login_required
def cart_state(request):
    """Return full cart JSON — called to re-render cart panel."""
    cart = get_or_create_cart(request)
    return JsonResponse({
        'items': cart.items_json,
        'item_count': cart.item_count,
        'subtotal': float(cart.subtotal),
        'discount_amount': float(cart.discount_amount),
        'discount_code': cart.discount_code,
        'installation_fee': float(cart.installation_fee),
        'delivery_fee': float(cart.delivery_fee),
        'total': float(cart.total),
        'customer_id': cart.customer_id,
        'customer_name': str(cart.customer) if cart.customer else '',
        'sale_type': cart.sale_type,
    })


# ─── Discount (AJAX) ─────────────────────────────────────────────────────────

@login_required
@require_POST
def apply_discount(request):
    """Apply a discount code to the cart."""
    form = ApplyDiscountForm(request.POST)
    if not form.is_valid():
        return JsonResponse({'ok': False, 'error': 'Invalid code.'}, status=400)

    from discounts.utils import validate_discount, get_discount_by_code
    cart = get_or_create_cart(request)
    code = form.cleaned_data['code']

    discount = get_discount_by_code(code)
    if not discount:
        return JsonResponse({'ok': False, 'error': 'Discount code not found.'})

    is_valid, error_msg, amount = validate_discount(discount, cart.subtotal, cart.customer)
    if not is_valid:
        return JsonResponse({'ok': False, 'error': error_msg})

    cart.discount = discount
    cart.discount_code = code
    cart.discount_amount = amount
    cart.save(update_fields=['discount', 'discount_code', 'discount_amount'])

    return JsonResponse({
        'ok': True,
        'discount_name': discount.name,
        'discount_amount': float(amount),
        'cart_total': float(cart.total),
        'requires_pin': discount.requires_pin,
    })


@login_required
@require_POST
def remove_discount(request):
    """Remove the applied discount from the cart."""
    cart = get_or_create_cart(request)
    cart.discount = None
    cart.discount_code = ''
    cart.discount_amount = Decimal('0')
    cart.save(update_fields=['discount', 'discount_code', 'discount_amount'])
    return JsonResponse({'ok': True, 'cart_total': float(cart.total)})


# ─── Set Customer on Cart ─────────────────────────────────────────────────────

@login_required
@require_POST
def cart_set_customer(request):
    """Attach or detach a customer to the active cart."""
    from customers.models import Customer
    customer_id = request.POST.get('customer_id')
    cart = get_or_create_cart(request)
    if customer_id:
        customer = get_object_or_404(Customer, pk=customer_id)
        cart.customer = customer
    else:
        cart.customer = None
    cart.save(update_fields=['customer'])
    return JsonResponse({
        'ok': True,
        'customer_name': str(cart.customer) if cart.customer else '',
    })


# ─── Checkout ─────────────────────────────────────────────────────────────────

@login_required
@require_POST
def checkout(request):
    """
    Complete the sale. Called when the cashier confirms payment.
    Builds the Sale, deducts stock, records payment.
    """
    form = CheckoutForm(request.POST)
    cart = get_or_create_cart(request)

    # DEBUG - remove after fix
    import logging
    logger = logging.getLogger(__name__)
    logger.warning(f'CHECKOUT DEBUG: user={request.user}, session={request.session.session_key}, cart_id={cart.pk}, items={len(cart.items_json)}')
    logger.warning(f'CHECKOUT FORM ERRORS: {form.errors if not form.is_valid() else "VALID"}')
    logger.warning(f'CHECKOUT POST DATA: {dict(request.POST)}')

    if not cart.items_json:
        if request.headers.get('X-Requested-With') == 'XMLHttpRequest':
            return JsonResponse({'ok': False, 'error': 'Cart is empty.'}, status=400)
        messages.error(request, "Cart is empty.")
        return redirect('sales:pos')

    # Update cart extras from form before checkout
    if not form.is_valid():
        if request.headers.get('X-Requested-With') == 'XMLHttpRequest':
            return JsonResponse({'ok': False, 'error': 'Invalid form data.', 'errors': form.errors}, status=400)
        messages.error(request, 'Invalid checkout data.')
        return redirect('sales:pos')

    # Update cart extras from form before checkout
    if True:
        cart.installation_fee = form.cleaned_data.get('installation_fee') or Decimal('0')
        cart.delivery_fee = form.cleaned_data.get('delivery_fee') or Decimal('0')
        cart.notes = form.cleaned_data.get('notes') or ''
        cart.save(update_fields=['installation_fee', 'delivery_fee', 'notes'])

        # Attach customer if given
        customer_id = form.cleaned_data.get('customer_id')
        if customer_id:
            from customers.models import Customer
            try:
                cart.customer = Customer.objects.get(pk=customer_id)
                cart.save(update_fields=['customer'])
            except Customer.DoesNotExist:
                pass

        try:
            sale = build_sale_from_cart(
                cart=cart,
                payment_method=form.cleaned_data['payment_method'],
                cash_tendered=form.cleaned_data.get('cash_tendered'),
                momo_amount=form.cleaned_data.get('momo_amount'),
                momo_reference=form.cleaned_data.get('momo_reference', ''),
                credit_due_date=form.cleaned_data.get('credit_due_date'),
                user=request.user,
            )
        except ValueError as e:
            if request.headers.get('X-Requested-With') == 'XMLHttpRequest':
                return JsonResponse({'ok': False, 'error': str(e)}, status=400)
            messages.error(request, str(e))
            return redirect('sales:pos')
        except Exception as e:
            if request.headers.get('X-Requested-With') == 'XMLHttpRequest':
                return JsonResponse({'ok': False, 'error': 'An unexpected error occurred.'}, status=500)
            messages.error(request, f"Checkout failed: {e}")
            return redirect('sales:pos')

        # Clear cart
        clear_cart(request)

        log_sale(
            request.user,
            f"Completed sale {sale.receipt_number} — GH₵{sale.total} via {sale.get_payment_method_display()}",
            request=request,
        )

        if request.headers.get('X-Requested-With') == 'XMLHttpRequest':
            return JsonResponse({
                'ok': True,
                'receipt_url': f"/sales/{sale.pk}/receipt/",
                'receipt_number': sale.receipt_number,
                'total': float(sale.total),
                'change': float(sale.change_given),
            })

        messages.success(request, f"Sale {sale.receipt_number} completed successfully!")
        return redirect('sales:receipt', pk=sale.pk)

    # Form invalid
    if request.headers.get('X-Requested-With') == 'XMLHttpRequest':
        return JsonResponse({'ok': False, 'errors': form.errors}, status=400)
    messages.error(request, "Please fix the errors below.")
    return redirect('sales:pos')


# ─── Receipt ─────────────────────────────────────────────────────────────────

@login_required
def receipt(request, pk):
    """Screen receipt shown after a completed sale."""
    sale = get_object_or_404(Sale, pk=pk)
    items = sale.items.select_related('product')
    payments = sale.payments.all()
    return render(request, 'sales/receipt.html', {
        'sale': sale,
        'items': items,
        'payments': payments,
    })


# ─── Sale History ─────────────────────────────────────────────────────────────

@login_required
def sale_list(request):
    """
    Full sale history.
    Attendants see their own sales only. Owner sees all.
    """
    form = SaleFilterForm(request.GET)
    qs = Sale.objects.select_related('attendant', 'customer').order_by('-created_at')

    if not request.user.is_owner:
        qs = qs.filter(attendant=request.user)

    search = request.GET.get('search', '').strip()
    payment_method = request.GET.get('payment_method', '')
    date_from = request.GET.get('date_from', '')
    date_to = request.GET.get('date_to', '')

    if search:
        qs = qs.filter(
            Q(receipt_number__icontains=search) |
            Q(customer_name__icontains=search) |
            Q(attendant_username__icontains=search)
        )
    if payment_method:
        qs = qs.filter(payment_method=payment_method)
    if date_from:
        qs = qs.filter(created_at__date__gte=date_from)
    if date_to:
        qs = qs.filter(created_at__date__lte=date_to)

    paginator = Paginator(qs, 25)
    page_obj = paginator.get_page(request.GET.get('page'))

    today_summary = get_daily_summary()

    return render(request, 'sales/sale_list.html', {
        'page_obj': page_obj,
        'form': form,
        'today_summary': today_summary,
        'search': search,
        'selected_method': payment_method,
        'date_from': date_from,
        'date_to': date_to,
    })


@login_required
def sale_detail(request, pk):
    """Full detail view for one sale."""
    sale = get_object_or_404(Sale, pk=pk)

    # Attendants can only view their own sales
    if not request.user.is_owner and sale.attendant != request.user:
        messages.error(request, "You can only view your own sales.")
        return redirect('sales:sale_list')

    items = sale.items.select_related('product', 'product_unit')
    payments = sale.payments.all()

    return render(request, 'sales/sale_detail.html', {
        'sale': sale,
        'items': items,
        'payments': payments,
    })


# ─── Serial Number Selector (AJAX) ────────────────────────────────────────────

@login_required
def available_units(request, product_pk):
    """Return available serialised units for a product — for the POS serial picker."""
    product = get_object_or_404(Product, pk=product_pk)
    units = ProductUnit.objects.filter(
        product=product, status='in_stock', condition='new'
    ).values('id', 'serial_number', 'condition')
    return JsonResponse({'units': list(units)})


# ─── Dashboard Widgets (AJAX) ─────────────────────────────────────────────────

@login_required
@owner_required
def dashboard_stats(request):
    """AJAX feed for the owner dashboard stats bar."""
    from django.utils import timezone
    today = timezone.now().date()
    summary = get_daily_summary(today)
    cash_pos = get_cash_position(today)
    return JsonResponse({
        'total_sales': summary['total_sales'],
        'total_revenue': float(summary['total_revenue']),
        'cash_sales': float(summary['cash_sales']),
        'momo_sales': float(summary['momo_sales']),
        'credit_sales': float(summary['credit_sales']),
        'cash_position': float(cash_pos),
    })
