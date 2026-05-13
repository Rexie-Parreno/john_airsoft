from django.contrib import admin
from django.utils.html import format_html
from .models import Category, Product, Order, OrderItem, StockMovement


@admin.register(Category)
class CategoryAdmin(admin.ModelAdmin):
    list_display = ("name", "slug", "product_count")
    prepopulated_fields = {"slug": ("name",)}
    search_fields = ("name",)

    def product_count(self, obj):
        return obj.products.count()
    product_count.short_description = "Products"


class OrderItemInline(admin.TabularInline):
    model = OrderItem
    extra = 1
    fields = ("product", "quantity", "unit_price", "subtotal_display")
    readonly_fields = ("subtotal_display",)

    def subtotal_display(self, obj):
        if obj.pk:
            return f"${obj.subtotal:.2f}"
        return "-"
    subtotal_display.short_description = "Subtotal"


@admin.register(Product)
class ProductAdmin(admin.ModelAdmin):
    list_display = ("name", "sku", "category", "price", "stock_quantity", "stock_status", "is_active")
    list_filter = ("category", "is_active")
    search_fields = ("name", "sku", "description")
    prepopulated_fields = {"slug": ("name",)}
    list_editable = ("price", "stock_quantity", "is_active")
    readonly_fields = ("created_at", "updated_at", "thumbnail_preview")
    fieldsets = (
        ("Basic Info", {"fields": ("name", "slug", "sku", "category", "description", "is_active")}),
        ("Pricing & Stock", {"fields": ("price", "stock_quantity", "low_stock_threshold")}),
        ("Image", {"fields": ("image", "thumbnail_preview")}),
        ("Timestamps", {"fields": ("created_at", "updated_at"), "classes": ("collapse",)}),
    )

    def stock_status(self, obj):
        if obj.stock_quantity == 0:
            return format_html('<span style="color:red;font-weight:bold;">Out of Stock</span>')
        if obj.is_low_stock:
            return format_html('<span style="color:orange;font-weight:bold;">Low Stock ({})</span>', obj.stock_quantity)
        return format_html('<span style="color:green;">In Stock ({})</span>', obj.stock_quantity)
    stock_status.short_description = "Stock Status"

    def thumbnail_preview(self, obj):
        if obj.image:
            return format_html('<img src="{}" style="max-height:100px;" />', obj.image.url)
        return "(No image)"
    thumbnail_preview.short_description = "Preview"


@admin.register(Order)
class OrderAdmin(admin.ModelAdmin):
    list_display = ("id", "customer_name", "customer_email", "status", "total_price", "created_at")
    list_filter = ("status", "created_at")
    search_fields = ("customer_name", "customer_email")
    readonly_fields = ("total_price", "created_at", "updated_at")
    inlines = [OrderItemInline]
    list_per_page = 25

    def save_model(self, request, obj, form, change):
        super().save_model(request, obj, form, change)
        obj.recalculate_total()

    def save_formset(self, request, form, formset, change):
        super().save_formset(request, form, formset, change)
        form.instance.recalculate_total()


@admin.register(StockMovement)
class StockMovementAdmin(admin.ModelAdmin):
    list_display = ("product", "reason", "quantity_change", "performed_by", "created_at")
    list_filter = ("reason", "created_at")
    search_fields = ("product__name", "notes")
    readonly_fields = ("created_at",)

    def save_model(self, request, obj, form, change):
        if not change:
            obj.performed_by = request.user
            obj.product.stock_quantity += obj.quantity_change
            obj.product.save(update_fields=["stock_quantity"])
        super().save_model(request, obj, form, change)

