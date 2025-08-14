from django import template
from django.utils.safestring import mark_safe
import json

register = template.Library()

@register.simple_tag(takes_context=True)
def consent_mode_head(context):
    """
    Include Google Consent Mode v2 script for EEA/UK traffic compliance.
    Usage: {% consent_mode_head %}
    """
    try:
        consent_settings = context['settings'].utils.ConsentModeSettings
        enabled = getattr(consent_settings, 'enable_consent_mode', False)
        google_tag_id = getattr(consent_settings, 'google_tag_id', '')
        default_state = getattr(consent_settings, 'default_consent_state', 'denied')
        region_detection = getattr(consent_settings, 'enable_region_detection', True)
    except (KeyError, AttributeError):
        return ''

    if not enabled or not google_tag_id:
        return ''

    # EEA/UK countries for region detection
    eea_countries = [
        'AT', 'BE', 'BG', 'HR', 'CY', 'CZ', 'DK', 'EE', 'FI', 'FR', 'DE', 'GR', 'HU', 
        'IE', 'IT', 'LV', 'LT', 'LU', 'MT', 'NL', 'PL', 'PT', 'RO', 'SK', 'SI', 'ES', 'SE'
    ]
    uk_countries = ['GB']

    consent_script = f"""
<script>
// Google Consent Mode v2 Configuration
window.dataLayer = window.dataLayer || [];
function gtag() {{dataLayer.push(arguments);}}

// Default consent state
gtag('consent', 'default', {{
    'ad_storage': '{default_state}',
    'ad_user_data': '{default_state}',
    'ad_personalization': '{default_state}',
    'analytics_storage': '{default_state}',
    'functionality_storage': '{default_state}',
    'personalization_storage': '{default_state}',
    'security_storage': 'granted'
}});

// Region detection for EEA/UK users
"""

    if region_detection:
        consent_script += f"""
// Detect EEA/UK users and update consent accordingly
(function() {{
    // This is a simplified detection - in production, you might want to use a more robust solution
    const userCountry = navigator.language.split('-')[1] || '';
    const eeaCountries = {json.dumps(eea_countries)};
    const ukCountries = {json.dumps(uk_countries)};
    
    if (eeaCountries.includes(userCountry) || ukCountries.includes(userCountry)) {{
        // EEA/UK users - require explicit consent
        gtag('consent', 'update', {{
            'ad_storage': 'denied',
            'ad_user_data': 'denied',
            'ad_personalization': 'denied',
            'analytics_storage': 'denied',
            'functionality_storage': 'denied',
            'personalization_storage': 'denied'
        }});
    }}
}})();
"""

    consent_script += f"""
// Load Google Tag Manager or Analytics
gtag('js', new Date());
gtag('config', '{google_tag_id}');
</script>
<script async src="https://www.googletagmanager.com/gtag/js?id={google_tag_id}"></script>
"""

    return mark_safe(consent_script)


@register.simple_tag(takes_context=True)
def consent_banner(context):
    """
    Display a consent banner for EEA/UK users.
    Usage: {% consent_banner %}
    """
    try:
        consent_settings = context['settings'].utils.ConsentModeSettings
        enabled = getattr(consent_settings, 'enable_consent_mode', False)
        region_detection = getattr(consent_settings, 'enable_region_detection', True)
    except (KeyError, AttributeError):
        return ''

    if not enabled:
        return ''

    banner_html = """
<div id="consent-banner" class="fixed bottom-0 left-0 right-0 bg-white border-t border-gray-200 p-4 z-50 hidden">
    <div class="max-w-7xl mx-auto flex flex-col md:flex-row items-center justify-between gap-4">
        <div class="flex-1">
            <p class="text-sm text-gray-700">
                We use cookies and similar technologies to provide you with the best experience on our website. 
                By continuing to use this site, you consent to our use of cookies and data collection for advertising purposes.
            </p>
        </div>
        <div class="flex gap-3">
            <button id="consent-accept" class="bg-blue-600 text-white px-4 py-2 rounded text-sm hover:bg-blue-700 transition-colors">
                Accept All
            </button>
            <button id="consent-decline" class="bg-gray-200 text-gray-700 px-4 py-2 rounded text-sm hover:bg-gray-300 transition-colors">
                Decline
            </button>
        </div>
    </div>
</div>

<script>
document.addEventListener('DOMContentLoaded', function() {
    const banner = document.getElementById('consent-banner');
    const acceptBtn = document.getElementById('consent-accept');
    const declineBtn = document.getElementById('consent-decline');
    
    // Check if consent has already been given
    if (localStorage.getItem('consent-given')) {
        return;
    }
    
    // Show banner for EEA/UK users (simplified detection)
    const userCountry = navigator.language.split('-')[1] || '';
    const eeaCountries = ['AT', 'BE', 'BG', 'HR', 'CY', 'CZ', 'DK', 'EE', 'FI', 'FR', 'DE', 'GR', 'HU', 'IE', 'IT', 'LV', 'LT', 'LU', 'MT', 'NL', 'PL', 'PT', 'RO', 'SK', 'SI', 'ES', 'SE'];
    const ukCountries = ['GB'];
    
    if (eeaCountries.includes(userCountry) || ukCountries.includes(userCountry)) {
        banner.classList.remove('hidden');
    }
    
    acceptBtn.addEventListener('click', function() {
        gtag('consent', 'update', {
            'ad_storage': 'granted',
            'ad_user_data': 'granted',
            'ad_personalization': 'granted',
            'analytics_storage': 'granted',
            'functionality_storage': 'granted',
            'personalization_storage': 'granted'
        });
        localStorage.setItem('consent-given', 'accepted');
        banner.classList.add('hidden');
    });
    
    declineBtn.addEventListener('click', function() {
        gtag('consent', 'update', {
            'ad_storage': 'denied',
            'ad_user_data': 'denied',
            'ad_personalization': 'denied',
            'analytics_storage': 'denied',
            'functionality_storage': 'denied',
            'personalization_storage': 'denied'
        });
        localStorage.setItem('consent-given', 'declined');
        banner.classList.add('hidden');
    });
});
</script>
"""

    return mark_safe(banner_html) 