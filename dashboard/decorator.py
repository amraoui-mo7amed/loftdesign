from functools import wraps
from django.core.paginator import Paginator, EmptyPage, PageNotAnInteger
from django.shortcuts import render, redirect
from django.urls import reverse
from django.core.exceptions import PermissionDenied


def admin_required(view_func):
    """
    Decorator for views that checks that the user is logged in and is a superuser,
    raising PermissionDenied if not.
    """

    @wraps(view_func)
    def _wrapped_view(request, *args, **kwargs):
        if not request.user.is_authenticated:
            return redirect(reverse("user_auth:login"))
        if not request.user.is_superuser:
            raise PermissionDenied
        return view_func(request, *args, **kwargs)

    return _wrapped_view


def with_pagination(
    per_page=10, context_name="page_obj", queryset_name="queryset", template="list.html"
):
    def decorator(view_func):
        @wraps(view_func)
        def _wrapped_view(request, *args, **kwargs):
            response = view_func(request, *args, **kwargs)

            # If response is not a dict (e.g. HttpResponse), skip
            if not isinstance(response, dict):
                return response

            queryset = response.get(queryset_name)
            if queryset is None:
                return response

            page_number = request.GET.get("page", 1)
            paginator = Paginator(queryset, per_page)

            try:
                page_obj = paginator.page(page_number)
            except PageNotAnInteger:
                page_obj = paginator.page(1)
            except EmptyPage:
                page_obj = paginator.page(paginator.num_pages)

            response[context_name] = page_obj
            return render(request, f"{template}.html", response)

        return _wrapped_view

    return decorator
