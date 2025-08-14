from django.db import models
from wagtail.admin.panels import FieldPanel, InlinePanel, MultiFieldPanel
from wagtail.fields import RichTextField
from wagtail.search import index

from wagtail.fields import StreamField
from myproject.utils.blocks import StoryBlock
from myproject.utils.models import BasePage


class StandardPage(BasePage):
    template = "pages/standard_page.html"

    introduction = models.TextField(blank=True)
    display_table_of_contents = models.BooleanField(default=True)
    body = StreamField(StoryBlock())
    featured_section_title = models.TextField(blank=True)

    search_fields = BasePage.search_fields + [index.SearchField("introduction")]

    content_panels = BasePage.content_panels + [
        FieldPanel("introduction"),
        FieldPanel("display_table_of_contents"),
        FieldPanel("body"),
        MultiFieldPanel(
            [
                FieldPanel("featured_section_title", heading="Title"),
                InlinePanel(
                    "page_related_pages",
                    label="Pages",
                    max_num=3,
                ),
            ],
            heading="Featured section",
        ),
    ]


class IndexPage(BasePage):
    template = "pages/index_page.html"

    introduction = RichTextField(blank=True)
    body = StreamField(StoryBlock(), blank=True)

    search_fields = BasePage.search_fields + [index.SearchField("introduction")]

    content_panels = BasePage.content_panels + [
        FieldPanel("introduction"),
        InlinePanel(
            "page_related_pages",
            label="Featured pages",
            min_num=3,
            max_num=12,
        ),
        FieldPanel("body")
    ]


class PrivacyPolicyPage(BasePage):
    """
    A dedicated page for the Privacy Policy that includes all required elements
    for Google AdSense compliance.
    """
    template = "pages/privacy_policy_page.html"
    
    # Main privacy policy content
    privacy_content = RichTextField(
        blank=True,
        help_text="Main privacy policy content including data collection, usage, and user rights"
    )
    
    # Cookie policy section
    cookie_policy = RichTextField(
        blank=True,
        help_text="Detailed information about cookies used on the site"
    )
    
    # AdSense specific section
    adsense_policy = RichTextField(
        blank=True,
        help_text="Information about Google AdSense, data sharing, and advertising"
    )
    
    # User choices and opt-out section
    user_choices = RichTextField(
        blank=True,
        help_text="Information about user choices, opt-out options, and data control"
    )
    
    # Contact information
    contact_info = RichTextField(
        blank=True,
        help_text="Contact information for privacy-related inquiries"
    )

    content_panels = BasePage.content_panels + [
        FieldPanel("privacy_content"),
        FieldPanel("cookie_policy"),
        FieldPanel("adsense_policy"),
        FieldPanel("user_choices"),
        FieldPanel("contact_info"),
    ]

    class Meta:
        verbose_name = "Privacy Policy Page"


class TermsOfServicePage(BasePage):
    """
    A dedicated page for Terms of Service that complements the privacy policy.
    """
    template = "pages/terms_of_service_page.html"
    
    # Main terms content
    terms_content = RichTextField(
        blank=True,
        help_text="Main terms of service content including usage rights and restrictions"
    )
    
    # User obligations section
    user_obligations = RichTextField(
        blank=True,
        help_text="User obligations and acceptable use policies"
    )
    
    # Intellectual property section
    intellectual_property = RichTextField(
        blank=True,
        help_text="Information about intellectual property rights and licensing"
    )
    
    # Limitation of liability section
    liability = RichTextField(
        blank=True,
        help_text="Limitation of liability and disclaimers"
    )
    
    # Contact information
    contact_info = RichTextField(
        blank=True,
        help_text="Contact information for terms-related inquiries"
    )

    content_panels = BasePage.content_panels + [
        FieldPanel("terms_content"),
        FieldPanel("user_obligations"),
        FieldPanel("intellectual_property"),
        FieldPanel("liability"),
        FieldPanel("contact_info"),
    ]

    class Meta:
        verbose_name = "Terms of Service Page"

