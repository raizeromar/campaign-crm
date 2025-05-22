from django import forms
from django.contrib import admin
from django.utils.html import format_html
from django.db.models import Count, Sum
from django.contrib.admin import SimpleListFilter
from django.http import HttpResponseRedirect
from django.contrib import messages
from django.core.exceptions import ValidationError
from .models import (
    Product, Campaign, Lead, NewsletterSubscriber,
    CampaignLead, Message, Link, MessageAssignment, CampaignStats
)
import logging

# Configure logger
logger = logging.getLogger(__name__)

# Inline models for related objects
class CampaignLeadInline(admin.TabularInline):
    model = CampaignLead
    extra = 0
    fields = ('lead', 'is_converted', 'converted_at')

class MessageAssignmentInline(admin.TabularInline):
    model = MessageAssignment
    extra = 0
    fields = ('message', 'scheduled_at', 'responded')

# Custom filter for Campaign selection
class CampaignFilter(SimpleListFilter):
    title = 'campaign'
    parameter_name = 'campaign'

    def lookups(self, request, model_admin):
        campaigns = Campaign.objects.all()
        return [(c.id, c.name) for c in campaigns]

    def queryset(self, request, queryset):
        if self.value():
            return queryset
        return queryset

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
    
    def add_to_campaign(self, request, queryset):
        # Get the campaign ID from the request
        campaign_id = request.POST.get('campaign')
        
        if not campaign_id:
            self.message_user(request, "No campaign selected", level=messages.ERROR)
            return
            
        try:
            campaign = Campaign.objects.get(id=campaign_id)
            
            # Count how many leads were added
            added_count = 0
            already_exists_count = 0
            
            for lead in queryset:
                # Try to create the campaign lead, handle duplicates
                try:
                    CampaignLead.objects.create(campaign=campaign, lead=lead)
                    added_count += 1
                except Exception:  # Handle unique constraint violation
                    already_exists_count += 1
            
            # Show success message
            if added_count > 0:
                self.message_user(
                    request, 
                    f"Successfully added {added_count} leads to campaign '{campaign.name}'",
                    level=messages.SUCCESS
                )
            
            if already_exists_count > 0:
                self.message_user(
                    request,
                    f"{already_exists_count} leads were already in the campaign",
                    level=messages.WARNING
                )
                
        except Campaign.DoesNotExist:
            self.message_user(request, "Selected campaign does not exist", level=messages.ERROR)
        
    add_to_campaign.short_description = "Add selected leads to campaign"
    
    def changelist_view(self, request, extra_context=None):
        # Add campaigns to the context for the dropdown
        extra_context = extra_context or {}
        extra_context['campaigns'] = Campaign.objects.all()
        return super().changelist_view(request, extra_context=extra_context)

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






# Custom form for CampaignLead
class CampaignLeadForm(forms.ModelForm):
    class Meta:
        model = CampaignLead
        fields = '__all__'
    
    def clean(self):
        cleaned_data = super().clean()
        lead = cleaned_data.get('lead')
        
        # Get filter values from POST data
        lead_type = self.data.get('lead_type')
        lead_source = self.data.get('lead_source')
        
        logger.warning(f"FORM VALIDATION: lead={lead}, lead_type={lead_type}, lead_source={lead_source}")
        
        # If filters are used, lead field is not required
        if lead_type or lead_source:
            self.fields['lead'].required = False
            if 'lead' in self._errors:
                del self._errors['lead']
            logger.warning("Using filters, lead field not required")
        elif not lead:
            # If no filters and no lead, raise validation error
            logger.warning("No filters and no lead, raising validation error")
            raise ValidationError({'lead': 'This field is required when not using filters.'})
        
        return cleaned_data

