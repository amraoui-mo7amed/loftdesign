/* Euro prices for visitors outside Algeria.
   The server decides when it knows the country (CDN header, cookie, ?devise=).
   Otherwise the browser time zone decides once and the choice is kept in the
   store_devise cookie, so carts and orders use the same currency. */
(function () {
  var store = window.STORE || { currency: "DZD", i18n: {} };
  var currency = store.currency;
  if (currency === "auto") {
    var tz = "";
    try { tz = Intl.DateTimeFormat().resolvedOptions().timeZone || ""; } catch (e) {}
    // Only a real foreign time zone switches to euros; UTC / unknown stays in dinars.
    currency = (/^(Europe|America|Asia|Australia|Pacific|Atlantic|Indian)\//.test(tz)) ? "EUR" : "DZD";
    document.cookie = "store_devise=" + currency.toLowerCase() + ";path=/;max-age=31536000;samesite=lax";
  }
  window.STORE.currency = currency;

  function apply() {
    if (currency !== "EUR") return;
    var swapped = 0;
    document.querySelectorAll(".js-price[data-eur]").forEach(function (el) {
      if (!el.dataset.eur) return;
      el.textContent = el.dataset.eur;
      swapped++;
    });
    // Keep the Algerian address form when nothing on the page is sold in euros.
    if (!swapped) return;
    // Outside Algeria: country and city instead of wilaya / commune lists.
    [["wilaya", store.i18n.country || gettext("Country"), "country-name"], ["commune", store.i18n.city || gettext("City"), "address-level2"]].forEach(function (f) {
      document.querySelectorAll('input[type="hidden"][name="' + f[0] + '"]').forEach(function (hidden) {
        var wrap = hidden.closest(".searchable-select-wrapper");
        if (!wrap) return;
        var input = document.createElement("input");
        input.type = "text";
        input.name = f[0];
        input.required = true;
        input.autocomplete = f[2];
        input.className = "form-control rounded-3";
        input.placeholder = f[1];
        wrap.replaceWith(input);
        var label = input.parentElement && input.parentElement.querySelector("label");
        if (label) label.textContent = f[1];
      });
    });
  }
  if (document.readyState === "loading") document.addEventListener("DOMContentLoaded", apply);
  else apply();
})();
