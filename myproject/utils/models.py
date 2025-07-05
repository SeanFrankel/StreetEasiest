from io import BytesIO
from bs4 import BeautifulSoup
from django.core.exceptions import FieldDoesNotExist, ValidationError
from django.core.files.images import ImageFile
from django.contrib.staticfiles.finders import find
from django.db import models
from django.db.models import QuerySet
from django.utils.decorators import method_decorator
from django.utils.functional import cached_property
from modelcluster.fields import ParentalKey
from willow.image import Image as WillowImage

from wagtail.admin.panels import FieldPanel, MultiFieldPanel
from wagtail.images.widgets import AdminImageChooser
from wagtail.contrib.settings.models import BaseSiteSetting, register_setting
from wagtail.fields import RichTextField
from wagtail.models import Orderable, Page
from wagtail.rich_text import expand_db_html
from wagtail.snippets.models import register_snippet

from myproject.images.models import CustomImage
from myproject.utils.cache import get_default_cache_control_decorator
from myproject.utils.query import order_by_pk_position


# Related pages
class PageRelatedPage(Orderable):
    parent = ParentalKey(Page, related_name="page_related_pages")
    page_id: int
    page = models.ForeignKey(
        "wagtailcore.Page",
        on_delete=models.CASCADE,
        related_name="+",
    )

    panels = [FieldPanel("page")]


# Generic social fields abstract class to add social image/text to any new content type easily.
class SocialFields(models.Model):
    social_image = models.ForeignKey(
        "images.CustomImage",
        null=True,
        blank=True,
        on_delete=models.SET_NULL,
        related_name="+",
    )
    social_text = models.CharField(max_length=255, blank=True)

    class Meta:
        abstract = True

    promote_panels = [
        MultiFieldPanel(
            [
                FieldPanel("social_image", widget=AdminImageChooser),
                FieldPanel("social_text")
            ],
            "Social networks",
        )
    ]


# Generic listing fields abstract class to add listing image/text to any new content type easily.
class ListingFields(models.Model):
    listing_image = models.ForeignKey(
        "images.CustomImage",
        null=True,
        blank=True,
        on_delete=models.SET_NULL,
        related_name="+",
        help_text="Choose the image you wish to be displayed when this page appears in listings",
    )
    listing_title = models.CharField(
        max_length=255,
        blank=True,
        help_text="Override the page title used when this page appears in listings",
    )
    listing_summary = models.CharField(
        max_length=255,
        blank=True,
        help_text="The text summary used when this page appears in listings. It's also used as "
        "the description for search engines if the 'Meta description' field above is not defined.",
    )

    class Meta:
        abstract = True

    promote_panels = [
        MultiFieldPanel(
            [
                FieldPanel("listing_image", widget=AdminImageChooser),
                FieldPanel("listing_title"),
                FieldPanel("listing_summary"),
            ],
            "Listing information",
        )
    ]


@register_snippet
class AuthorSnippet(models.Model):
    title = models.CharField(blank=False, max_length=255)
    image = models.ForeignKey(
        "images.CustomImage",
        null=True,
        blank=True,
        on_delete=models.SET_NULL,
        related_name="+",
    )

    panels = [
        FieldPanel("title"),
        FieldPanel("image", widget=AdminImageChooser),
    ]

    def __str__(self):
        return self.title


@register_snippet
class ArticleTopic(models.Model):
    title = models.CharField(blank=False, max_length=255)
    slug = models.SlugField(blank=False, max_length=255)

    panels = [
        FieldPanel("title"),
        FieldPanel("slug"),
    ]

    def __str__(self):
        return self.title

    def save(self, *args, **kwargs):
        if self._state.adding and not self.slug:
            self.slug = self.slugify(self.title)
            using = kwargs.get("using") or router.db_for_write(
                type(self), instance=self
            )
            # Make sure we write to the same db for all attempted writes,
            # with a multi-master setup, theoretically we could try to
            # write and rollback on different DBs
            kwargs["using"] = using
            # Be opportunistic and try to save the tag, this should work for
            # most cases ;)
            try:
                with transaction.atomic(using=using):
                    res = super().save(*args, **kwargs)
                return res
            except IntegrityError:
                pass
            # Now try to find existing slugs with similar titles
            slugs = set(
                type(self)
                ._default_manager.filter(slug__startswith=self.slug)
                .values_list("slug", flat=True)
            )
            i = 1
            while True:
                slug = self.slugify(self.title, i)
                if slug not in slugs:
                    self.slug = slug
                    # We purposely ignore concurrency issues here for now.
                    # (That is, till we found a nice solution...)
                    return super().save(*args, **kwargs)
                i += 1
        else:
            return super().save(*args, **kwargs)

    def slugify(self, title, i=None):
        title = slugify(title, allow_unicode=True)

        if i is not None:
            title += "_%d" % i
        return title


@register_snippet
class Statistic(models.Model):
    statistic = models.CharField(blank=False, max_length=12)
    description = models.CharField(blank=False, max_length=225)

    panels = [
        FieldPanel("statistic"),
        FieldPanel("description"),
    ]

    def __str__(self):
        return self.statistic


