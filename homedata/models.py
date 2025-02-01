from django.db import models
from wagtail.models import Page
from wagtail.admin.panels import FieldPanel

class RentalTrendsPage(Page):
    """
    A Wagtail page that displays rental trends (using your CSV data and interactive chart).
    """
    # Add any custom fields if you need them (for example, a brief introduction or extra content)
    intro = models.CharField(max_length=255, blank=True, help_text="Intro text for the page.")

    content_panels = Page.content_panels + [
        FieldPanel('intro'),
    ]

    # Ensure that this page can only be created as a child of your HomePage.
    # Replace 'home.HomePage' with the correct path if your home page model is in a different app.
    parent_page_types = ['home.HomePage']
    subpage_types = []  # Disallow child pages if desired

    template = "homedata/rental_trends.html"
