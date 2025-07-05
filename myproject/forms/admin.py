from django.contrib import admin
from django.http import HttpResponse
from django.utils import timezone
from django.db.models import Q
from .models import NewsletterSubscriber


@admin.register(NewsletterSubscriber)
class NewsletterSubscriberAdmin(admin.ModelAdmin):
    list_display = ['email', 'full_name', 'is_active', 'subscribed_date', 'source']
    list_filter = ['is_active', 'subscribed_date', 'source']
    search_fields = ['email', 'first_name', 'last_name']
    readonly_fields = ['subscribed_date', 'unsubscribed_date', 'unsubscribe_token']
    ordering = ['-subscribed_date']
    
    actions = ['export_active_emails', 'export_all_emails', 'mark_as_unsubscribed', 'mark_as_subscribed']
    
    fieldsets = (
        ('Subscriber Information', {
            'fields': ('email', 'first_name', 'last_name', 'source')
        }),
        ('Subscription Status', {
            'fields': ('is_active', 'subscribed_date', 'unsubscribed_date')
        }),
        ('Technical', {
            'fields': ('unsubscribe_token',),
            'classes': ('collapse',)
        }),
    )
    
    def export_active_emails(self, request, queryset):
        """Export only active subscribers' emails to CSV."""
        response = HttpResponse(content_type='text/csv')
        response['Content-Disposition'] = f'attachment; filename="active_newsletter_subscribers_{timezone.now().strftime("%Y%m%d_%H%M%S")}.csv"'
        
        response.write('Email,First Name,Last Name,Subscribed Date,Source\n')
        
        active_subscribers = queryset.filter(is_active=True)
        for subscriber in active_subscribers:
            response.write(f'"{subscriber.email}","{subscriber.first_name}","{subscriber.last_name}","{subscriber.subscribed_date.strftime("%Y-%m-%d %H:%M:%S")}","{subscriber.source}"\n')
        
        self.message_user(request, f'Successfully exported {active_subscribers.count()} active subscribers.')
        return response
    
    export_active_emails.short_description = "Export active subscribers to CSV"
    
    def export_all_emails(self, request, queryset):
        """Export all subscribers' emails to CSV."""
        response = HttpResponse(content_type='text/csv')
        response['Content-Disposition'] = f'attachment; filename="all_newsletter_subscribers_{timezone.now().strftime("%Y%m%d_%H%M%S")}.csv"'
        
        response.write('Email,First Name,Last Name,Status,Subscribed Date,Unsubscribed Date,Source\n')
        
        for subscriber in queryset:
            status = 'Active' if subscriber.is_active else 'Unsubscribed'
            unsubscribed_date = subscriber.unsubscribed_date.strftime("%Y-%m-%d %H:%M:%S") if subscriber.unsubscribed_date else ''
            response.write(f'"{subscriber.email}","{subscriber.first_name}","{subscriber.last_name}","{status}","{subscriber.subscribed_date.strftime("%Y-%m-%d %H:%M:%S")}","{unsubscribed_date}","{subscriber.source}"\n')
        
        self.message_user(request, f'Successfully exported {queryset.count()} subscribers.')
        return response
    
    export_all_emails.short_description = "Export all subscribers to CSV"
    
    def mark_as_unsubscribed(self, request, queryset):
        """Mark selected subscribers as unsubscribed."""
        updated = queryset.update(is_active=False, unsubscribed_date=timezone.now())
        self.message_user(request, f'Successfully marked {updated} subscribers as unsubscribed.')
    
    mark_as_unsubscribed.short_description = "Mark selected subscribers as unsubscribed"
    
    def mark_as_subscribed(self, request, queryset):
        """Mark selected subscribers as subscribed."""
        updated = queryset.update(is_active=True, unsubscribed_date=None)
        self.message_user(request, f'Successfully marked {updated} subscribers as subscribed.')
    
    mark_as_subscribed.short_description = "Mark selected subscribers as subscribed"
    
    def get_queryset(self, request):
        """Custom queryset to show all subscribers by default."""
        return super().get_queryset(request)
    
    def changelist_view(self, request, extra_context=None):
        """Add custom context for the changelist view."""
        extra_context = extra_context or {}
        
        # Get statistics
        total_subscribers = NewsletterSubscriber.objects.count()
        active_subscribers = NewsletterSubscriber.objects.filter(is_active=True).count()
        unsubscribed_count = NewsletterSubscriber.objects.filter(is_active=False).count()
        
        extra_context.update({
            'total_subscribers': total_subscribers,
            'active_subscribers': active_subscribers,
            'unsubscribed_count': unsubscribed_count,
        })
        
        return super().changelist_view(request, extra_context) 