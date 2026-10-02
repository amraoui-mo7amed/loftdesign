"""Money flows of the marketplace: commissions, wallets, withdrawals, stock."""
from decimal import Decimal

from django.contrib.auth.models import User
from django.core.files.uploadedfile import SimpleUploadedFile
from django.test import TestCase
from django.urls import reverse

from dashboard.models import LoftPrice, Order, PartnerPrice, Product, SupplierPrice
from dashboard.utils import (
    PricingError,
    credit_wallets_for_order,
    snapshot_order,
    split_from_chain,
    resolve_chain,
)
from user_auth.models import Transaction, UserProfile, Wallet

R = UserProfile.roleChoices
D = Decimal


def make_user(username, role=None, superuser=False, **profile):
    if superuser:
        user = User.objects.create_superuser(username, f"{username}@x.dz", "pw")
    else:
        user = User.objects.create_user(username, f"{username}@x.dz", "pw")
    if role:
        profile.setdefault("is_approved", True)
        UserProfile.objects.create(user=user, role=role, **profile)
    return user


def make_product(owner, purchase, wholesale, retail, aff_wholesale=None, qty=10):
    product = Product.objects.create(
        user=owner, title=f"P{Product.objects.count()}", description="d",
        thumbnail=SimpleUploadedFile("t.jpg", b"x", content_type="image/jpeg"),
        quantity=qty, status=Product.ProductStatus.APPROVED,
        loft_purchase_price=purchase, loft_wholesale_price=wholesale, loft_retail_price=retail,
    )
    LoftPrice.objects.create(product=product, loft_purchase_price=purchase,
                             loft_default_wholesale_price=wholesale, loft_retail_price=retail, is_active=True)
    SupplierPrice.objects.create(product=product, supplier=owner, loft_purchase_price=purchase,
                                 affiliate_wholesale_price=aff_wholesale)
    return product


def order_for(product, price, qty=1, code="", status=Order.OrderStatus.DELIVERED):
    order = Order.objects.create(
        items=[{"product_id": product.pk, "title": product.title, "price": str(price), "quantity": qty}],
        customer_name="c", customer_phone="0", customer_address="", referred_by=code, status=status,
    )
    snapshot_order(order)
    return order


def balance(user):
    return Wallet.objects.get_or_create(user=user)[0].balance


