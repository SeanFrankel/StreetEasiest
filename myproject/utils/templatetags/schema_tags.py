from django import template
import json
from django.utils.html import format_html

register = template.Library()

@register.simple_tag(takes_context=True)
def page_schema(context):
    page = context.get('page')
    if not page:
        return ''
    
    # Basic schema for all pages
    schema = {
        "@context": "https://schema.org",
        "@type": "WebPage",
        "name": page.title,
    }
    
    # Add description if available
    if hasattr(page, 'listing_summary') and page.listing_summary:
        schema["description"] = page.listing_summary
    
    # Add image if available
    if hasattr(page, 'listing_image') and page.listing_image:
        schema["image"] = page.listing_image.get_rendition('original').url
    
    # Special handling for article pages
    if page.__class__.__name__ == 'ArticlePage':
        schema["@type"] = "Article"
        if hasattr(page, 'author') and page.author:
            schema["author"] = {
                "@type": "Person",
                "name": page.author.name
            }
        if hasattr(page, 'publication_date') and page.publication_date:
            schema["datePublished"] = page.publication_date.isoformat()
    
    return format_html('<script type="application/ld+json">{}</script>', json.dumps(schema)) 