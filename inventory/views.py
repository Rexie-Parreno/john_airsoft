from django.shortcuts import render, get_object_or_404
from django.db.models import Count, Q
from .models import Category, Product


def home(request):
    categories = Category.objects.annotate(
        product_count=Count('products', filter=Q(products__is_active=True))
    )
    featured_products = Product.objects.filter(is_active=True).select_related('category').order_by('-created_at')[:8]
    return render(request, 'store/home.html', {
        'categories': categories,
        'featured_products': featured_products,
    })


def product_list(request):
    categories = Category.objects.annotate(
        product_count=Count('products', filter=Q(products__is_active=True))
    )
    products = Product.objects.filter(is_active=True).select_related('category')
    category_slug = request.GET.get('category', '').strip()
    search_query = request.GET.get('q', '').strip()
    current_category = None

    if category_slug:
        current_category = get_object_or_404(Category, slug=category_slug)
        products = products.filter(category=current_category)

    if search_query:
        products = products.filter(
            Q(name__icontains=search_query) | Q(description__icontains=search_query) | Q(sku__icontains=search_query)
        )

    return render(request, 'store/products.html', {
        'products': products,
        'categories': categories,
        'current_category': current_category,
        'search_query': search_query,
    })


def product_detail(request, slug):
    product = get_object_or_404(Product, slug=slug, is_active=True)
    related = Product.objects.filter(category=product.category, is_active=True).exclude(pk=product.pk)[:4]
    return render(request, 'store/product_detail.html', {
        'product': product,
        'related': related,
    })

