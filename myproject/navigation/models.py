from django.db import models
from modelcluster.models import ClusterableModel
from wagtail import blocks
from wagtail.admin.panels import FieldPanel, MultiFieldPanel
from wagtail.contrib.settings.models import BaseSiteSetting, register_setting
from wagtail.fields import StreamField
from wagtail.snippets.blocks import SnippetChooserBlock

from myproject.utils.blocks import LinkStreamBlock, InternalLinkBlock
from myproject.utils.models import ActionLinkBlock


class FooterLinkBlock(blocks.StructBlock):
    """
    A flexible link block that can be either internal (Wagtail page) or external URL.
    """
    link_type = blocks.ChoiceBlock(
        choices=[
            ('internal', 'Internal Page'),
            ('external', 'External URL'),
        ],
        default='internal',
        help_text="Choose whether this links to a page on this site or an external website"
    )
    
    # Internal link fields
    internal_page = blocks.PageChooserBlock(
        required=False,
        help_text="Choose a page from this website"
    )
    
    # External link fields
    external_url = blocks.URLBlock(
        required=False,
        help_text="Enter the full URL (e.g., https://example.com)"
    )
    
    # Common fields
    title = blocks.CharBlock(
        required=True,
        help_text="The text that will be displayed as the link"
    )
    
    open_in_new_tab = blocks.BooleanBlock(
        default=False,
        required=False,
        help_text="Open this link in a new tab/window"
    )

    class Meta:
        icon = "link"
        template = "components/footer_link_block.html"

    def clean(self, value):
        cleaned_data = super().clean(value)
        
        if cleaned_data.get('link_type') == 'internal':
            if not cleaned_data.get('internal_page'):
                raise blocks.ValidationError("Please select an internal page.")
        elif cleaned_data.get('link_type') == 'external':
            if not cleaned_data.get('external_url'):
                raise blocks.ValidationError("Please enter an external URL.")
        
        return cleaned_data

    def get_url(self, value):
        """Get the URL for this link."""
        if value.get('link_type') == 'internal' and value.get('internal_page'):
            return value['internal_page'].url
        elif value.get('link_type') == 'external' and value.get('external_url'):
            return value['external_url']
        return '#'

    def get_title(self, value):
        """Get the title for this link."""
        return value.get('title', '')


class FooterSectionBlock(blocks.StructBlock):
    """
    A section of footer links with a heading.
    """
    section_heading = blocks.CharBlock(
        required=True,
        help_text="The heading for this section of links"
    )
    
    links = blocks.ListBlock(
        FooterLinkBlock(),
        min_num=0,  # Allow zero links so only the action button can be shown
        help_text="Add links to this section"
    )

    action = ActionLinkBlock(required=False, help_text="Add a prominent action button to this section (optional)")

    class Meta:
        icon = "list-ul"
        template = "components/footer_section_block.html"


@register_setting(icon="list-ul")
class NavigationSettings(BaseSiteSetting, ClusterableModel):
    primary_navigation = StreamField(
        [("link", InternalLinkBlock())],
        blank=True,
        help_text="Main site navigation",
    )
    
    footer_navigation = StreamField(
        [
            ("section", FooterSectionBlock()),
        ],
        blank=True,
        help_text="Organize footer links into sections with headings",
    )

    panels = [
        FieldPanel("primary_navigation"),
        MultiFieldPanel([
            FieldPanel("footer_navigation"),
        ], heading="Footer Navigation", help_text="Create sections of links for the footer. Each section can contain both internal and external links."),
    ]