class CommissionTests(TestCase):
    def setUp(self):
        self.admin = make_user("admin", superuser=True)
        self.provider = make_user("prov", R.PROVIDER, commission=D("10"), is_trusted=True)
        self.provider_profile = self.provider.profile
        # purchase 1000, Loft wholesale 1300, retail 1800
        self.product = make_product(self.provider, D("1000"), D("1300"), D("1800"), aff_wholesale=D("1200"))
        self.aff = make_user("aff", R.AFFILIATE, affiliate_code="AFF1")
        self.semi = make_user("semi", R.SEMI_AFFILIATE, affiliate_code="SEMI1",
                              parent_affiliate=self.aff.profile)
        PartnerPrice.objects.create(product=self.product, seller=self.provider, buyer=self.aff,
                                    purchase_price=D("1300"), wholesale_price=D("1500"), retail_price=D("1800"))
        PartnerPrice.objects.create(product=self.product, seller=self.aff, buyer=self.semi,
                                    purchase_price=D("1500"), wholesale_price=D("1800"), retail_price=D("1800"))

    def assert_conserved(self, order, price, qty=1):
        total = sum(D(i["settlement"][k]) for i in order.items
                    for k in ("supplier", "provider", "loft", "affiliate", "semi"))
        self.assertEqual(total, D(price) * qty)

    def test_direct_sale(self):
        order = order_for(self.product, "1800")
        st = order.items[0]["settlement"]
        self.assertEqual(D(st["supplier"]), D("900.00"))   # 1000 - 10 %
        self.assertEqual(D(st["loft"]), D("900.00"))
        self.assert_conserved(order, "1800")

    def test_affiliate_and_semi_shares(self):
        order = order_for(self.product, "1800", qty=2, code="SEMI1")
        st = order.items[0]["settlement"]
        self.assertEqual(D(st["supplier"]), D("1800.00"))
        self.assertEqual(D(st["loft"]), D("800.00"))       # (1300 - 900) x 2
        self.assertEqual(D(st["affiliate"]), D("400.00"))  # (1500 - 1300) x 2
        self.assertEqual(D(st["semi"]), D("600.00"))       # (1800 - 1500) x 2
        self.assert_conserved(order, "1800", 2)

    def test_provider_network(self):
        net_aff = make_user("netaff", R.AFFILIATE, affiliate_code="NET1", created_by=self.provider_profile)
        PartnerPrice.objects.create(product=self.product, seller=self.provider, buyer=net_aff,
                                    purchase_price=D("1200"), wholesale_price=D("1200"), retail_price=D("1700"))
        order = order_for(self.product, "1700", code="NET1")
        st = order.items[0]["settlement"]
        self.assertEqual(D(st["provider"]), D("200.00"))   # 1200 - 1000
        self.assertEqual(D(st["loft"]), D("100.00"))       # commission 10 % of 1000
        self.assertEqual(D(st["affiliate"]), D("500.00"))
        self.assert_conserved(order, "1700")

    def test_blocked_referrer_earns_nothing(self):
        UserProfile.objects.filter(user=self.aff).update(is_blocked=True)
        order = order_for(self.product, "1800", code="AFF1")
        self.assertEqual(D(order.items[0]["settlement"]["affiliate"]), D("0"))

    def test_price_below_purchase_is_rejected(self):
        chain = resolve_chain(self.product, "AFF1")
        with self.assertRaises(PricingError):
            split_from_chain(chain, D("1200"), 1)  # under the affiliate's 1300 purchase price

    def test_credit_is_idempotent_and_per_supplier(self):
        other = make_user("prov2", R.PROVIDER, commission=D("0"))
        other_product = make_product(other, D("500"), D("600"), D("700"))
        order = Order.objects.create(
            items=[
                {"product_id": self.product.pk, "title": "a", "price": "1800", "quantity": 1},
                {"product_id": other_product.pk, "title": "b", "price": "700", "quantity": 1},
            ],
            customer_name="c", customer_phone="0", status=Order.OrderStatus.DELIVERED,
        )
        snapshot_order(order)
        self.assertTrue(credit_wallets_for_order(order))
        self.assertFalse(credit_wallets_for_order(Order.objects.get(pk=order.pk)))
        self.assertEqual(balance(self.provider), D("900.00"))
        self.assertEqual(balance(other), D("500.00"))
        self.assertEqual(balance(self.admin), D("900.00") + D("200.00"))
        self.assertEqual(Transaction.objects.count(), 3)  # Loft share grouped in one line

    def test_snapshot_is_used_after_price_change(self):
        order = order_for(self.product, "1800", code="AFF1")
        PartnerPrice.objects.filter(buyer=self.aff).update(purchase_price=D("1700"))
        credit_wallets_for_order(order)
        self.assertEqual(balance(self.aff), D("500.00"))  # 1800 - 1300 at order time


class StatusAndStockTests(TestCase):
    def setUp(self):
        self.admin = make_user("admin", superuser=True)
        self.product = make_product(self.admin, D("100"), D("150"), D("200"), qty=5)
        self.client.force_login(self.admin)

    def test_cancel_restocks_and_deliver_pays_once(self):
        order = Order.objects.create(
            items=[{"product_id": self.product.pk, "title": "p", "price": "200", "quantity": 2}],
            customer_name="c", customer_phone="0",
        )
        snapshot_order(order)
        Product.objects.filter(pk=self.product.pk).update(quantity=3)
        url = reverse("dash:order_update_status", args=[order.pk])
        r = self.client.post(url, {"status": Order.OrderStatus.CANCELLED})
        self.assertTrue(r.json()["success"])
        self.product.refresh_from_db()
        self.assertEqual(self.product.quantity, 5)
        r = self.client.post(url, {"status": Order.OrderStatus.CANCELLED})
        self.assertFalse(r.json()["success"])
        self.product.refresh_from_db()
        self.assertEqual(self.product.quantity, 5)

        order2 = order_for(self.product, "200", status=Order.OrderStatus.PENDING)
        url2 = reverse("dash:order_update_status", args=[order2.pk])
        self.client.post(url2, {"status": Order.OrderStatus.DELIVERED})
        self.client.post(url2, {"status": Order.OrderStatus.DELIVERED})
        self.assertEqual(balance(self.admin), D("200.00"))


class WithdrawalTests(TestCase):
    def setUp(self):
        self.admin = make_user("admin", superuser=True)
        self.aff = make_user("aff", R.AFFILIATE, affiliate_code="AFF1")
        Wallet.objects.create(user=self.aff, balance=D("1000"))

    def request(self, amount):
        self.client.force_login(self.aff)
        return self.client.post(reverse("dash:wallet_withdraw"), {"amount": amount}).json()

    def test_pending_requests_reserve_the_balance(self):
        self.assertTrue(self.request("700")["success"])
        self.assertFalse(self.request("400")["success"])
        self.assertFalse(self.request("abc")["success"])  # used to crash with a 500
        self.assertFalse(self.request("NaN")["success"])

    def test_cannot_approve_twice(self):
        self.request("700")
        tx = Transaction.objects.get(transaction_type=Transaction.TransactionType.WITHDRAWAL)
        self.client.force_login(self.admin)
        url = reverse("dash:handle_withdrawal", args=[tx.pk])
        self.assertTrue(self.client.post(url, {"action": "approve"}).json()["success"])
        self.assertFalse(self.client.post(url, {"action": "approve"}).json()["success"])
        self.assertEqual(balance(self.aff), D("300.00"))


