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


def role_required(allowed_roles):
    """
    Decorator for views that checks if the user has one of the allowed roles.
    allowed_roles: list of roles from UserProfile.roleChoices
    """

    def decorator(view_func):
        @wraps(view_func)
        def _wrapped_view(request, *args, **kwargs):
            if not request.user.is_authenticated:
                return redirect(reverse("user_auth:login"))

            # Check if user has a profile and if the role is allowed
            # Superusers bypass the role check
            if request.user.is_superuser:
                return view_func(request, *args, **kwargs)

            profile = getattr(request.user, "profile", None)
            if profile and profile.is_blocked:
                # A blocked account loses access immediately, even with an open session.
                from django.contrib.auth import logout
                logout(request)
                return redirect(reverse("user_auth:login"))
            if profile and profile.role in allowed_roles:
                return view_func(request, *args, **kwargs)

            raise PermissionDenied

        return _wrapped_view

    return decorator


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
