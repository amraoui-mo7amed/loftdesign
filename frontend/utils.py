from decouple import config

def get_website_name():
    return config("SITE_NAME", default="LOFT Design")
