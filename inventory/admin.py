import csv
from django.contrib import admin
from django.db.models import F, Sum
from django.http import HttpResponse
from django.utils.html import format_html
from .models import Category, Product, Order, OrderItem, StockMovement

admin.site.site_header = 'Airsoft Store - Admin'
admin.site.site_title = 'Airsoft Admin'
admin.site.index_title = 'Store Management'


@admin.register(Category)
class CategoryAdmin(admin.ModelAdmin):
    list_display = ('name', 'slug', 'description_short', 'product_count')
    prepopulated_fields = {'slug': ('name',)}
    search_fields = ('name', 'description')
    ordering = ('name',)

    def product_count(self, obj):
        return format_html('<b>{}</b>', obj.products.count())
    product_count.short_description = 'Products'

    def description_short(self, obj):
        if not obj.description:
            return '-'
        return obj.description[:70] + '...' if len(obj.description) > 70 else obj.description
    description_short.short_description = 'Description'


class StockLevelFilter(admin.SimpleListFilter):
    title = 'Stock Level'
    parameter_name = 'stock_level'

    def lookups(self, request, model_admin):
        return [
            ('out', 'Out of Stock'),
            ('low', 'Low Stock'),
            ('ok',  'In Stock'),
        ]

    def queryset(self, request, queryset):
        if self.value() == 'out':
            return queryset.filter(stock_quantity=0)
        if self.value() == 'low':
            return queryset.filter(stock_quantity__gt=0, stock_quantity__lte=F('low_stock_threshold'))
        if self.value() == 'ok':
            return queryset.filter(stock_quantity__gt=F('low_stock_threshold'))
        return queryset


class StockMovementInline(admin.TabularInline):
    model = StockMovement
    extra = 1
    fields = ('reason', 'quantity_change', 'notes')
    can_delete = False
    verbose_name = 'Stock Adjustment'
    verbose_name_plural = 'Stock Adjustments  (add a new row to adjust stock)'


