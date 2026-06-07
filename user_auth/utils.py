import os
import re
import time
import secrets
from django.db import transaction
from django.contrib.auth.models import User


def create_user_account(user_data, profile_data, profile_picture):
    """
    Helper to create a User and UserProfile within a transaction.
    """
    from .models import UserProfile

    base_username = user_data["email"].split("@")[0]
    username = base_username
    if User.objects.filter(username=username).exists():
        username = f"{base_username}_{int(time.time())}"

    with transaction.atomic():
        user = User.objects.create_user(
            username=username,
            email=user_data["email"],
            password=user_data["password"],
            first_name=user_data["first_name"],
            last_name=user_data["last_name"],
        )

        UserProfile.objects.create(
            user=user,
            profile_picture=profile_picture,
            phone_number=profile_data.get("phone_number", ""),
            sex=profile_data.get("sex"),
            birth_date=profile_data.get("birth_date"),
        )
    return user


def create_affiliate_account(user_data, profile_data):
    """
    Creates an affiliate account with is_active=False until admin approval.
    Generates a unique affiliate code.
    """
    from .models import UserProfile

    base_username = user_data["email"].split("@")[0]
    username = base_username
    if User.objects.filter(username=username).exists():
        username = f"{base_username}_{int(time.time())}"

    affiliate_code = generate_affiliate_code()

    with transaction.atomic():
        user = User.objects.create_user(
            username=username,
            email=user_data["email"],
            password=user_data["password"],
            first_name=user_data["first_name"],
            last_name=user_data["last_name"],
            is_active=False,
        )

        UserProfile.objects.create(
            user=user,
            role=UserProfile.roleChoices.AFFILIATE,
            affiliate_code=affiliate_code,
            phone_number=profile_data.get("phone_number", ""),
            is_approved=False,
        )
    return user, affiliate_code


def generate_affiliate_code():
    """Generate a unique 8-character affiliate code."""
    return "LOFT" + secrets.token_hex(4).upper()[:8]


def user_profile_upload_path(instance, filename):
    ext = filename.split(".")[-1]
    filename = f"user_{instance.user.id}_profile.{ext}"
    return os.path.join("profile_pictures/", filename)


def validate_algerian_phone(phone):
    """
    Validates Algerian phone numbers (mobile).
    Supports formats: 05, 06, 07, +213, 213.
    """
    pattern = r"^(0|\+213|213)[567]\d{8}$"
    return bool(re.match(pattern, str(phone)))