class AccessTests(TestCase):
    def test_affiliate_cannot_delete_someone_elses_semi(self):
        a1 = make_user("a1", R.AFFILIATE, affiliate_code="A1")
        a2 = make_user("a2", R.AFFILIATE, affiliate_code="A2")
        semi = make_user("s", R.SEMI_AFFILIATE, affiliate_code="S1", parent_affiliate=a2.profile)
        self.client.force_login(a1)
        r = self.client.post(reverse("dash:semi_affiliate_delete", args=[semi.profile.pk]))
        self.assertEqual(r.status_code, 403)
        self.assertTrue(User.objects.filter(pk=semi.pk).exists())

    def test_final_client_cannot_list_semis(self):
        c = make_user("c", R.FINAL_CLIENT)
        self.client.force_login(c)
        self.assertEqual(self.client.get(reverse("dash:semi_affiliate_list")).status_code, 403)

    def test_blocked_user_is_logged_out(self):
        a = make_user("a", R.AFFILIATE, affiliate_code="A9", is_blocked=True)
        self.client.force_login(a)
        r = self.client.get(reverse("dash:semi_affiliate_list"))
        self.assertEqual(r.status_code, 302)

    def test_storefront_filters_do_not_crash(self):
        r = self.client.get(reverse("frontend:product_list") + "?min_price=1&max_price=x&sort=price")
        self.assertEqual(r.status_code, 200)
        r = self.client.get(reverse("frontend:product_list") + "?sort=password")
        self.assertEqual(r.status_code, 200)


class StorefrontPriceTests(TestCase):
    def setUp(self):
        from django.contrib.sessions.middleware import SessionMiddleware
        from django.test import RequestFactory

        self.admin = make_user("admin", superuser=True)
        self.product = make_product(self.admin, D("100"), D("150"), D("200"))
        Product.objects.filter(pk=self.product.pk).update(pro_price=D("170"), price_eur=D("12.50"))
        self.product.refresh_from_db()
        self.rf, self.sessions = RequestFactory(), SessionMiddleware(lambda r: None)

    def req(self, user=None, **meta):
        from django.contrib.auth.models import AnonymousUser
        r = self.rf.get("/", **meta)
        self.sessions.process_request(r)
        r.user = user or AnonymousUser()
        return r

    def test_public_pro_and_euro_prices(self):
        from frontend.pricing import charge_eur, customer_price, visitor_currency

        self.assertEqual(customer_price(self.req(), self.product)["dzd"], D("200"))
        pro = make_user("pro", R.PROFESSIONAL_CLIENT)
        price = customer_price(self.req(pro), self.product)
        self.assertEqual((price["dzd"], price["pro"]), (D("170"), True))
        pending = make_user("pro2", R.PROFESSIONAL_CLIENT, is_approved=False)
        self.assertEqual(customer_price(self.req(pending), self.product)["dzd"], D("200"))

        self.assertEqual(visitor_currency(self.req(HTTP_CF_IPCOUNTRY="FR")), "EUR")
        self.assertEqual(visitor_currency(self.req(HTTP_CF_IPCOUNTRY="DZ")), "DZD")
        self.assertEqual(charge_eur(self.req(HTTP_CF_IPCOUNTRY="FR"), self.product), D("12.50"))
        self.assertIsNone(charge_eur(self.req(HTTP_CF_IPCOUNTRY="DZ"), self.product))

    def test_product_form_rejects_incoherent_prices(self):
        from dashboard.views.products import _parse_pricing

        _p, errors = _parse_pricing({"loft_purchase_price": "100", "loft_wholesale_price": "90",
                                     "loft_retail_price": "80", "pro_price": "500"}, True)
        self.assertEqual(set(errors), {"loft_wholesale_price", "loft_retail_price", "pro_price"})
        p, errors = _parse_pricing({"loft_purchase_price": "100", "loft_wholesale_price": "150",
                                    "loft_retail_price": "200", "pro_price": "170", "price_eur": "12,5"}, True)
        self.assertEqual(errors, {})
        self.assertEqual(p["eur"], D("12.50"))