@admin.register(Product)
class ProductAdmin(admin.ModelAdmin):
    list_display = (
        'thumbnail_list', 'name', 'sku', 'category',
        'price_display', 'stock_badge', 'inventory_value_list', 'is_active', 'delete_link',
    )
    list_filter = ('category', 'is_active', StockLevelFilter)
    search_fields = ('name', 'sku', 'description')
    prepopulated_fields = {'slug': ('name',)}
    list_editable = ('is_active',)
    list_per_page = 20
    ordering = ('name',)
    date_hierarchy = 'created_at'
    readonly_fields = ('created_at', 'updated_at', 'thumbnail_preview', 'inventory_value_detail')
    inlines = [StockMovementInline]
    actions = ['activate_products', 'deactivate_products', 'export_products_csv', 'delete_selected']
    fieldsets = (
        ('Basic Info', {
            'fields': ('name', 'slug', 'sku', 'category', 'description', 'is_active'),
        }),
        ('Pricing & Stock', {
            'fields': ('price', 'inventory_value_detail', 'stock_quantity', 'low_stock_threshold'),
        }),
        ('Image', {
            'fields': ('image', 'image_url', 'thumbnail_preview'),
            'description': 'Upload a file OR paste an external image URL.',
        }),
        ('Timestamps', {
            'fields': ('created_at', 'updated_at'),
            'classes': ('collapse',),
        }),
    )

    def _img_url(self, obj):
        if obj.image:
            try:
                return obj.image.url
            except Exception:
                pass
        return obj.image_url or None

    def thumbnail_list(self, obj):
        url = self._img_url(obj)
        if url:
            return format_html(
                '<img src="{}" style="height:46px;width:46px;object-fit:cover;border-radius:6px;border:1px solid #e5e7eb;" />',
                url,
            )
        return format_html(
            '<div style="height:46px;width:46px;background:#f3f4f6;border-radius:6px;'
            'display:flex;align-items:center;justify-content:center;font-size:20px;">?</div>'
        )
    thumbnail_list.short_description = ''

    def price_display(self, obj):
        return format_html('<b>${}</b>', obj.price)
    price_display.short_description = 'Price'
    price_display.admin_order_field = 'price'

    def stock_badge(self, obj):
        if obj.stock_quantity == 0:
            return format_html(
                '<span style="background:#ef4444;color:#fff;padding:3px 9px;border-radius:12px;font-size:11px;font-weight:600;">OUT</span>'
            )
        if obj.is_low_stock:
            return format_html(
                '<span style="background:#f59e0b;color:#fff;padding:3px 9px;border-radius:12px;font-size:11px;font-weight:600;">LOW: {}</span>',
                obj.stock_quantity,
            )
        return format_html(
            '<span style="background:#22c55e;color:#fff;padding:3px 9px;border-radius:12px;font-size:11px;font-weight:600;">IN: {}</span>',
            obj.stock_quantity,
        )
    stock_badge.short_description = 'Stock'
    stock_badge.admin_order_field = 'stock_quantity'

    def inventory_value_list(self, obj):
        if obj.price is None:
            return '-'
        return format_html('<b>${}</b>', '{:.2f}'.format(obj.price * (obj.stock_quantity or 0)))
    inventory_value_list.short_description = 'Stock Value'

    def thumbnail_preview(self, obj):
        url = self._img_url(obj)
        if url:
            return format_html(
                '<img src="{}" style="max-height:220px;border-radius:8px;border:1px solid #e5e7eb;" />',
                url,
            )
        return '(No image)'
    thumbnail_preview.short_description = 'Preview'

    def inventory_value_detail(self, obj):
        if obj.price is None:
            return '-'
        return format_html('<b>${}</b>  ({} units x ${})', '{:.2f}'.format(obj.price * (obj.stock_quantity or 0)), obj.stock_quantity or 0, obj.price)
    inventory_value_detail.short_description = 'Total Inventory Value'

    def delete_link(self, obj):
        return format_html(
            '<a href="{}/delete/" style="color:#ef4444;font-weight:600;" '
            'onclick="return confirm(\'Delete {}?\')">Delete</a>',
            obj.pk, obj.name,
        )
    delete_link.short_description = ''

    @admin.action(description='Activate selected products')
    def activate_products(self, request, queryset):
        count = queryset.update(is_active=True)
        self.message_user(request, f'{count} product(s) activated.')

    @admin.action(description='Deactivate selected products')
    def deactivate_products(self, request, queryset):
        count = queryset.update(is_active=False)
        self.message_user(request, f'{count} product(s) deactivated.')

    @admin.action(description='Export selected products to CSV')
    def export_products_csv(self, request, queryset):
        response = HttpResponse(content_type='text/csv')
        response['Content-Disposition'] = 'attachment; filename=products.csv'
        writer = csv.writer(response)
        writer.writerow(['Name', 'SKU', 'Category', 'Price', 'Stock', 'Low Stock Threshold', 'Inventory Value', 'Active'])
        for p in queryset.select_related('category'):
            writer.writerow([
                p.name, p.sku,
                p.category.name if p.category else '',
                p.price, p.stock_quantity, p.low_stock_threshold,
                '{:.2f}'.format(p.price * p.stock_quantity),
                p.is_active,
            ])
        return response


_STATUS_COLORS = {
    'pending':   '#6b7280',
    'confirmed': '#3b82f6',
    'shipped':   '#8b5cf6',
    'delivered': '#22c55e',
    'cancelled': '#ef4444',
}


class OrderItemInline(admin.TabularInline):
    model = OrderItem
    extra = 1
    fields = ('product', 'quantity', 'unit_price', 'subtotal_display')
    readonly_fields = ('subtotal_display',)

    def subtotal_display(self, obj):
        if obj.pk:
            return format_html('<b>${}</b>', '{:.2f}'.format(obj.subtotal))
        return '-'
    subtotal_display.short_description = 'Subtotal'


