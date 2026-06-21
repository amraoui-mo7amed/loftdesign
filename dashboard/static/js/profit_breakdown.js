document.addEventListener("DOMContentLoaded", function () {
  var modal = document.getElementById("profitBreakdownModal");
  if (!modal) return;
  var strings;
  try {
    strings = JSON.parse(modal.getAttribute("data-breakdown"));
  } catch (_) {
    return;
  }
  modal.addEventListener("show.bs.modal", function (e) {
    var btn = e.relatedTarget;
    var raw = btn.getAttribute("data-breakdown");
    var orderId = btn.getAttribute("data-order-id");
    document.getElementById("breakdownOrderId").textContent = "#" + orderId;
    var body = document.getElementById("breakdownModalBody");
    var items;
    try {
      items = JSON.parse(raw);
    } catch (_) {
      items = [];
    }
    if (!items.length) {
      body.innerHTML =
        '<div class="text-center py-4 text-muted"><i class="fas fa-info-circle me-2"></i>' +
        strings.no_data +
        "</div>";
      return;
    }
    var html =
      '<div class="table-responsive"><table class="table table-bordered table-sm align-middle mb-0"><thead class="table-light"><tr>' +
      "<th>" +
      strings.product +
      '</th><th class="text-center">' +
      strings.qty +
      '</th><th class="text-end">' +
      strings.total +
      '</th><th class="text-end" style="color:var(--bs-danger)">' +
      strings.supplier +
      '</th><th class="text-end" style="color:#ffc107">' +
      strings.loft +
      '</th><th class="text-end" style="color:var(--bs-info)">' +
      strings.affiliate +
      '</th><th class="text-end" style="color:var(--bs-success)">' +
      strings.semi +
      "</th></tr></thead><tbody>";
    var totals = { total: 0, supplier: 0, loft: 0, affiliate: 0, semi: 0 };
    items.forEach(function (it) {
      var t = parseFloat(it.price) || 0;
      var s = parseFloat(it.supplier) || 0;
      var l = parseFloat(it.loft) || 0;
      var a = parseFloat(it.affiliate) || 0;
      var m = parseFloat(it.semi) || 0;
      totals.total += t;
      totals.supplier += s;
      totals.loft += l;
      totals.affiliate += a;
      totals.semi += m;
      html +=
        "<tr>" +
        "<td>" +
        it.title +
        '</td><td class="text-center">' +
        it.qty +
        '</td><td class="text-end fw-bold">' +
        t.toFixed(2) +
        '</td><td class="text-end text-danger">' +
        s.toFixed(2) +
        '</td><td class="text-end" style="color:#ffc107">' +
        l.toFixed(2) +
        '</td><td class="text-end text-info">' +
        a.toFixed(2) +
        '</td><td class="text-end text-success">' +
        m.toFixed(2) +
        "</td></tr>";
    });
    html +=
      '</tbody><tfoot class="table-dark fw-bold"><tr><td colspan="2">' +
      strings.totals +
      '</td><td class="text-end">' +
      totals.total.toFixed(2) +
      '</td><td class="text-end text-danger">' +
      totals.supplier.toFixed(2) +
      '</td><td class="text-end" style="color:#ffc107">' +
      totals.loft.toFixed(2) +
      '</td><td class="text-end text-info">' +
      totals.affiliate.toFixed(2) +
      '</td><td class="text-end text-success">' +
      totals.semi.toFixed(2) +
      "</td></tr></tfoot></table></div>";
    body.innerHTML = html;
  });
});
