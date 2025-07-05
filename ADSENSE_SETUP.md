# Simple Google AdSense Setup

This is a minimal Google AdSense integration for your Wagtail website.

## Quick Setup

### 1. Get Your AdSense Publisher ID
1. Go to [Google AdSense](https://www.google.com/adsense)
2. Sign up and wait for approval (1-2 weeks)
3. Get your Publisher ID (format: `ca-pub-1234567890123456`)

### 2. Configure in Wagtail Admin
1. Go to **Settings** → **Google AdSense**
2. Check "Enable AdSense"
3. Enter your Publisher ID
4. Save

### 3. Add Ads to Your Templates

The AdSense script is automatically added to your site. To display ads, just add this to any template:

```django
{% load adsense_tags %}

<!-- Replace '1234567890' with your actual ad slot ID from Google AdSense -->
{% adsense_ad '1234567890' %}
```

## How to Get Ad Slot IDs

1. In your Google AdSense dashboard, go to **Ads** → **By ad unit**
2. Create a new ad unit
3. Copy the "Ad unit ID" (the numbers, not the full code)
4. Use that ID in the `{% adsense_ad 'ID' %}` tag

## Example Usage

```django
<!-- Header ad -->
{% adsense_ad '1234567890' %}

<!-- Sidebar ad -->
{% adsense_ad '9876543210' %}

<!-- Content ad -->
{% adsense_ad '555666777' %}
```

That's it! Your ads will automatically be responsive and work on all devices. 