from decimal import Decimal as D

from django.test import Client, TestCase
from django.urls import reverse

from dashboard.models import LoftPrice, Product, ProductItem
from dashboard.tests import make_product, make_user

from .models import ShoppingList, ShoppingListItem


class ShoppingListTests(TestCase):
    def setUp(self):
        self.admin = make_user("admin", superuser=True)
        self.sofa = make_product(self.admin, D("100"), D("150"), D("200"))
        self.lamp = make_product(self.admin, D("10"), D("15"), D("30"))
        self.variant = ProductItem.objects.create(product=self.sofa, name="Beige", stock_quantity=5)

    def _add(self, client, product, **extra):
        data = {"product": product.pk, "list": "", "new_list": "Villa Hydra", "room": "Salon", "quantity": 2, **extra}
        return client.post(reverse("shopping:add"), data)

    def _set_price(self, product, retail):
        product.loft_retail_price = retail
        product.save()
        LoftPrice.objects.filter(product=product).update(loft_retail_price=retail)

    def test_visitor_creates_a_list_with_rooms_and_price_snapshot(self):
        r = self._add(self.client, self.sofa, item=self.variant.pk)
        lst = ShoppingList.objects.get()
        self.assertRedirects(r, lst.get_absolute_url())
        item = lst.items.get()
        self.assertEqual((item.room.name, item.quantity, item.price_snapshot), ("Salon", 2, D("200")))
        self.assertEqual(item.variant_id_snapshot, self.variant.variant_id)
        self.assertEqual(item.bpid_snapshot, self.sofa.bpid)

        # Same room name reused, new list not created
        self.client.post(reverse("shopping:add"), {"product": self.lamp.pk, "list": lst.code, "room": "salon", "quantity": 1})
        self.assertEqual(ShoppingList.objects.count(), 1)
        self.assertEqual(lst.rooms.count(), 1)

        # Price change: the snapshot stays, the page shows both prices
        self._set_price(self.sofa, D("260"))
        page = self.client.get(lst.get_absolute_url())
        self.assertContains(page, "260 DZD")
        self.assertContains(page, "200 DZD")
        item.refresh_from_db()
        self.assertEqual(item.price_snapshot, D("200"))

        # The owner accepts today's price explicitly
        self.client.post(reverse("shopping:action", args=[lst.code]), {"action": "refresh_price", "item": item.pk})
        item.refresh_from_db()
        self.assertEqual(item.price_snapshot, D("260"))

    def test_shared_link_reads_and_orders_but_does_not_edit(self):
        self._add(self.client, self.sofa)
        lst = ShoppingList.objects.get()
        other = Client()
        page = other.get(lst.get_absolute_url())
        self.assertEqual(page.status_code, 200)
        self.assertNotContains(page, "update_item")
        r = other.post(reverse("shopping:action", args=[lst.code]), {"action": "delete_list"})
        self.assertEqual(r.status_code, 404)

        # The private edit link gives the right back
        other.get(lst.get_absolute_url() + "?cle=" + lst.edit_key)
        other.post(reverse("shopping:action", args=[lst.code]), {"action": "update_list", "name": "Villa", "budget": "1 000 000"})
        lst.refresh_from_db()
        self.assertEqual((lst.name, lst.budget), ("Villa", D("1000000")))

        # Anyone with the link can put it in their cart
        other.post(reverse("shopping:to_cart", args=[lst.code]))
        cart = other.session["cart"]
        self.assertEqual(cart[str(self.sofa.pk)]["quantity"], 2)

    def test_unavailable_and_refused_lines_are_not_ordered_nor_replaced(self):
        self._add(self.client, self.sofa)
        lst = ShoppingList.objects.get()
        self.client.post(reverse("shopping:add"), {"product": self.lamp.pk, "list": lst.code, "quantity": 1})
        lamp_line = lst.items.get(product=self.lamp)
        lamp_line.status = ShoppingListItem.Status.REFUSED
        lamp_line.save()
        Product.objects.filter(pk=self.sofa.pk).update(is_active=False)

        page = self.client.get(lst.get_absolute_url())
        self.assertContains(page, "sl-bad")
        self.client.post(reverse("shopping:to_cart", args=[lst.code]))
        self.assertEqual(self.client.session.get("cart", {}), {})
        self.assertEqual(lst.items.filter(product=self.sofa).count(), 1)  # still there, untouched

    def test_account_owns_its_lists_print_and_cart_conversion(self):
        user = make_user("client")
        self.client.force_login(user)
        self.client.post(reverse("frontend:cart_add"), {"product_id": self.lamp.pk, "quantity": 3})
        r = self.client.post(reverse("shopping:from_cart"))
        lst = ShoppingList.objects.get()
        self.assertEqual(lst.owner, user)
        self.assertRedirects(r, lst.get_absolute_url())
        self.assertEqual(lst.items.get().quantity, 3)
        self.assertContains(self.client.get(reverse("shopping:index")), lst.code)

        printed = self.client.get(reverse("shopping:print", args=[lst.code]))
        self.assertContains(printed, "<svg")
        self.assertContains(printed, lst.code)
