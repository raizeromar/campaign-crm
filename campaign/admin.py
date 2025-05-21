from django.contrib import admin
from django.utils.html import format_html
from django.db.models import Count, Sum
from .models import (
    Product, Campaign, Lead, NewsletterSubscriber,
    CampaignLead, Message, Link, MessageAssignment, CampaignStats
)

# Inline models for related objects
class CampaignLeadInline(admin.TabularInline):
    model = CampaignLead
    extra = 0
    fields = ('lead', 'is_converted', 'converted_at')

class MessageAssignmentInline(admin.TabularInline):
    model = MessageAssignment
    extra = 0
    fields = ('message', 'scheduled_at', 'responded')

# Custom admin classes
@admin.register(Product)
class ProductAdmin(admin.ModelAdmin):
    list_display = ('name', 'campaign_count', 'landing_page_link')
    search_fields = ('name', 'description')
    
    def campaign_count(self, obj):
        return obj.campaign_set.count()
    campaign_count.short_description = 'Campaigns'
    
    def landing_page_link(self, obj):
        if obj.landing_page_url:
            return format_html('<a href="{}" target="_blank">View Landing Page</a>', obj.landing_page_url)
        return "-"
    landing_page_link.short_description = 'Landing Page'

@admin.register(Campaign)
class CampaignAdmin(admin.ModelAdmin):
    list_display = ('name', 'product', 'start_date', 'end_date', 'is_active', 'lead_count', 'conversion_rate')
    list_filter = ('is_active', 'product', 'start_date')
    search_fields = ('name', 'short_name', 'product__name')
    prepopulated_fields = {'short_name': ('name',)}
    inlines = [CampaignLeadInline]
    
    def lead_count(self, obj):
        return obj.campaignlead_set.count()
    lead_count.short_description = 'Leads'
    
    def conversion_rate(self, obj):
        try:
            stats = obj.campaignstats
            return f"{stats.conversion_rate}%"
        except CampaignStats.DoesNotExist:
            return "0%"
    conversion_rate.short_description = 'Conversion'

@admin.register(Lead)
class LeadAdmin(admin.ModelAdmin):
    list_display = ('full_name', 'email', 'company_name', 'lead_type', 'source', 'campaign_count')
    list_filter = ('lead_type', 'source', 'created_at')
    search_fields = ('full_name', 'email', 'company_name')
    fieldsets = (
        ('Personal Information', {
            'fields': ('full_name', 'first_name', 'last_name', 'position', 'email', 'phone_number', 'linkedin_profile')
        }),
        ('Company Information', {
            'fields': ('company_name', 'company_website', 'industry', 'employee_count')
        }),
        ('Lead Details', {
            'fields': ('source', 'lead_type')
        }),
    )
    
    def campaign_count(self, obj):
        return obj.campaignlead_set.count()
    campaign_count.short_description = 'Campaigns'

@admin.register(NewsletterSubscriber)
class NewsletterSubscriberAdmin(admin.ModelAdmin):
    list_display = ('lead_name', 'lead_email', 'joined_at', 'unsubscribed')
    list_filter = ('unsubscribed', 'joined_at')
    search_fields = ('lead__full_name', 'lead__email')
    
    def lead_name(self, obj):
        return obj.lead.full_name if obj.lead else "-"
    lead_name.short_description = 'Name'
    
    def lead_email(self, obj):
        return obj.lead.email if obj.lead else "-"
    lead_email.short_description = 'Email'

@admin.register(CampaignLead)
class CampaignLeadAdmin(admin.ModelAdmin):
    list_display = ('lead', 'campaign', 'is_converted', 'converted_at', 'created_at')
    list_filter = ('is_converted', 'campaign', 'created_at')
    search_fields = ('lead__full_name', 'lead__email', 'campaign__name')
    inlines = [MessageAssignmentInline]

@admin.register(Message)
class MessageAdmin(admin.ModelAdmin):
    list_display = ('subject', 'cta', 'message_preview')
    search_fields = ('subject', 'content', 'cta')
    
    def message_preview(self, obj):
        if len(obj.content) > 50:
            return obj.content[:50] + "..."
        return obj.content
    message_preview.short_description = 'Content Preview'

@admin.register(Link)
class LinkAdmin(admin.ModelAdmin):
    list_display = ('url', 'utm_campaign', 'utm_source', 'utm_medium', 'ref', 'visited_at')
    list_filter = ('utm_source', 'utm_medium', 'visited_at')
    search_fields = ('url', 'utm_campaign', 'ref')

@admin.register(MessageAssignment)
class MessageAssignmentAdmin(admin.ModelAdmin):
    list_display = ('campaign_lead', 'message', 'scheduled_at', 'responded')
    list_filter = ('responded', 'scheduled_at')
    search_fields = ('campaign_lead__lead__full_name', 'message__subject')

@admin.register(CampaignStats)
class CampaignStatsAdmin(admin.ModelAdmin):
    list_display = ('campaign', 'total_leads', 'total_messages_sent', 'open_rate', 'click_rate', 'conversion_rate')
    readonly_fields = ('open_rate', 'click_rate', 'conversion_rate')

# Customize admin site
admin.site.site_header = "Campaign Automation Dashboard"
admin.site.site_title = "Campaign Management"
admin.site.index_title = "Campaign Analytics & Management"
