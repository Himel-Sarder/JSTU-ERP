"""Make the university identity (name, logo, owner) available to every template."""

from django.conf import settings


def university(request):
    return {"jstu": settings.JSTU}