class BilnovReferentialTests(TestCase):
    def setUp(self):
        from dashboard.models import Category, ProductItem

        self.admin = make_user("admin", superuser=True)
        cat = Category.objects.create(name="Fauteuils", code="FUR")
        self.product = make_product(self.admin, D("100"), D("150"), D("200"))
        self.product.category = cat
        self.product.save()
        self.product.refresh_from_db()
        self.variant = ProductItem.objects.create(product=self.product, name="Beige", sku="NOR-BGE-01", stock_quantity=4)

    def test_bpid_is_assigned_once_and_never_changes(self):
        from dashboard.models import Category

        bpid = self.product.bpid
        self.assertEqual(bpid, f"BPID-{self.product.pk:09d}")
        self.product.category = Category.objects.create(name="Luminaires", code="LGT")
        self.product.title = "Renamed"
        self.product.loft_retail_price = D("250")
        self.product.save()
        self.product.refresh_from_db()
        self.assertEqual(self.product.bpid, bpid)

    def test_variant_ids_follow_the_bpid(self):
        from dashboard.models import ProductItem

        second = ProductItem.objects.create(product=self.product, name="Gris", stock_quantity=1)
        self.assertEqual(self.variant.variant_id, f"{self.product.bpid}-V01")
        self.assertEqual(second.variant_id, f"{self.product.bpid}-V02")
        self.variant.delete()
        third = ProductItem.objects.create(product=self.product, name="Vert", stock_quantity=1)
        self.assertEqual(third.variant_id, f"{self.product.bpid}-V03")

    def test_new_file_creates_a_version(self):
        from dashboard.models import ProductAsset

        for _ in range(2):
            ProductAsset.objects.create(product=self.product, file_format="skp",
                                        file=SimpleUploadedFile("nora.skp", b"x"))
        current = ProductAsset.objects.get(product=self.product, is_current=True)
        self.assertEqual(current.version, 2)
        self.product.refresh_from_db()
        self.assertEqual(self.product.model_version, 2)

    def test_file_metadata_and_bim_block(self):
        import hashlib

        from dashboard.models import ProductAsset

        content = b"ISO-10303-21;"
        asset = ProductAsset.objects.create(
            product=self.product, file_format="ifc", file=SimpleUploadedFile("nora.ifc", content),
            unit="cm", polygon_count=1200, compatibility="IFC 4",
        )
        self.assertEqual(asset.file_size, len(content))
        self.assertEqual(asset.sha256, hashlib.sha256(content).hexdigest())

        data = self.client.get(reverse("catalog:assets", args=[self.product.bpid])).json()
        ifc = next(a for a in data["assets"] if a["format"] == "ifc")
        self.assertEqual((ifc["unit"], ifc["polygons"], ifc["size"], ifc["compatibility"]), ("cm", 1200, len(content), "IFC 4"))
        self.assertEqual(ifc["sha256"], asset.sha256)

        self.product.status = Product.ProductStatus.APPROVED
        self.product.is_active = True
        self.product.save()
        page = self.client.get(reverse("frontend:product_detail", args=[self.product.pk]))
        self.assertContains(page, 'id="bim"')
        self.assertContains(page, self.variant.variant_id)
        self.assertContains(page, asset.file.url)

    def test_catalog_api(self):
        import json

        bpid = self.product.bpid
        data = self.client.get(reverse("catalog:product", args=[bpid])).json()
        self.assertEqual(data["bpid"], bpid)
        self.assertEqual(data["variants"][0]["sku"], "NOR-BGE-01")
        self.assertEqual(data["variants"][0]["variantId"], self.variant.variant_id)
        self.assertEqual(data["ifcPropertySet"]["name"], "Pset_BilnovProduct")
        self.assertEqual(data["ifcPropertySet"]["properties"]["BilnovProductID"], bpid)
        self.assertNotIn("loft_purchase_price", json.dumps(data))
        self.assertEqual(self.client.get(reverse("catalog:product", args=["BPID-000000000"])).status_code, 404)

        found = self.client.get(reverse("catalog:search") + "?q=NOR-BGE-01").json()
        self.assertEqual(found["results"][0]["bpid"], bpid)

        body = {"objects": [
            {"bpid": bpid.lower(), "ifcGuid": "3Hs8JK", "variantId": self.variant.variant_id},
            {"bpid": None, "ifcGuid": "generic"},
            {"bpid": "BPID-999999999", "ifcGuid": "gone"},
        ]}
        r = self.client.post(reverse("catalog:bim_resolve"), json.dumps(body), content_type="application/json").json()
        self.assertEqual([o["status"] for o in r["objects"]], ["identified", "generic", "unknown"])
        self.assertEqual(r["objects"][0]["variantId"], self.variant.variant_id)

        r = self.client.get(reverse("frontend:product_by_bpid", args=[bpid]))
        self.assertRedirects(r, reverse("frontend:product_detail", args=[self.product.pk]), fetch_redirect_response=False)
