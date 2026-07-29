from django.contrib import admin

from .models import Category, Order, OrderItem, Product, ProductImage


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
    list_filter = ("category", "is_active", "is_featured", "created_at")
    search_fields = ("name", "slug", "short_description", "material", "color")
    prepopulated_fields = {"slug": ("name",)}
    readonly_fields = ("created_at", "updated_at")
    inlines = [ProductImageInline]


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
