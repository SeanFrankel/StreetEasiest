from django.urls import path
from django.shortcuts import render, get_object_or_404
from django.http import Http404
from .models import NewsletterSubscriber, NewsletterSignupPage


def newsletter_unsubscribe_view(request, token):
    """
    Handle newsletter unsubscribe functionality.
    """
    try:
        subscriber = NewsletterSubscriber.objects.get(unsubscribe_token=token)
    except NewsletterSubscriber.DoesNotExist:
        raise Http404("Invalid unsubscribe link")
    
    # Get the first NewsletterSignupPage for the template
    newsletter_page = NewsletterSignupPage.objects.first()
    if not newsletter_page:
        # Create a default context if no page exists
        context = {
            'page': {
                'title': 'Newsletter',
                'introduction': '',
                'unsubscribe_success_text': '',
                'resubscribe_text': ''
            }
        }
    else:
        context = {'page': newsletter_page}
    
    if request.method == 'POST' and 'resubscribe' in request.POST:
        subscriber.resubscribe()
        context['resubscribed'] = True
        context['message'] = "You have been successfully resubscribed to our newsletter!"
    else:
        subscriber.unsubscribe()
        context['unsubscribed'] = True
        context['subscriber'] = subscriber
        context['message'] = context['page'].unsubscribe_success_text or "You have been successfully unsubscribed from our newsletter."
    
    return render(request, 'pages/newsletter_signup_page.html', context)


urlpatterns = [
    path('newsletter/unsubscribe/<str:token>/', 
         newsletter_unsubscribe_view, 
         name='newsletter_unsubscribe'),
] 