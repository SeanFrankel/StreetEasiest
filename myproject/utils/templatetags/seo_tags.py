from django import template
from django.utils.html import format_html

register = template.Library()

@register.simple_tag(takes_context=True)
def meta_tags(context):
    page = context.get('page')
    if not page:
        return ''
    
    tags = []
    
    # Basic meta tags
    if hasattr(page, 'listing_summary') and page.listing_summary:
        tags.append(format_html('<meta name="description" content="{}">', page.listing_summary))
    
    # OpenGraph tags
    tags.append(format_html('<meta property="og:title" content="{}">', page.title))
    tags.append('<meta property="og:type" content="website">')
    
    if hasattr(page, 'listing_summary') and page.listing_summary:
        tags.append(format_html('<meta property="og:description" content="{}">', page.listing_summary))
    
    # Image support
    if hasattr(page, 'social_image') and page.social_image:
        tags.append(format_html('<meta property="og:image" content="{}">', page.social_image.get_rendition('original').url))
    elif hasattr(page, 'listing_image') and page.listing_image:
        tags.append(format_html('<meta property="og:image" content="{}">', page.listing_image.get_rendition('original').url))
    
    # Twitter card
    tags.append('<meta name="twitter:card" content="summary_large_image">')
    
    return format_html('\n'.join(tags)) 