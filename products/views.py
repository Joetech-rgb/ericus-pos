from django.shortcuts import render, redirect, get_object_or_404
from django.contrib.auth.decorators import login_required
from django.contrib import messages
from django.http import JsonResponse
from django.db.models import Q
from django.core.paginator import Paginator
import openpyxl

from .models import Category, Product, ProductUnit
from .forms import ProductForm, CategoryForm, ProductUnitForm, BulkImportForm
from accounts.decorators import owner_required
from audit.utils import log_action


# ─── Product List ─────────────────────────────────────────────────────────────

@login_required
def product_list(request):
    products = Product.objects.select_related('category').filter(is_active=True)

    # Search
    q = request.GET.get('q', '').strip()
    if q:
        products = products.filter(
            Q(name__icontains=q) |
            Q(brand__icontains=q) |
            Q(model_number__icontains=q) |
            Q(barcode__icontains=q) |
            Q(sku__icontains=q)
        )

    # Filter by category
    category_id = request.GET.get('category', '')
    if category_id:
        products = products.filter(category_id=category_id)

    # Filter low stock
    if request.GET.get('low_stock'):
        low_stock_ids = [p.id for p in products if p.is_low_stock]
        products = products.filter(id__in=low_stock_ids)

    # Paginate
    paginator = Paginator(products, 20)
    page      = request.GET.get('page', 1)
    products  = paginator.get_page(page)

    categories = Category.objects.filter(is_active=True)

    return render(request, 'products/product_list.html', {
        'products':   products,
        'categories': categories,
        'q':          q,
    })


# ─── Product Detail ───────────────────────────────────────────────────────────

@login_required
def product_detail(request, product_id):
    product = get_object_or_404(Product, id=product_id)
    units   = product.units.all().order_by('status', '-received_at')
    return render(request, 'products/product_detail.html', {
        'product': product,
        'units':   units,
    })


# ─── Product Create ───────────────────────────────────────────────────────────

@login_required
@owner_required
def product_create(request):
    form = ProductForm(request.POST or None, request.FILES or None)

    if request.method == 'POST':
        if form.is_valid():
            product = form.save(commit=False)
            product.created_by = request.user
            product.save()
            log_action(request.user, 'CREATE', 'Product', product.id,
                       f'Created product: {product}')
            messages.success(request, f'Product "{product}" added successfully.')
            return redirect('product_detail', product_id=product.id)

    return render(request, 'products/product_form.html', {
        'form':       form,
        'title':      'Add New Product',
        'categories': Category.objects.filter(is_active=True).order_by('name'),  # ✅ FIXED
    })


# ─── Product Edit ─────────────────────────────────────────────────────────────

@login_required
@owner_required
def product_edit(request, product_id):
    product = get_object_or_404(Product, id=product_id)
    form    = ProductForm(request.POST or None, request.FILES or None, instance=product)

    if request.method == 'POST':
        if form.is_valid():
            form.save()
            log_action(request.user, 'UPDATE', 'Product', product.id,
                       f'Updated product: {product}')
            messages.success(request, f'Product "{product}" updated.')
            return redirect('product_detail', product_id=product.id)

    return render(request, 'products/product_form.html', {
        'form':       form,
        'product':    product,
        'title':      f'Edit — {product}',
        'categories': Category.objects.filter(is_active=True).order_by('name'),  # ✅ FIXED
    })


# ─── Product Deactivate ───────────────────────────────────────────────────────

@login_required
@owner_required
def product_deactivate(request, product_id):
    product            = get_object_or_404(Product, id=product_id)
    product.is_active  = False
    product.save(update_fields=['is_active'])
    log_action(request.user, 'DELETE', 'Product', product.id,
               f'Deactivated product: {product}')
    messages.warning(request, f'"{product}" has been deactivated.')
    return redirect('product_list')


# ─── Barcode / SKU Lookup (Used by POS) ──────────────────────────────────────

@login_required
def barcode_lookup(request):
    """
    AJAX endpoint — POS calls this when attendant scans a barcode.
    Returns product info as JSON.
    """
    code    = request.GET.get('code', '').strip()
    product = Product.objects.filter(
        Q(barcode=code) | Q(sku=code), is_active=True
    ).first()

    if not product:
        return JsonResponse({'found': False, 'message': 'Product not found.'})

    return JsonResponse({
        'found':         True,
        'id':            product.id,
        'name':          str(product),
        'selling_price': str(product.selling_price),
        'stock':         product.current_stock,
        'track_serials': product.track_serials,
        'image':         product.image.url if product.image else None,
    })


# ─── Product Search (AJAX for POS) ───────────────────────────────────────────

@login_required
def product_search(request):
    """
    AJAX product search for POS screen.
    Returns list of matching products as JSON.
    """
    q        = request.GET.get('q', '').strip()
    results  = []

    if len(q) >= 2:
        products = Product.objects.filter(
            Q(name__icontains=q) |
            Q(brand__icontains=q) |
            Q(model_number__icontains=q) |
            Q(barcode__icontains=q) |
            Q(sku__icontains=q),
            is_active=True
        ).select_related('category')[:10]

        for p in products:
            results.append({
                'id':            p.id,
                'name':          str(p),
                'category':      p.category.name,
                'selling_price': str(p.selling_price),
                'stock':         p.current_stock,
                'track_serials': p.track_serials,
                'image':         p.image.url if p.image else None,
            })

    return JsonResponse({'results': results})