@admin.register(Order)
class OrderAdmin(admin.ModelAdmin):
    list_display = (
        'order_number', 'customer_name', 'customer_email',
        'status_badge', 'item_count', 'total_display', 'created_at',
    )
    list_filter = ('status', 'created_at')
    search_fields = ('customer_name', 'customer_email')
    readonly_fields = ('total_price', 'created_at', 'updated_at')
    inlines = [OrderItemInline]
    list_per_page = 25
    date_hierarchy = 'created_at'
    actions = ['mark_confirmed', 'mark_shipped', 'mark_delivered', 'mark_cancelled', 'export_orders_csv']

    def order_number(self, obj):
        return format_html('<b>#{}</b>', obj.pk)
    order_number.short_description = 'Order'
    order_number.admin_order_field = 'pk'

    def status_badge(self, obj):
        color = _STATUS_COLORS.get(obj.status, '#6b7280')
        return format_html(
            '<span style="background:{};color:#fff;padding:3px 10px;border-radius:12px;font-size:11px;font-weight:600;">{}</span>',
            color, obj.get_status_display(),
        )
    status_badge.short_description = 'Status'
    status_badge.admin_order_field = 'status'

    def item_count(self, obj):
        return obj.items.count()
    item_count.short_description = 'Items'

    def total_display(self, obj):
        if obj.total_price is None:
            return '-'
        return format_html('<b>${}</b>', '{:.2f}'.format(obj.total_price))
    total_display.short_description = 'Total'
    total_display.admin_order_field = 'total_price'

    def save_model(self, request, obj, form, change):
        super().save_model(request, obj, form, change)
        obj.recalculate_total()

    def save_formset(self, request, form, formset, change):
        super().save_formset(request, form, formset, change)
        form.instance.recalculate_total()

    @admin.action(description='Mark as Confirmed')
    def mark_confirmed(self, request, queryset):
        count = queryset.update(status='confirmed')
        self.message_user(request, f'{count} order(s) marked as confirmed.')

    @admin.action(description='Mark as Shipped')
    def mark_shipped(self, request, queryset):
        count = queryset.update(status='shipped')
        self.message_user(request, f'{count} order(s) marked as shipped.')

    @admin.action(description='Mark as Delivered')
    def mark_delivered(self, request, queryset):
        count = queryset.update(status='delivered')
        self.message_user(request, f'{count} order(s) marked as delivered.')

    @admin.action(description='Mark as Cancelled')
    def mark_cancelled(self, request, queryset):
        count = queryset.update(status='cancelled')
        self.message_user(request, f'{count} order(s) marked as cancelled.')

    @admin.action(description='Export selected orders to CSV')
    def export_orders_csv(self, request, queryset):
        response = HttpResponse(content_type='text/csv')
        response['Content-Disposition'] = 'attachment; filename=orders.csv'
        writer = csv.writer(response)
        writer.writerow(['Order #', 'Customer', 'Email', 'Status', 'Items', 'Total', 'Date'])
        for o in queryset.prefetch_related('items'):
            writer.writerow([
                o.pk, o.customer_name, o.customer_email,
                o.get_status_display(), o.items.count(),
                '{:.2f}'.format(o.total_price), o.created_at.strftime('%Y-%m-%d'),
            ])
        return response


_MOVEMENT_COLORS = {
    'purchase':   '#22c55e',
    'return':     '#3b82f6',
    'sale':       '#f59e0b',
    'adjustment': '#6b7280',
    'damage':     '#ef4444',
}


@admin.register(StockMovement)
class StockMovementAdmin(admin.ModelAdmin):
    list_display = ('product', 'reason_badge', 'qty_display', 'current_stock', 'performed_by', 'notes_short', 'created_at')
    list_filter = ('reason', 'created_at', 'product__category')
    search_fields = ('product__name', 'notes', 'performed_by__username')
    readonly_fields = ('created_at', 'performed_by')
    list_per_page = 30
    date_hierarchy = 'created_at'
    fields = ('product', 'reason', 'quantity_change', 'notes', 'performed_by', 'created_at')

    def reason_badge(self, obj):
        color = _MOVEMENT_COLORS.get(obj.reason, '#6b7280')
        return format_html(
            '<span style="background:{};color:#fff;padding:3px 8px;border-radius:12px;font-size:11px;font-weight:600;">{}</span>',
            color, obj.get_reason_display(),
        )
    reason_badge.short_description = 'Reason'
    reason_badge.admin_order_field = 'reason'

    def qty_display(self, obj):
        if obj.quantity_change > 0:
            return format_html('<span style="color:#22c55e;font-weight:bold;">+{}</span>', obj.quantity_change)
        return format_html('<span style="color:#ef4444;font-weight:bold;">{}</span>', obj.quantity_change)
    qty_display.short_description = 'Qty Change'
    qty_display.admin_order_field = 'quantity_change'

    def current_stock(self, obj):
        return format_html('<b>{}</b>', obj.product.stock_quantity)
    current_stock.short_description = 'Current Stock'

    def notes_short(self, obj):
        if not obj.notes:
            return '-'
        return obj.notes[:55] + '...' if len(obj.notes) > 55 else obj.notes
    notes_short.short_description = 'Notes'

    def save_model(self, request, obj, form, change):
        if not change:
            obj.performed_by = request.user
            obj.product.stock_quantity += obj.quantity_change
            obj.product.save(update_fields=['stock_quantity'])
        super().save_model(request, obj, form, change)

    def has_change_permission(self, request, obj=None):
        return False