@register_setting
class SocialMediaSettings(BaseSiteSetting):
    """
    Settings for social media integration.
    """
    twitter_handle = models.CharField(
        max_length=255,
        blank=True,
        help_text="Your Twitter/X handle without the @ symbol"
    )
    linkedin_handle = models.CharField(
        max_length=255,
        blank=True,
        help_text="Your LinkedIn profile URL"
    )
    facebook_app_id = models.CharField(
        max_length=255,
        blank=True,
        help_text="Your Facebook App ID"
    )
    instagram_handle = models.CharField(
        max_length=255,
        blank=True,
        help_text="Your Instagram handle without the @ symbol"
    )
    tiktok_handle = models.CharField(
        max_length=255,
        blank=True,
        help_text="Your TikTok handle without the @ symbol"
    )
    default_sharing_text = models.CharField(
        max_length=255,
        blank=True,
        help_text="Default text used when sharing pages on social media"
    )

    panels = [
        FieldPanel("twitter_handle"),
        FieldPanel("linkedin_handle"),
        FieldPanel("facebook_app_id"),
        FieldPanel("instagram_handle"),
        FieldPanel("tiktok_handle"),
        FieldPanel("default_sharing_text"),
    ]

    class Meta:
        verbose_name = 'Social Media'


@register_setting
class SystemMessagesSettings(BaseSiteSetting):
    """
    Settings for system-wide messages and content.
    """
    title_404 = models.CharField(
        max_length=255,
        default="Page not found",
        help_text="Title shown on 404 pages"
    )
    body_404 = RichTextField(
        default="<p>The page you are looking for could not be found.</p>",
        help_text="Content shown on 404 pages"
    )
    placeholder_image = models.ForeignKey(
        'images.CustomImage',
        null=True,
        blank=True,
        on_delete=models.SET_NULL,
        related_name='+',
        help_text="Default image used when no image is specified"
    )
    footer_newsletter_signup_title = models.CharField(
        max_length=255,
        default="Stay Updated",
        help_text="Title for the newsletter signup section in the footer"
    )
    footer_newsletter_signup_description = models.TextField(
        default="Get the latest updates and news delivered to your inbox.",
        help_text="Description for the newsletter signup section in the footer"
    )
    footer_newsletter_signup_link = models.URLField(
        max_length=255,
        default="",
        help_text="Link for the newsletter signup form"
    )

    panels = [
        MultiFieldPanel([
            FieldPanel('title_404'),
            FieldPanel('body_404'),
        ], heading="404 Page"),
        FieldPanel('placeholder_image', widget=AdminImageChooser),
        MultiFieldPanel([
            FieldPanel('footer_newsletter_signup_title'),
            FieldPanel('footer_newsletter_signup_description'),
            FieldPanel('footer_newsletter_signup_link'),
        ], heading="Footer Newsletter"),
    ]

    class Meta:
        verbose_name = 'System Messages'


@register_setting
class GoogleAdSenseSettings(BaseSiteSetting):
    """
    Settings for Google AdSense integration.
    """
    publisher_id = models.CharField(
        max_length=255,
        blank=True,
        help_text="Your Google AdSense Publisher ID (e.g., ca-pub-1234567890123456)"
    )
    enable_adsense = models.BooleanField(
        default=False,
        help_text="Enable Google AdSense on the website"
    )

    panels = [
        FieldPanel('enable_adsense'),
        FieldPanel('publisher_id'),
    ]

    class Meta:
        verbose_name = 'Google AdSense'


# Apply default cache headers on this page model's serve method.
@method_decorator(get_default_cache_control_decorator(), name="serve")
class BasePage(SocialFields, ListingFields, Page):
    show_in_menus_default = True

    appear_in_search_results = models.BooleanField(
        default=True,
        help_text="Make this page available for indexing by search engines."
        "If unchecked, the page will no longer be indexed by search engines.",
    )

    class Meta:
        abstract = True

    promote_panels = (
        Page.promote_panels
        + SocialFields.promote_panels
        + ListingFields.promote_panels
        + [
            FieldPanel("appear_in_search_results"),
        ]
    )

    @cached_property
    def related_pages(self) -> QuerySet:
        """
        Return a `PageQuerySet` of items related to this page via the
        `PageRelatedPage` through model, and are suitable for display.
        The result is ordered to match that specified by editors using
        the 'page_related_pages' `InlinePanel`.
        """
        ordered_page_pks = tuple(item.page_id for item in self.page_related_pages.all())
        return order_by_pk_position(
            Page.objects.live().public().specific(),
            pks=ordered_page_pks,
            exclude_non_matches=True,
        )

    @property
    def plain_introduction(self):
        """
        This property returns a plain text representation of a model's 'introduction' field.

        If 'introduction' is a RichTextField, the method uses BeautifulSoup to filter and parse
        the rich text content, returning the plain text. If 'introduction' is a standard TextField
        or if it doesn't exist, the method returns the original text or an empty string.

        Returns:
            str: Plain text representation of the 'introduction' field or none if the field
            doesn't exist or is blank.
        """
        try:
            introduction_field = self._meta.get_field("introduction")
        except FieldDoesNotExist:
            pass
        else:
            introduction_value = getattr(self, "introduction", None)
            if introduction_value:
                if isinstance(introduction_field, RichTextField):
                    soup = BeautifulSoup(expand_db_html(introduction_value), "html.parser")
                    return soup.text
                else:
                    return introduction_value


BasePage._meta.get_field("seo_title").verbose_name = "Title tag"
BasePage._meta.get_field("search_description").verbose_name = "Meta description"