# ─── Category CRUD ────────────────────────────────────────────────────────────

@login_required
@owner_required
def category_list(request):
    categories = Category.objects.all().order_by('name')
    return render(request, 'products/category_list.html', {'categories': categories})


@login_required
@owner_required
def category_create(request):
    form = CategoryForm(request.POST or None)
    if request.method == 'POST' and form.is_valid():
        cat = form.save()
        log_action(request.user, 'CREATE', 'Category', cat.id, f'Created category: {cat.name}')
        messages.success(request, f'Category "{cat.name}" created.')
        return redirect('category_list')
    return render(request, 'products/category_form.html', {'form': form, 'title': 'Add Category'})


@login_required
@owner_required
def category_edit(request, category_id):
    cat  = get_object_or_404(Category, id=category_id)
    form = CategoryForm(request.POST or None, instance=cat)
    if request.method == 'POST' and form.is_valid():
        form.save()
        log_action(request.user, 'UPDATE', 'Category', cat.id, f'Updated category: {cat.name}')
        messages.success(request, f'Category "{cat.name}" updated.')
        return redirect('category_list')
    return render(request, 'products/category_form.html', {
        'form': form, 'title': f'Edit — {cat.name}'
    })


# ─── Product Unit Management ──────────────────────────────────────────────────

@login_required
@owner_required
def add_unit(request, product_id):
    """Add a single unit / serial number to a product."""
    product = get_object_or_404(Product, id=product_id)
    form    = ProductUnitForm(request.POST or None, product=product)  # ✅ pass product

    if request.method == 'POST' and form.is_valid():
        unit         = form.save(commit=False)
        unit.product = product
        unit.added_by = request.user
        unit.save()

        # Log stock movement
        from inventory.utils import record_movement
        record_movement(
            product=product,
            movement_type='purchase',
            quantity=1,
            user=request.user,
            note=f'Unit added: {unit.serial_number or "no serial"}',
        )

        log_action(request.user, 'CREATE', 'ProductUnit', unit.id,
                   f'Added unit to {product}: {unit.serial_number or "no serial"}')
        messages.success(request, 'Unit added successfully.')
        return redirect('product_detail', product_id=product.id)

    return render(request, 'products/unit_form.html', {
        'form': form, 'product': product, 'title': 'Add Unit'
    })


@login_required
@owner_required
def convert_to_demo(request, unit_id):
    """Convert a sellable unit to a demo/floor unit. Requires owner."""
    unit = get_object_or_404(ProductUnit, id=unit_id)
    unit.convert_to_demo()
    log_action(request.user, 'UPDATE', 'ProductUnit', unit.id,
               f'Converted to demo: {unit.product} — {unit.serial_number}')
    messages.info(request, f'Unit converted to demo unit.')
    return redirect('product_detail', product_id=unit.product.id)


@login_required
@owner_required
def convert_to_sellable(request, unit_id):
    """Convert a demo unit back to sellable stock."""
    unit = get_object_or_404(ProductUnit, id=unit_id)
    unit.convert_to_sellable()
    log_action(request.user, 'UPDATE', 'ProductUnit', unit.id,
               f'Converted demo to sellable: {unit.product} — {unit.serial_number}')
    messages.success(request, 'Unit converted to sellable stock.')
    return redirect('product_detail', product_id=unit.product.id)


# ─── Bulk Import via Excel ────────────────────────────────────────────────────

@login_required
@owner_required
def bulk_import(request):
    form = BulkImportForm(request.POST or None, request.FILES or None)

    if request.method == 'POST' and form.is_valid():
        excel_file = request.FILES['file']
        try:
            wb      = openpyxl.load_workbook(excel_file)
            ws      = wb.active
            created = 0
            errors  = []

            for row_num, row in enumerate(ws.iter_rows(min_row=2, values_only=True), start=2):
                try:
                    name, category_name, brand, model_no, barcode, sku, \
                    cost_price, selling_price, wholesale_price, \
                    warranty_months, reorder_point = row[:11]

                    if not name or not category_name:
                        continue

                    category, _ = Category.objects.get_or_create(name=str(category_name).strip())

                    Product.objects.update_or_create(
                        name=str(name).strip(),
                        defaults={
                            'category':        category,
                            'brand':           str(brand or '').strip(),
                            'model_number':    str(model_no or '').strip(),
                            'barcode':         str(barcode or '').strip() or None,
                            'sku':             str(sku or '').strip() or None,
                            'cost_price':      cost_price or 0,
                            'selling_price':   selling_price or 0,
                            'wholesale_price': wholesale_price or 0,
                            'warranty_months': int(warranty_months or 0),
                            'reorder_point':   int(reorder_point or 5),
                            'created_by':      request.user,
                        }
                    )
                    created += 1
                except Exception as e:
                    errors.append(f'Row {row_num}: {str(e)}')

            log_action(request.user, 'BULK_IMPORT', 'Product', 0,
                       f'Bulk imported {created} products')

            if errors:
                messages.warning(request, f'{created} products imported. {len(errors)} rows had errors.')
            else:
                messages.success(request, f'{created} products imported successfully.')

            return redirect('product_list')

        except Exception as e:
            messages.error(request, f'Failed to read file: {str(e)}')

    return render(request, 'products/bulk_import.html', {'form': form})