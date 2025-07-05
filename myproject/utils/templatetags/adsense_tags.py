from django import template
from django.utils.safestring import mark_safe

register = template.Library()


@register.simple_tag(takes_context=True)
def adsense_head(context):
    """
    Include AdSense head code if enabled.
    Usage: {% adsense_head %}
    """
    try:
        adsense_settings = context['settings'].utils.GoogleAdSenseSettings
        if adsense_settings.enable_adsense and adsense_settings.publisher_id:
            return mark_safe(f'''
                <script async src="https://pagead2.googlesyndication.com/pagead/js/adsbygoogle.js?client={adsense_settings.publisher_id}"
                     crossorigin="anonymous"></script>
            ''')
    except (KeyError, AttributeError):
        pass
    return ''


@register.simple_tag(takes_context=True)
def adsense_ad(context, ad_slot_id, css_class=''):
    """
    Display an AdSense ad.
    Usage: {% adsense_ad '1234567890' %}
    """
    try:
        adsense_settings = context['settings'].utils.GoogleAdSenseSettings
        if not adsense_settings.enable_adsense or not adsense_settings.publisher_id:
            return ''
        
        return mark_safe(f'''
            <div class="adsense-ad {css_class}">
                <ins class="adsbygoogle"
                     style="display:block"
                     data-ad-client="{adsense_settings.publisher_id}"
                     data-ad-slot="{ad_slot_id}"
                     data-ad-format="auto"
                     data-full-width-responsive="true"></ins>
                <script>
                     (adsbygoogle = window.adsbygoogle || []).push({{}});
                </script>
            </div>
        ''')
    except (KeyError, AttributeError):
        return '' 