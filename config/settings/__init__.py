# Import environment-specific settings
import os

from .base import *

environment = os.getenv("DJANGO_ENV", "development")

if environment == "production":
    from .production import *
else:
    from .development import *
