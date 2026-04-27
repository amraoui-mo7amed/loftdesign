from django.utils.translation import get_language_bidi


def get_website_name():
    """
    Returns the website name based on the current language direction.
    """
    if get_language_bidi():
        return "ذكي الإستغلال"
    else:
        return "Smart Operating Cycle"
