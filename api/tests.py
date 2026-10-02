import json
from decimal import Decimal as D

from django.test import Client, TestCase
from django.urls import reverse

from dashboard.models import ProductItem
from dashboard.tests import make_product, make_user
from shopping.models import ShoppingList

from .models import ApiClient


class ApiV1Tests(TestCase):
    def setUp(self):
        self.admin = make_user("admin", superuser=True)
        self.sofa = make_product(self.admin, D("100"), D("150"), D("200"))
        self.sofa.is_active = True
        self.sofa.save()
        self.variant = ProductItem.objects.create(product=self.sofa, name="Beige", stock_quantity=3)
        self.api_client, self.key = ApiClient.create("BILNOV Desktop")
        self.auth = {"HTTP_AUTHORIZATION": f"Bearer {self.key}"}

    def test_catalog_is_public_and_paginated(self):
        r = self.client.get(reverse("api:products") + "?pageSize=1")
        self.assertEqual(r.status_code, 200)
        data = r.json()
        self.assertEqual(data["count"], 1)
        self.assertEqual(data["results"][0]["bpid"], self.sofa.bpid)
        self.assertEqual(r["Access-Control-Allow-Origin"], "*")
        for name in ("product", "variants", "assets", "availability", "price"):
            self.assertEqual(self.client.get(reverse(f"api:{name}", args=[self.sofa.bpid])).status_code, 200, name)
        missing = self.client.get(reverse("api:product", args=["BPID-999999999"]))
        self.assertEqual((missing.status_code, missing.json()), (404, {"error": "not found"}))
        self.assertNotIn("purchase", json.dumps(self.client.get(reverse("api:product", args=[self.sofa.bpid])).json()))

    def test_writes_need_a_valid_key(self):
        url = reverse("api:shopping_lists")
        self.assertEqual(self.client.post(url, "{}", content_type="application/json").status_code, 401)
        bad = {"HTTP_AUTHORIZATION": "Bearer sb_00000000.nope"}
        self.assertEqual(self.client.post(url, "{}", content_type="application/json", **bad).status_code, 401)
        self.api_client.is_active = False
        self.api_client.save()
        self.assertEqual(self.client.post(url, "{}", content_type="application/json", **self.auth).status_code, 401)

    def test_desktop_creates_a_list_then_a_cart_link(self):
        body = {"name": "Villa Hydra", "bilnovProjectId": "PRJ-42", "rooms": [{"name": "Salon", "budget": 500000}],
                "items": [{"bpid": self.sofa.bpid.lower(), "variantId": self.variant.variant_id, "quantity": 2, "room": "Salon"},
                          {"bpid": "BPID-999999999"}]}
        r = self.client.post(reverse("api:shopping_lists"), json.dumps(body), content_type="application/json", **self.auth)
        self.assertEqual(r.status_code, 201)
        data = r.json()
        self.assertEqual(data["rejected"][0]["reason"], "unknown BPID")
        self.assertEqual(data["items"][0]["variantId"], self.variant.variant_id)
        self.assertEqual(data["items"][0]["status"], "proposed_architect")
        self.assertEqual(data["items"][0]["price"]["snapshot"], 200.0)
        self.assertIn("?cle=", data["editUrl"])
        lst = ShoppingList.objects.get(code=data["id"])
        self.assertEqual((lst.bilnov_project_id, lst.rooms.get().budget), ("PRJ-42", D("500000")))

        self.assertEqual(self.client.get(reverse("api:shopping_list", args=[lst.code])).json()["id"], lst.code)

        r = self.client.post(reverse("api:cart_from_list"), json.dumps({"id": lst.code}), content_type="application/json", **self.auth)
        link = r.json()["cartUrl"]
        self.assertEqual(r.json()["total"]["dzd"], 400.0)
        browser = Client()
        browser.get(link.replace("http://testserver", ""))
        self.assertEqual(browser.session["cart"][str(self.variant.pk)]["quantity"], 2)
        self.assertEqual(browser.get(reverse("shopping:cart_link", args=[lst.code]) + "?t=forged").status_code, 404)
