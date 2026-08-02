from uuid import uuid4

from django.contrib import messages
from django.core.exceptions import ValidationError
from django.http import Http404
from django.shortcuts import get_object_or_404, redirect, render
from django.urls import reverse
from django.views.decorators.http import require_http_methods

from .cart import Cart
from .forms import CheckoutForm
from .models import Category, Product
from .services import create_order_from_cart

# Old category slugs kept for backward-compatible redirects after renames.
LEGACY_CATEGORY_SLUGS = {
    "chains": "portefeuilles",
}


def home(request):
    featured_products = Product.objects.filter(
        is_active=True,
        is_featured=True,
        category__is_active=True,
    ).select_related("category")[:6]
    latest_products = Product.objects.filter(
        is_active=True,
        category__is_active=True,
    ).select_related("category")[:8]
    categories = Category.objects.filter(is_active=True)
    return render(
        request,
        "shop/home.html",
        {
            "featured_products": featured_products,
            "latest_products": latest_products,
            "categories": categories,
        },
    )


def product_list(request):
    selected_category = (request.GET.get("category") or "").strip()
    if selected_category in LEGACY_CATEGORY_SLUGS:
        new_slug = LEGACY_CATEGORY_SLUGS[selected_category]
        return redirect(f"{reverse('shop:product_list')}?category={new_slug}", permanent=True)

    categories = Category.objects.filter(is_active=True)
    products = Product.objects.filter(
        is_active=True,
        category__is_active=True,
    ).select_related("category")
    if selected_category:
        products = products.filter(category__slug=selected_category, category__is_active=True)
    return render(
        request,
        "shop/product_list.html",
        {
            "categories": categories,
            "products": products,
            "selected_category": selected_category,
        },
    )


def product_detail(request, slug):
    product = get_object_or_404(
        Product.objects.select_related("category").prefetch_related("images"),
        slug=slug,
        is_active=True,
        category__is_active=True,
    )
    return render(request, "shop/product_detail.html", {"product": product})


@require_http_methods(["GET", "POST"])
def cart_view(request):
    cart = Cart(request)
    if request.method == "POST":
        action = request.POST.get("action")
        product_id = request.POST.get("product_id")
        product = get_object_or_404(Product, id=product_id, is_active=True)
        quantity = request.POST.get("quantity", 1)

        if action == "add":
            if product.stock < 1:
                messages.error(request, "Ce produit est en rupture de stock.")
            else:
                cart.add(product, quantity)
                messages.success(request, "Produit ajoute au panier.")
        elif action == "update":
            cart.update(product, quantity)
            messages.success(request, "Panier mis a jour.")
        elif action == "remove":
            cart.remove(product.id)
            messages.success(request, "Produit retire du panier.")

        return redirect(request.POST.get("next") or "shop:cart")

    return render(request, "shop/cart.html", {"cart": cart, "cart_items": list(cart)})


@require_http_methods(["GET", "POST"])
def checkout(request):
    cart = Cart(request)
    cart_items = list(cart)
    if not cart_items:
        messages.error(request, "Votre panier est vide.")
        return redirect("shop:cart")

    if request.method == "POST":
        form = CheckoutForm(request.POST)
        session_token = request.session.get("checkout_token")
        posted_token = request.POST.get("checkout_token")
        if not session_token or posted_token != session_token:
            messages.error(request, "Cette commande a deja ete traitee ou a expire.")
            return redirect("shop:cart")

        if form.is_valid():
            try:
                order = create_order_from_cart(cart, form.cleaned_data)
            except ValidationError as error:
                form.add_error(None, error)
            else:
                request.session.pop("checkout_token", None)
                request.session["last_order_number"] = order.order_number
                request.session["last_order_summary"] = {
                    "order_number": order.order_number,
                    "items": [
                        {
                            "name": item.product_name,
                            "quantity": item.quantity,
                            "subtotal": str(item.subtotal),
                        }
                        for item in order.items.all()
                    ],
                    "subtotal": str(order.subtotal),
                    "delivery_fee": str(order.delivery_fee),
                    "total": str(order.total),
                }
                cart.clear()
                return redirect("shop:order_success", order_number=order.order_number)
    else:
        token = uuid4().hex
        request.session["checkout_token"] = token
        form = CheckoutForm(initial={"checkout_token": token})

    return render(
        request,
        "shop/checkout.html",
        {"form": form, "cart": cart, "cart_items": cart_items},
    )


def order_success(request, order_number):
    if request.session.get("last_order_number") != order_number:
        raise Http404("Order not found")
    summary = request.session.get("last_order_summary", {})
    return render(request, "shop/order_success.html", {"summary": summary})
