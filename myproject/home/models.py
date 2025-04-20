from django.db import models
from wagtail.admin.panels import FieldPanel, InlinePanel, MultiFieldPanel
from wagtail.search import index
from wagtail.models import Page
from wagtail.fields import StreamField, RichTextField
from myproject.utils.blocks import StoryBlock, InternalLinkBlock
from myproject.utils.models import BasePage


class HomePage(BasePage):
    template = "pages/home_page.html"
    introduction = models.TextField(blank=True)
    hero_cta = StreamField(
        [("link", InternalLinkBlock())],
        blank=True,
        min_num=0,
        max_num=1,
        use_json_field=True,
    )
    body = StreamField(StoryBlock(), use_json_field=True)
    featured_section_title = models.TextField(blank=True)

    search_fields = BasePage.search_fields + [index.SearchField("introduction")]

    content_panels = BasePage.content_panels + [
        FieldPanel("introduction"),
        FieldPanel("hero_cta"),
        FieldPanel("body"),
        MultiFieldPanel(
            [
                FieldPanel("featured_section_title", heading="Title"),
                InlinePanel(
                    "page_related_pages",
                    label="Pages",
                    max_num=12,
                ),
            ],
            heading="Featured section",
        ),
    ]

    class Meta:
        verbose_name = "Home Page"


class NYCAggregatedDashboardPage(BasePage):
    """A page that displays the NYC Aggregated Dashboard."""
    header = models.CharField(
        max_length=255,
        default="NYC Aggregated Dashboard",
        help_text="Main heading for the dashboard page"
    )
    instructions = RichTextField(
        blank=True,
        help_text="Instructions on how to use the dashboard"
    )
    
    search_fields = BasePage.search_fields + [
        index.SearchField('header'),
        index.SearchField('instructions'),
    ]
    
    content_panels = BasePage.content_panels + [
        FieldPanel("header"),
        FieldPanel("instructions"),
    ]
    
    template = "pages/nyc_aggregated_dashboard.html"
    
    class Meta:
        verbose_name = "NYC Aggregated Dashboard Page"
