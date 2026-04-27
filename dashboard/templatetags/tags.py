from django import template

register = template.Library()

@register.inclusion_tag("components/pagination.html", takes_context=True)
def render_pagination(context, page_obj):
    request = context["request"]
    querydict = request.GET.copy()
    if "page" in querydict:
        querydict.pop("page")

    base_url = request.path + "?" + querydict.urlencode()
    if base_url and not base_url.endswith("&") and not base_url.endswith("?"):
        base_url += "&"

    return {
        "page_obj": page_obj,
        "base_url": base_url,
    }



@register.filter
def humanize_number(value):
    """
    Converts a large number into a human-readable format with k, M, B, etc.
    Example:
        1500 -> 1.5k
        2500000 -> 2.5M
    """
    try:
        num = float(value)
    except (ValueError, TypeError):
        return value

    if num >= 1_000_000_000:
        return f"{num / 1_000_000_000:.1f}B"
    elif num >= 1_000_000:
        return f"{num / 1_000_000:.1f}M"
    elif num >= 1_000:
        return f"{num / 1_000:.1f}k"
    else:
        return f"{num:.0f}"
