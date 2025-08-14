# Google Ads Compliance Implementation Guide

This guide provides step-by-step instructions to fix Google Ads policy violations and ensure compliance.

## ✅ Completed Fixes

### 1. Privacy Policy Implementation
- ✅ Created `PrivacyPolicyPage` model with comprehensive sections
- ✅ Added privacy policy template with proper structure
- ✅ Added privacy policy link to footer
- ✅ Created `TermsOfServicePage` model and template

### 2. Google Consent Mode v2 for EEA/UK Traffic
- ✅ Created `ConsentModeSettings` model for configuration
- ✅ Implemented consent mode template tags
- ✅ Added region detection for EEA/UK users
- ✅ Integrated consent banner with accept/decline options
- ✅ Added consent mode scripts to base template

### 3. ads.txt File
- ✅ Created `ads.txt` file with publisher ID: `ca-pub-5539267642012864`

## 🔧 Required Actions

### 1. Run Database Migrations
```bash
python manage.py makemigrations
python manage.py migrate
```

### 2. Remove Unlicensed Images (Manual)
1. Go to **Images** in Wagtail Admin
2. Search for and identify unlicensed images:
   - `frank.png` (Seinfeld character)
   - `George_Costanza_with_a_baseball_bat.jpg` (Seinfeld character)
   - Any other Seinfeld stills, memes, or unlicensed content
3. Delete these images from the media library
4. Replace with licensed stock photos or your own graphics

### 3. Enhance Thin Pages (Manual)
1. Review all pages in your site for insufficient content
2. Add substantive, original content to each page
3. Ensure each page provides real value to users
4. Focus on pages that currently have minimal content

### 4. Configure Consent Mode (Wagtail Admin)
1. Go to **Settings** → **Consent Mode Settings**
2. Enable "Enable Consent Mode"
3. Enter your Google Tag Manager ID or Google Analytics 4 ID
4. Set default consent state (recommended: "denied")
5. Enable region detection
6. Save settings

### 5. Create Privacy Policy Content (Wagtail Admin)
1. Create a new **Privacy Policy Page** under your site structure
2. Add comprehensive content including:
   - **Privacy Policy**: Data collection, usage, and user rights
   - **Cookie Policy**: Detailed cookie information
   - **AdSense Policy**: Information about Google AdSense and data sharing
   - **User Choices**: Opt-out options and data control
   - **Contact Information**: How to reach you about privacy concerns

### 6. Create Terms of Service Content (Wagtail Admin)
1. Create a new **Terms of Service Page** under your site structure
2. Add comprehensive content including:
   - **Terms of Service**: Usage rights and restrictions
   - **User Obligations**: Acceptable use policies
   - **Intellectual Property**: Rights and licensing information
   - **Limitation of Liability**: Disclaimers and liability limits
   - **Contact Information**: How to reach you about terms

## 📋 Privacy Policy Content Template

Here's a suggested structure for your privacy policy:

### Privacy Policy Section
- Information we collect
- How we use your information
- Data sharing practices
- Data retention policies
- Your rights under applicable laws

### Cookie Policy Section
- Types of cookies we use
- Purpose of each cookie type
- How to manage cookie preferences
- Third-party cookies (including Google AdSense)

### AdSense Policy Section
- Google AdSense integration
- Data collection for advertising
- Personalized ads
- Ad preferences and opt-out options
- Google's privacy practices

### User Choices Section
- How to opt out of data collection
- Managing advertising preferences
- Accessing and deleting your data
- Contact methods for privacy requests

### Contact Information Section
- Email address for privacy inquiries
- Physical address (if applicable)
- Response time commitments
- Escalation procedures

## 🔍 Verification Checklist

Before submitting for Google Ads review:

- [ ] Privacy policy is accessible from every page (footer link)
- [ ] Privacy policy includes all required sections
- [ ] Terms of service page is created and linked
- [ ] Consent mode is properly configured and working
- [ ] ads.txt file is accessible at `/ads.txt`
- [ ] All unlicensed images are removed
- [ ] All pages have substantive content (minimum 200+ characters)
- [ ] No placeholder or thin content pages remain
- [ ] Site provides real value to users

## 🚨 Important Notes

1. **Content Quality**: Ensure all content is original and provides genuine value to users
2. **Regular Updates**: Keep privacy policy and terms updated as your practices change
3. **Testing**: Test consent mode functionality with EEA/UK IP addresses
4. **Monitoring**: Regularly check for new unlicensed content
5. **Compliance**: Stay updated with Google's policy changes

## 📞 Support

If you encounter issues:
1. Check the Django logs for errors
2. Verify all migrations are applied
3. Test consent mode in different regions
4. Ensure all template tags are properly loaded

## 🔄 Maintenance

Regular tasks to maintain compliance:
- Monthly content quality audits
- Quarterly privacy policy reviews
- Annual terms of service updates
- Continuous monitoring for policy violations 