document.addEventListener("DOMContentLoaded", function () {
    var modal = document.getElementById("chainDetailModal");
    if (!modal) return;

    var i18n;
    try {
        i18n = JSON.parse(modal.dataset.i18n || "{}");
    } catch (_) {
        i18n = {};
    }

    function _(key) {
        return i18n[key] || key;
    }

    modal.addEventListener("show.bs.modal", function (e) {
        var btn = e.relatedTarget;
        var raw = btn.getAttribute("data-chain");
        var body = document.getElementById("chainModalBody");
        var data;
        try { data = JSON.parse(raw); } catch (_) { data = null; }

        if (!data || !data.items || !data.items.length) {
            body.innerHTML = '<div class="text-center py-4 text-muted"><i class="fas fa-info-circle me-2"></i>' + _("No chain data available.") + '</div>';
            return;
        }

        // ── Order Info ──────────────────────────────────────
        var html = '<div class="mb-4 p-3 rounded-3 bg-light">' +
            '<div class="d-flex justify-content-between align-items-center flex-wrap gap-2 mb-1">' +
            '<h6 class="fw-bold mb-0">' + data.order_number + '</h6>' +
            '<span class="badge bg-' + (data.status === 'delivered' ? 'success' : data.status === 'pending' ? 'warning' : 'secondary') + ' rounded-pill">' + data.status + '</span>' +
            '</div>' +
            '<div class="small text-muted">' +
            '<div><i class="fas fa-user me-1"></i>' + data.customer_name + (data.customer_phone ? ' &mdash; ' + data.customer_phone : '') + '</div>' +
            (data.wilaya ? '<div><i class="fas fa-map-marker-alt me-1"></i>' + data.wilaya + (data.commune ? ' &mdash; ' + data.commune : '') + '</div>' : '') +
            '<div><i class="fas fa-calendar me-1"></i>' + (data.created_at ? new Date(data.created_at).toLocaleString() : '') + '</div>' +
            '</div>' +
            '</div>';

        // ── Per Product ─────────────────────────────────────
        data.items.forEach(function (item) {
            var c = item.chain;
            var p = item.profits;

            html += '<div class="card border-0 shadow-sm rounded-3 mb-3">' +
                '<div class="card-header bg-white border-bottom-0 py-3 px-3 d-flex justify-content-between align-items-center flex-wrap gap-2">' +
                '<h6 class="fw-bold mb-0">' + item.title + '</h6>' +
                '<span class="small text-muted">' + item.qty + ' &times; ' + item.price.toFixed(2) + ' = <strong>' + item.subtotal.toFixed(2) + ' DZD</strong></span>' +
                '</div>' +
                '<div class="card-body pt-0 px-3 pb-3">';

            // Build level cards in a responsive grid
            var levels = [];

            if (c.supplier_wholesale > 0) {
                levels.push({ label: _("Provider"), color: 'danger', textClass: 'text-light', bgClass: 'bg-danger', purchased: '\u2014', sold: c.supplier_wholesale, profit: p.supplier });
            }

            levels.push({ label: _("Loft Design"), color: 'warning', textClass: 'text-warning', bgClass: 'bg-warning bg-opacity-10', purchased: c.supplier_wholesale > 0 ? c.supplier_wholesale : '\u2014', sold: c.loft_wholesale, profit: p.loft });

            if (c.affiliate_wholesale !== null) {
                levels.push({ label: _("Affiliate"), color: 'info', textClass: 'text-info', bgClass: 'bg-info bg-opacity-10', purchased: c.loft_wholesale, sold: c.affiliate_wholesale, profit: p.affiliate });
            }

            if (c.semi_wholesale !== null && c.retail_price_charged !== null) {
                levels.push({ label: _("Semi-Affiliate"), color: 'success', textClass: 'text-light', bgClass: 'bg-success', purchased: c.affiliate_wholesale !== null ? c.affiliate_wholesale : c.loft_wholesale, sold: c.retail_price_charged, profit: p.semi });
            }

            var profitColors = { danger: 'text-danger', warning: 'text-warning', info: 'text-info', success: 'text-success' };

            html += '<div class="row g-2">';
            levels.forEach(function (lvl) {
                var profitColor = profitColors[lvl.color] || 'text-dark';
                var purchasedDisplay = typeof lvl.purchased === 'number' ? lvl.purchased.toFixed(2) + ' DZD' : lvl.purchased;
                var soldDisplay = typeof lvl.sold === 'number' ? lvl.sold.toFixed(2) + ' DZD' : '\u2014';
                html += '<div class="col-md-6">' +
                    '<div class="p-3 rounded-3 border h-100" style="border-color:var(--bs-' + lvl.color + ')20 !important;">' +
                    '<div class="d-flex justify-content-between align-items-center mb-2">' +
                    '<span class="badge ' + lvl.bgClass + ' ' + lvl.textClass + ' px-2 py-1 fw-bold">' + lvl.label + '</span>' +
                    '<span class="fw-black fs-5 ' + profitColor + '">+' + lvl.profit.toFixed(2) + '</span>' +
                    '</div>' +
                    '<div class="d-flex justify-content-between small">' +
                    '<span class="text-muted">' + _("Purchased") + ': <strong>' + purchasedDisplay + '</strong></span>' +
                    '<span class="text-muted">' + _("Sold") + ': <strong>' + soldDisplay + '</strong></span>' +
                    '</div>' +
                    '</div>' +
                    '</div>';
            });
            html += '</div>';

            // Item total
            var totalProfit = p.supplier + p.loft + p.affiliate + p.semi;
            html += '<div class="d-flex justify-content-end mt-2 pt-2 border-top small fw-bold">' +
                '<span>' + _("Item Profit") + ': ' + totalProfit.toFixed(2) + ' DZD</span>' +
                '</div>';

            html += '</div></div>';
        });

        // ── Order Summary ────────────────────────────────────
        var t = data.totals;
        html += '<div class="p-3 rounded-3 bg-light">' +
            '<div class="d-flex justify-content-between align-items-center flex-wrap gap-2 mb-2">' +
            '<span class="fw-bold fs-6">' + _("Order Total") + '</span>' +
            '<span class="fw-black fs-5">' + t.total.toFixed(2) + ' DZD</span>' +
            '</div>' +
            '<hr class="my-2">' +
            '<div class="row g-2 text-center">' +
            (t.supplier_share > 0 ? '<div class="col-6 col-md-3"><div class="p-2 rounded-3 bg-danger"><small class="text-light fw-bold d-block">' + _("Provider") + '</small><span class="fw-black text-light">' + t.supplier_share.toFixed(2) + ' DZD</span></div></div>' : '') +
            '<div class="col-6 col-md-3"><div class="p-2 rounded-3 bg-warning bg-opacity-10"><small class="text-warning fw-bold d-block">' + _("Loft") + '</small><span class="fw-black">' + t.loft_share.toFixed(2) + ' DZD</span></div></div>' +
            (t.affiliate_share > 0 ? '<div class="col-6 col-md-3"><div class="p-2 rounded-3 bg-info bg-opacity-10"><small class="text-info fw-bold d-block">' + _("Affiliate") + '</small><span class="fw-black">' + t.affiliate_share.toFixed(2) + ' DZD</span></div></div>' : '') +
            (t.semi_share > 0 ? '<div class="col-6 col-md-3"><div class="p-2 rounded-3 bg-success"><small class="text-light fw-bold d-block">' + _("Semi") + '</small><span class="fw-black text-light">' + t.semi_share.toFixed(2) + ' DZD</span></div></div>' : '') +
            '</div>' +
            '</div>';

        body.innerHTML = html;
    });
});
