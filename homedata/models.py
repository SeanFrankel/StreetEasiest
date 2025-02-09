from django.db import models
from wagtail.models import Page
from wagtail.fields import RichTextField
from wagtail.admin.panels import FieldPanel

class RentalTrendsPage(Page):
    """
    A Wagtail page that displays rental trends (using your CSV data and interactive chart).
    Includes an intro (CharField) and a FAQ section (RichTextField).
    """
    intro = models.CharField(
        max_length=255,
        blank=True,
        help_text="Intro text for the page."
    )
    faq_section = RichTextField(
        blank=True,
        help_text="FAQ content for the page (shown at the bottom)."
    )

    content_panels = Page.content_panels + [
        FieldPanel('intro'),
        FieldPanel('faq_section'),
    ]

    # Ensure that this page can only be created as a child of your HomePage.
    parent_page_types = ['home.HomePage']

    # Disallow child pages.
    subpage_types = []

    template = "homedata/rental_trends.html"
