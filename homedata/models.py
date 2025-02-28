from django.db import models
from wagtail.models import Page
from wagtail.fields import RichTextField, StreamField
from wagtail.admin.panels import FieldPanel
from wagtail.blocks import RichTextBlock

class RentalTrendsPage(Page):
    """
    A Wagtail page that displays rental trends (using your CSV data and interactive chart).
    Includes an intro (CharField) and a FAQ section (RichTextField).
    """
    intro = RichTextField(
        blank=True,
        help_text="Intro text for the page."
    )
    
    body = StreamField([
        ('rich_text', RichTextBlock()),
    ], blank=True, use_json_field=True)

    data_faqs = RichTextField(
        blank=True,
        help_text="Data FAQs content for the page."
    )
    how_to_use = RichTextField(
        blank=True,
        help_text="Instructions on how to use the page."
    )
    content_panels = Page.content_panels + [
        FieldPanel('intro'),
        FieldPanel('data_faqs'),
        FieldPanel('how_to_use'),
    ]

    # Ensure that this page can only be created as a child of your HomePage.
    parent_page_types = ['home.HomePage']

    # Disallow child pages.
    subpage_types = []

    template = "homedata/rental_trends.html"
    
    def get_context(self, request, *args, **kwargs):
        context = super().get_context(request, *args, **kwargs)
        
        # Add available neighborhoods (normally these would come from your data)
        context['neighborhoods'] = [
            "Manhattan", "Brooklyn", "Queens", "Bronx", "Staten Island", 
            "Upper East Side", "Upper West Side", "Midtown", "Downtown", 
            "Williamsburg", "Park Slope", "Astoria", "Long Island City"
        ]
        
        # Add available years for filtering
        context['years'] = list(range(2010, 2024))
        
        return context
