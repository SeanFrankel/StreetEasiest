from django.db import models
from django.core.validators import EmailValidator
from django.core.exceptions import ValidationError
from django.utils import timezone
from django.urls import reverse
from modelcluster.fields import ParentalKey
from wagtail.admin.panels import (
    FieldPanel, FieldRowPanel,
    InlinePanel, MultiFieldPanel
)
from wagtail.fields import RichTextField
from wagtail.contrib.forms.models import AbstractEmailForm, AbstractFormField
from wagtail.contrib.forms.panels import FormSubmissionsPanel
from wagtail.admin.panels import ObjectList, TabbedInterface
from wagtail.search import index

from myproject.utils.models import BasePage


class FormField(AbstractFormField):
    page = ParentalKey('FormPage', on_delete=models.CASCADE, related_name='form_fields')


class FormPage(AbstractEmailForm, BasePage):
    template = "pages/form_page.html"
    introduction = RichTextField(blank=True, features=["bold", "italic", "link"])
    action_text = models.CharField(
        max_length=32,
        blank=True,
        help_text='Form action text. Defaults to "Submit"',
    )
    thank_you_text = RichTextField(blank=True)

    content_panels = AbstractEmailForm.content_panels + [
        FormSubmissionsPanel(),
        FieldPanel('introduction'),
        InlinePanel('form_fields', label="Form fields"),
        FieldPanel('thank_you_text'),
        MultiFieldPanel([
            FieldRowPanel([
                FieldPanel('from_address', classname="col6"),
                FieldPanel('to_address', classname="col6"),
            ]),
            FieldPanel('subject'),
        ], "Email"),
    ]


class NewsletterSubscriber(models.Model):
    """
    Model to store newsletter subscribers with email validation and unsubscribe functionality.
    """
    email = models.EmailField(
        unique=True,
        validators=[EmailValidator()],
        help_text="Subscriber's email address"
    )
    first_name = models.CharField(
        max_length=100,
        blank=True,
        help_text="Subscriber's first name (optional)"
    )
    last_name = models.CharField(
        max_length=100,
        blank=True,
        help_text="Subscriber's last name (optional)"
    )
    is_active = models.BooleanField(
        default=True,
        help_text="Whether the subscriber is currently subscribed"
    )
    subscribed_date = models.DateTimeField(
        default=timezone.now,
        help_text="When the subscriber signed up"
    )
    unsubscribed_date = models.DateTimeField(
        null=True,
        blank=True,
        help_text="When the subscriber unsubscribed"
    )
    unsubscribe_token = models.CharField(
        max_length=64,
        unique=True,
        null=True,
        blank=True,
        help_text="Unique token for unsubscribe links"
    )
    source = models.CharField(
        max_length=100,
        default="website",
        help_text="Where the subscriber signed up from"
    )

    class Meta:
        verbose_name = "Newsletter Subscriber"
        verbose_name_plural = "Newsletter Subscribers"
        ordering = ['-subscribed_date']

    def __str__(self):
        return self.email

    def save(self, *args, **kwargs):
        if not self.unsubscribe_token:
            import secrets
            self.unsubscribe_token = secrets.token_urlsafe(32)
        super().save(*args, **kwargs)

    def unsubscribe(self):
        """Mark subscriber as unsubscribed."""
        self.is_active = False
        self.unsubscribed_date = timezone.now()
        self.save()

    def resubscribe(self):
        """Mark subscriber as active again."""
        self.is_active = True
        self.unsubscribed_date = None
        self.save()

    @property
    def full_name(self):
        """Return full name if available, otherwise email."""
        if self.first_name and self.last_name:
            return f"{self.first_name} {self.last_name}"
        elif self.first_name:
            return self.first_name
        return self.email

    def get_unsubscribe_url(self, request=None):
        """Generate unsubscribe URL for this subscriber."""
        if request:
            return request.build_absolute_uri(
                reverse('newsletter_unsubscribe', kwargs={'token': self.unsubscribe_token})
            )
        return f"/forms/newsletter/unsubscribe/{self.unsubscribe_token}/"


