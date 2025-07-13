# Google AdSense Setup Guide for StreetEasiest

Your website already has a complete Google AdSense integration! Here's how to connect it to Google AdSense.

## ✅ What's Already Set Up

Your website includes:
- **AdSense Settings Model** - Configure Publisher ID and enable/disable ads
- **Template Tags** - `{% adsense_head %}` and `{% adsense_ad 'ID' %}` tags
- **Base Template Integration** - AdSense script automatically included
- **Admin Interface** - Settings available in Wagtail admin
- **Responsive Styling** - CSS for mobile-friendly ad display

## 🚀 Step-by-Step Setup

### 1. Get Your Google AdSense Account

1. Go to [Google AdSense](https://www.google.com/adsense)
2. Click "Get Started" and sign up
3. Wait for approval (1-2 weeks typically)
4. Once approved, get your **Publisher ID** (format: `ca-pub-1234567890123456`)

### 2. Configure AdSense in Wagtail Admin

1. Go to your Wagtail admin panel
2. Navigate to **Settings** → **Google AdSense**
3. Check "Enable AdSense"
4. Enter your Publisher ID
5. Save the settings

### 3. Create Ad Units in Google AdSense

1. In your AdSense dashboard, go to **Ads** → **By ad unit**
2. Click **Create new ad unit**
3. Choose ad type (Display ads recommended)
4. Set size (Responsive recommended)
5. Copy the **Ad unit ID** (just the numbers, e.g., `1234567890`)

### 4. Add Ads to Your Templates

Your article page template has been updated with example ad placements. Here's how to add ads to other templates:

```django
{% load adsense_tags %}

<!-- Header Ad -->
<div class="my-8">
    {% adsense_ad '1234567890' 'header-ad' %}
</div>

<!-- Sidebar Ad -->
<div class="sidebar-ad">
    {% adsense_ad '9876543210' 'sidebar-ad' %}
</div>

<!-- Content Ad -->
<div class="my-8">
    {% adsense_ad '555666777' 'content-ad' %}
</div>
```

## 📍 Recommended Ad Placements

### Article Pages (Already Added)
- **Header Ad** - After introduction, before images
- **Content Ad** - Before main content
- **Footer Ad** - After main content

### Home Page
```django
<!-- Add to templates/pages/home_page.html -->
{% load adsense_tags %}

<!-- Hero Ad -->
<div class="my-8">
    {% adsense_ad '111222333' 'hero-ad' %}
</div>
```

### Rental Trends Page
```django
<!-- Add to templates/pages/rental_trends_page.html -->
{% load adsense_tags %}

<!-- Sidebar Ad -->
<div class="sidebar-ad">
    {% adsense_ad '444555666' 'sidebar-ad' %}
</div>
```

### Search Results
```django
<!-- Add to templates/pages/search_view.html -->
{% load adsense_tags %}

<!-- Search Results Ad -->
<div class="my-8">
    {% adsense_ad '777888999' 'search-ad' %}
</div>
```

## 🎨 Ad Styling

The ads are automatically styled to be:
- **Responsive** - Adapt to mobile and desktop
- **Centered** - Properly aligned in containers
- **Mobile-friendly** - Optimized for small screens
- **Dark mode compatible** - Works with your site's theme

## 📱 Mobile Optimization

Ads automatically resize for mobile devices:
- Desktop: Up to 728px wide
- Mobile: 320px wide
- Sidebar: 300px wide

## 🔧 Troubleshooting

### Ads Not Showing?
1. Check if AdSense is enabled in admin
2. Verify Publisher ID is correct
3. Ensure you're not in preview mode
4. Check browser console for errors

### AdSense Not Approved?
- Ensure your site has original content
- Remove any duplicate content
- Make sure site is publicly accessible
- Follow AdSense policies

### Performance Issues?
- Don't place too many ads (max 3 per page recommended)
- Use responsive ad units
- Test on different devices

## 📊 Best Practices

1. **Don't Overload** - Max 3 ads per page
2. **Strategic Placement** - Above the fold, between content
3. **User Experience** - Don't interfere with navigation
4. **Mobile First** - Test on mobile devices
5. **Compliance** - Follow AdSense policies

## 🚨 Important Notes

- **Wait for Approval** - Don't expect immediate revenue
- **Policy Compliance** - Follow Google's AdSense policies
- **Testing** - Test ads in different browsers and devices
- **Monitoring** - Use AdSense dashboard to track performance

## 📞 Support

If you need help:
1. Check Google AdSense help center
2. Review AdSense policies
3. Test with AdSense's diagnostic tools

Your website is now ready for Google AdSense! 🎉 