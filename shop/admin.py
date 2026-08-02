from django.contrib import admin

from .models import Category, Order, OrderItem, Product, ProductImage

admin.site.site_header = "VELQARO Admin"
admin.site.site_title = "VELQARO Admin"
admin.site.index_title = "Gestion de la boutique"


class ProductImageInline(admin.TabularInline):
    model = ProductImage
    extra = 1


@admin.register(Category)
class CategoryAdmin(admin.ModelAdmin):
    list_display = ("name", "slug", "is_active", "created_at")
    list_filter = ("is_active",)
    search_fields = ("name", "slug")
    prepopulated_fields = {"slug": ("name",)}
    readonly_fields = ("created_at",)


def archive_products(modeladmin, request, queryset):
    updated = queryset.update(is_active=False, is_featured=False)
    modeladmin.message_user(request, f"{updated} product(s) archived and hidden from the storefront.")


archive_products.short_description = "Archive selected products (hide from storefront)"


def restore_products(modeladmin, request, queryset):
    updated = queryset.update(is_active=True)
    modeladmin.message_user(request, f"{updated} product(s) restored and visible on the storefront.")


restore_products.short_description = "Restore selected products (show on storefront)"


@admin.register(Product)
class ProductAdmin(admin.ModelAdmin):
    list_display = (
        "name",
        "category",
        "price",
        "stock",
        "is_active",
        "is_featured",
        "created_at",
    )
    list_editable = ("is_active",)
    list_filter = ("category", "is_active", "is_featured", "created_at")
    search_fields = ("name", "slug", "short_description", "material", "color")
    prepopulated_fields = {"slug": ("name",)}
    readonly_fields = ("created_at", "updated_at")
    inlines = [ProductImageInline]
    actions = [archive_products, restore_products]

    def has_delete_permission(self, request, obj=None):
        if obj is not None and obj.order_items.exists():
            return False
        return super().has_delete_permission(request, obj)


class OrderItemInline(admin.TabularInline):
    model = OrderItem
    extra = 0
    readonly_fields = ("product_name", "unit_price", "subtotal")


def mark_as(status):
    def action(modeladmin, request, queryset):
        queryset.update(status=status)

    action.short_description = f"Mark selected orders as {status}"
    action.__name__ = f"mark_as_{status}"
    return action


@admin.register(Order)
class OrderAdmin(admin.ModelAdmin):
    list_display = (
        "order_number",
        "full_name",
        "phone",
        "city",
        "total",
        "status",
        "tracking_number",
        "created_at",
    )
    list_filter = ("status", "city", "created_at")
    search_fields = ("order_number", "full_name", "phone", "city", "tracking_number")
    readonly_fields = ("order_number", "created_at", "updated_at")
    inlines = [OrderItemInline]
    actions = [
        mark_as(Order.Status.CONFIRMED),
        mark_as(Order.Status.PREPARED),
        mark_as(Order.Status.SHIPPED),
        mark_as(Order.Status.DELIVERED),
        mark_as(Order.Status.CANCELLED),
    ]


@admin.register(ProductImage)
class ProductImageAdmin(admin.ModelAdmin):
    list_display = ("product", "alt_text", "created_at")
    search_fields = ("product__name", "alt_text")
    readonly_fields = ("created_at",)


@admin.register(OrderItem)
class OrderItemAdmin(admin.ModelAdmin):
    list_display = ("order", "product_name", "unit_price", "quantity", "subtotal")
    search_fields = ("order__order_number", "product_name")