class NewsletterSignupPage(BasePage):
    """
    Unified page for newsletter signup and unsubscribe with email validation.
    """
    template = "pages/newsletter_signup_page.html"
    
    introduction = RichTextField(
        blank=True,
        features=["bold", "italic", "link"],
        help_text="Introduction text displayed above the signup form"
    )
    thank_you_text = RichTextField(
        blank=True,
        help_text="Text displayed after successful signup"
    )
    unsubscribe_success_text = RichTextField(
        blank=True,
        help_text="Text displayed after successful unsubscribe"
    )
    resubscribe_text = RichTextField(
        blank=True,
        help_text="Text displayed with resubscribe option"
    )
    email_placeholder = models.CharField(
        max_length=100,
        default="Enter your email address",
        help_text="Placeholder text for email field"
    )
    first_name_placeholder = models.CharField(
        max_length=100,
        default="First name (optional)",
        help_text="Placeholder text for first name field"
    )
    last_name_placeholder = models.CharField(
        max_length=100,
        default="Last name (optional)",
        help_text="Placeholder text for last name field"
    )
    submit_button_text = models.CharField(
        max_length=50,
        default="Subscribe to Newsletter",
        help_text="Text for the submit button"
    )
    unsubscribe_button_text = models.CharField(
        max_length=50,
        default="Unsubscribe",
        help_text="Text for the unsubscribe button"
    )
    show_name_fields = models.BooleanField(
        default=True,
        help_text="Show first name and last name fields"
    )
    require_names = models.BooleanField(
        default=False,
        help_text="Make first name and last name required fields"
    )

    content_panels = BasePage.content_panels + [
        FieldPanel('introduction'),
        FieldPanel('thank_you_text'),
        FieldPanel('unsubscribe_success_text'),
        FieldPanel('resubscribe_text'),
        MultiFieldPanel([
            FieldPanel('email_placeholder'),
            FieldPanel('first_name_placeholder'),
            FieldPanel('last_name_placeholder'),
            FieldPanel('submit_button_text'),
            FieldPanel('unsubscribe_button_text'),
        ], heading="Form Settings"),
        MultiFieldPanel([
            FieldPanel('show_name_fields'),
            FieldPanel('require_names'),
        ], heading="Field Options"),
    ]

    class Meta:
        verbose_name = "Newsletter Page"

    def get_context(self, request, *args, **kwargs):
        context = super().get_context(request, *args, **kwargs)
        
        if request.method == 'POST':
            action = request.POST.get('action', 'subscribe')
            email = request.POST.get('email', '').strip()
            first_name = request.POST.get('first_name', '').strip()
            last_name = request.POST.get('last_name', '').strip()
            email_validator = EmailValidator()
            try:
                email_validator(email)
            except ValidationError:
                context['error'] = "Please enter a valid email address."
                context['form_data'] = {
                    'email': email,
                    'first_name': first_name,
                    'last_name': last_name
                }
                return context
            
            if action == 'unsubscribe':
                try:
                    subscriber = NewsletterSubscriber.objects.get(email=email)
                    if subscriber.is_active:
                        subscriber.unsubscribe()
                        context['unsubscribed'] = True
                        context['message'] = self.unsubscribe_success_text or "You have been unsubscribed from our newsletter."
                    else:
                        context['error'] = "This email is already unsubscribed."
                except NewsletterSubscriber.DoesNotExist:
                    context['error'] = "This email is not subscribed to our newsletter."
                context['form_data'] = {
                    'email': email,
                    'first_name': first_name,
                    'last_name': last_name
                }
                return context
            else:  # subscribe
                if NewsletterSubscriber.objects.filter(email=email).exists():
                    subscriber = NewsletterSubscriber.objects.get(email=email)
                    if subscriber.is_active:
                        context['error'] = "This email is already subscribed to our newsletter."
                    else:
                        # Resubscribe
                        subscriber.resubscribe()
                        context['success'] = True
                        context['message'] = self.thank_you_text or "Thank you for resubscribing to our newsletter!"
                else:
                    # Create new subscriber
                    subscriber = NewsletterSubscriber.objects.create(
                        email=email,
                        first_name=first_name if self.show_name_fields else '',
                        last_name=last_name if self.show_name_fields else '',
                        source="website"
                    )
                    context['success'] = True
                    context['message'] = self.thank_you_text or "Thank you for subscribing to our newsletter!"
        return context