@admin.register(CampaignLead)
class CampaignLeadAdmin(admin.ModelAdmin):
    form = CampaignLeadForm
    list_display = ('lead', 'campaign', 'is_converted', 'converted_at', 'created_at')
    list_filter = ('is_converted', 'campaign', 'created_at')
    search_fields = ('lead__full_name', 'lead__email', 'campaign__name')
    inlines = [MessageAssignmentInline]
    
    def add_view(self, request, form_url='', extra_context=None):
        # Add lead types and sources to the context
        extra_context = extra_context or {}
        extra_context['lead_types'] = dict(Lead.TYPE_CHOICES)
        extra_context['lead_sources'] = dict(Lead.SOURCE_CHOICES)
        
        # Use custom template
        self.change_form_template = 'admin/campaign/campaignlead/add_form.html'
        
        logger.warning("Rendering add_view with custom template")
        
        # Handle POST request with filters
        if request.method == 'POST':
            lead_type = request.POST.get('lead_type')
            lead_source = request.POST.get('lead_source')
            campaign_id = request.POST.get('campaign')
            is_converted = request.POST.get('is_converted') == 'on'
            converted_at = request.POST.get('converted_at')
            
            logger.warning(f"POST data: campaign={campaign_id}, lead_type={lead_type}, lead_source={lead_source}")
            
            # If using filters and we have a campaign
            if (lead_type or lead_source) and campaign_id:
                # Build query based on filters
                query = {}
                if lead_type:
                    query['lead_type'] = lead_type
                if lead_source:
                    query['source'] = lead_source
                
                logger.warning(f"Query filters: {query}")
                
                # Get all leads matching the filters
                leads = Lead.objects.filter(**query)
                logger.warning(f"Found {leads.count()} leads matching filters")
                
                if not leads.exists():
                    logger.warning("No leads match the selected filters")
                    messages.warning(request, "No leads match the selected filters.")
                else:
                    # Create campaign leads for each matching lead
                    campaign = Campaign.objects.get(id=campaign_id)
                    added_count = 0
                    already_exists_count = 0
                    
                    for lead in leads:
                        logger.warning(f"Processing lead: {lead.full_name} (ID: {lead.id})")
                        # Check if this lead is already in the campaign
                        if CampaignLead.objects.filter(campaign=campaign, lead=lead).exists():
                            already_exists_count += 1
                            logger.warning(f"Lead {lead.full_name} already exists in campaign")
                            continue
                        
                        try:
                            CampaignLead.objects.create(
                                campaign=campaign,
                                lead=lead,
                                is_converted=is_converted,
                                converted_at=converted_at if converted_at else None
                            )
                            added_count += 1
                            logger.warning(f"Successfully added lead {lead.full_name} to campaign")
                        except Exception as e:
                            logger.error(f"Error adding lead {lead.full_name}: {str(e)}")
                    
                    # Show messages
                    if added_count > 0:
                        success_msg = f"Successfully added {added_count} leads to campaign '{campaign.name}'"
                        messages.success(request, success_msg)
                        logger.warning(success_msg)
                    
                    if already_exists_count > 0:
                        warning_msg = f"{already_exists_count} leads were already in the campaign"
                        messages.warning(request, warning_msg)
                        logger.warning(warning_msg)
                    
                    # Redirect to the campaign lead list
                    return HttpResponseRedirect("../")
        
        return super().add_view(request, form_url, extra_context)
    
    def save_model(self, request, obj, form, change):
        logger.warning(f"SAVE_MODEL called: change={change}")
        
        # For normal saves (not using filters), save normally
        super().save_model(request, obj, form, change)






@admin.register(Message)
class MessageAdmin(admin.ModelAdmin):
    list_display = ('subject', 'product', 'cta', 'message_preview')
    search_fields = ('subject', 'content', 'cta')
    
    def message_preview(self, obj):
        if len(obj.content) > 50:
            return obj.content[:50] + "..."
        return obj.content
    message_preview.short_description = 'Content Preview'










class LinkAdminForm(forms.ModelForm):
    class Meta:
        model = Link
        fields = '__all__'
    
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        # Make URL and utm_campaign not required in the form
        self.fields['url'].required = False
        self.fields['utm_campaign'].required = False
        
        # Update help text to be more clear
        self.fields['url'].help_text = "Will be auto-populated from campaign's product landing page if left empty"
        self.fields['utm_campaign'].help_text = "Will be auto-populated from campaign's short_name if left empty"
    
    def clean(self):
        cleaned_data = super().clean()
        campaign = cleaned_data.get('campaign')
        
        # Validate that campaign is selected if URL or utm_campaign is empty
        if not cleaned_data.get('url') and not campaign:
            self.add_error('campaign', 'Campaign is required when URL is not provided')
        
        if not cleaned_data.get('utm_campaign') and not campaign:
            self.add_error('campaign', 'Campaign is required when UTM Campaign is not provided')
        
        return cleaned_data

@admin.register(Link)
class LinkAdmin(admin.ModelAdmin):
    form = LinkAdminForm
    list_display = ('url', 'utm_campaign', 'utm_source', 'utm_medium', 'ref', 'visited_at')
    list_filter = ('utm_source', 'utm_medium', 'visited_at')
    search_fields = ('url', 'utm_campaign', 'ref')
    
    def save_model(self, request, obj, form, change):
        # Make sure the URL and utm_campaign are populated before saving
        if not obj.url and obj.campaign:
            obj.url = obj.campaign.product.landing_page_url
        
        if not obj.utm_campaign and obj.campaign:
            obj.utm_campaign = obj.campaign.short_name
        
        super().save_model(request, obj, form, change)






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
