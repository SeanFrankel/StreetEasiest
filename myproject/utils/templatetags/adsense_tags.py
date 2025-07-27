from django import template
from django.utils.safestring import mark_safe

register = template.Library()

@register.simple_tag(takes_context=True)
def adsense_head(context):
    """
    Include Google AdSense Auto Ads script and initialization.
    Usage: {% adsense_head %}
    """
    try:
        # Access your Wagtail Site Settings via the 'settings' context
        adsense_settings = context['settings'].utils.GoogleAdSenseSettings
        enabled = getattr(adsense_settings, 'enable_adsense', False)
        pid = getattr(adsense_settings, 'publisher_id', '')
    except (KeyError, AttributeError):
        return ''

    if not enabled or not pid:
        return ''

    # Page‑level (Auto) Ads script + init
    return mark_safe(f"""
<script async src="https://pagead2.googlesyndication.com/pagead/js/adsbygoogle.js?client={pid}" crossorigin="anonymous"></script>
<script>
    (adsbygoogle = window.adsbygoogle || []).push({{
        google_ad_client: "{pid}",
        enable_page_level_ads: true
    }});
</script>
""")

@register.simple_tag(takes_context=True)
def adsense_ad(context, ad_slot_id, css_class=''):
    """
    Display an AdSense ad unit.
    Usage: {% adsense_ad '1234567890' 'my-css-class' %}
    """
    try:
        adsense_settings = context['settings'].utils.GoogleAdSenseSettings
        enabled = getattr(adsense_settings, 'enable_adsense', False)
        pid = getattr(adsense_settings, 'publisher_id', '')
    except (KeyError, AttributeError):
        return ''

    if not enabled or not pid:
        return ''

    return mark_safe(f"""
<div class="adsense-ad {css_class}">
    <ins class="adsbygoogle"
         style="display:block"
         data-ad-client="{pid}"
         data-ad-slot="{ad_slot_id}"
         data-ad-format="auto"
         data-full-width-responsive="true"></ins>
    <script>
         (adsbygoogle = window.adsbygoogle || []).push({{}});
    </script>
</div>
""")
