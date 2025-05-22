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
from django.conf import settings

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
        campaign = cleaned_data.get('campaign')
        
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
        
        # Always require a campaign
        if not campaign:
            raise ValidationError({'campaign': 'This field is required.'})
        
        return cleaned_data

@admin.register(CampaignLead)
class CampaignLeadAdmin(admin.ModelAdmin):
    form = CampaignLeadForm
    list_display = ('lead', 'campaign', 'is_converted', 'link_count', 'converted_at', 'created_at')
    list_filter = ('is_converted', 'campaign', 'created_at')
    search_fields = ('lead__full_name', 'lead__email', 'campaign__name')
    inlines = [MessageAssignmentInline]
    
    def link_count(self, obj):
        """Count how many links this campaign lead has"""
        count = Link.objects.filter(campaign_lead=obj).count()
        if count > 0:
            return format_html('<a href="/admin/campaign/link/?campaign_lead__id__exact={}">{} links</a>', obj.id, count)
        return "0"
    link_count.short_description = 'Links'
    
    def add_view(self, request, form_url='', extra_context=None):
        # Add lead types and sources to the context
        extra_context = extra_context or {}
        extra_context['lead_types'] = dict(Lead.TYPE_CHOICES)
        extra_context['lead_sources'] = dict(Lead.SOURCE_CHOICES)
        
        # Use custom template
        self.change_form_template = 'admin/campaign/campaignlead/add_form.html'
        
        logger.warning("Rendering add_view with custom template")
        
        # Handle POST request
        if request.method == 'POST':
            lead_type = request.POST.get('lead_type')
            lead_source = request.POST.get('lead_source')
            campaign_id = request.POST.get('campaign')
            lead_id = request.POST.get('lead')
            is_converted = request.POST.get('is_converted') == 'on'
            converted_at = request.POST.get('converted_at')
            
            logger.warning(f"POST data: campaign={campaign_id}, lead_id={lead_id}, lead_type={lead_type}, lead_source={lead_source}")
            
            # Case 1: Using filters to add multiple leads
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
            
            # Case 2: Adding a single lead
            elif campaign_id and lead_id:
                logger.warning(f"Adding single lead: lead_id={lead_id}, campaign_id={campaign_id}")
                try:
                    campaign = Campaign.objects.get(id=campaign_id)
                    lead = Lead.objects.get(id=lead_id)
                    
                    # Check if this lead is already in the campaign
                    if CampaignLead.objects.filter(campaign=campaign, lead=lead).exists():
                        messages.warning(request, f"Lead '{lead.full_name}' is already in campaign '{campaign.name}'")
                        logger.warning(f"Lead {lead.full_name} already exists in campaign")
                    else:
                        # Create the campaign lead
                        CampaignLead.objects.create(
                            campaign=campaign,
                            lead=lead,
                            is_converted=is_converted,
                            converted_at=converted_at if converted_at else None
                        )
                        messages.success(request, f"Successfully added lead '{lead.full_name}' to campaign '{campaign.name}'")
                        logger.warning(f"Successfully added lead {lead.full_name} to campaign")
                    
                    # Redirect to the campaign lead list or to add another
                    if '_addanother' in request.POST:
                        return HttpResponseRedirect(".")
                    else:
                        return HttpResponseRedirect("../")
                except Campaign.DoesNotExist:
                    messages.error(request, "Selected campaign does not exist")
                    logger.error(f"Campaign with ID {campaign_id} does not exist")
                except Lead.DoesNotExist:
                    messages.error(request, "Selected lead does not exist")
                    logger.error(f"Lead with ID {lead_id} does not exist")
                except Exception as e:
                    messages.error(request, f"Error adding lead to campaign: {str(e)}")
                    logger.error(f"Error adding lead to campaign: {str(e)}")
        
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
    create_for_all_leads = forms.BooleanField(
        required=False,
        label="Create for all campaign leads",
        help_text="If checked, a link will be created for each lead in the selected campaign"
    )
    
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
        
        # If this is an existing link, hide the create_for_all_leads field
        if kwargs.get('instance') and kwargs['instance'].pk:
            self.fields['create_for_all_leads'].widget = forms.HiddenInput()
    
    def clean(self):
        cleaned_data = super().clean()
        campaign = cleaned_data.get('campaign')
        campaign_lead = cleaned_data.get('campaign_lead')
        create_for_all_leads = cleaned_data.get('create_for_all_leads')
        
        # If creating for all leads, campaign_lead should be empty
        if create_for_all_leads and campaign_lead:
            self.add_error('campaign_lead', 'Leave this empty when creating links for all campaign leads')
        
        # Validate that campaign is selected if URL or utm_campaign is empty
        if not cleaned_data.get('url') and not campaign:
            self.add_error('campaign', 'Campaign is required when URL is not provided')
        
        if not cleaned_data.get('utm_campaign') and not campaign:
            self.add_error('campaign', 'Campaign is required when UTM Campaign is not provided')
        
        return cleaned_data

@admin.register(Link)
class LinkAdmin(admin.ModelAdmin):
    form = LinkAdminForm
    list_display = ('url', 'campaign', 'campaign_lead', 'purpose', 'tracking_url', 'message_assignments_count', 'visit_count', 'visited_at')
    list_filter = ('campaign', 'purpose', 'visit_count')
    search_fields = ('url', 'utm_campaign', 'ref', 'description')
    
    def tracking_url(self, obj):
        """Display the tracking URL with a copy button"""
        if obj.ref:
            # Use the existing get_redirect_url method
            redirect_url = obj.get_redirect_url()
            full_url = f"{settings.SITE_URL}{redirect_url}" if hasattr(settings, 'SITE_URL') else redirect_url
            return format_html('<a href="{0}" target="_blank">{0}</a>', full_url)
        return "-"
    tracking_url.short_description = 'Tracking URL'
    
    def message_assignments_count(self, obj):
        """Count how many message assignments use this link"""
        count = obj.message_assignments.count()
        if count > 0:
            return format_html('<a href="/admin/campaign/messageassignment/?url__id__exact={}">{} assignments</a>', obj.id, count)
        return "0"
    message_assignments_count.short_description = 'Used in Messages'
    
    def save_model(self, request, obj, form, change):
        create_for_all_leads = form.cleaned_data.get('create_for_all_leads')
        
        if create_for_all_leads and not change:
            # Get the campaign
            campaign = obj.campaign
            
            # Get all campaign leads for this campaign
            campaign_leads = CampaignLead.objects.filter(campaign=campaign)
            
            if campaign_leads.exists():
                # Create a link for each campaign lead
                for campaign_lead in campaign_leads:
                    # Create a new Link object for each lead
                    link = Link(
                        campaign=campaign,
                        campaign_lead=campaign_lead,
                        purpose=obj.purpose,
                        description=obj.description,
                        url=obj.url,
                        utm_source=obj.utm_source,
                        utm_medium=obj.utm_medium,
                        utm_campaign=obj.utm_campaign,
                        utm_term=obj.utm_term,
                        utm_content=obj.utm_content
                    )
                    # Save it to generate unique ref and apply other logic
                    link.save()
                
                # Show a success message
                self.message_user(
                    request, 
                    f"Created {campaign_leads.count()} links for campaign leads in '{campaign.name}'",
                    level=messages.SUCCESS
                )
                
                # Don't save the original object
                return
            else:
                # No campaign leads found
                self.message_user(
                    request,
                    f"No campaign leads found for campaign '{campaign.name}'",
                    level=messages.WARNING
                )
        
        # Normal save for a single link
        super().save_model(request, obj, form, change)






@admin.register(MessageAssignment)
class MessageAssignmentAdmin(admin.ModelAdmin):
    list_display = ('campaign_lead', 'message', 'link_info', 'scheduled_at', 'sent_at', 'responded')
    list_filter = ('responded', 'scheduled_at', 'sent_at')
    search_fields = ('campaign_lead__lead__full_name', 'message__subject')
    
    def link_info(self, obj):
        """Display link information if available"""
        if obj.url:
            visit_count = obj.url.visit_count
            visit_text = f"{visit_count} visit{'s' if visit_count != 1 else ''}"
            return format_html(
                '<a href="/admin/campaign/link/{}/change/">{}</a> ({}) - <a href="{}" target="_blank">View</a>',
                obj.url.id,
                obj.url.ref,
                visit_text,
                obj.url.get_redirect_url()
            )
        return "No link"
    link_info.short_description = 'Tracking Link'







@admin.register(CampaignStats)
class CampaignStatsAdmin(admin.ModelAdmin):
    list_display = ('campaign', 'total_leads', 'total_messages_sent', 'open_rate', 'click_rate', 'conversion_rate')
    readonly_fields = ('open_rate', 'click_rate', 'conversion_rate')

# Customize admin site
admin.site.site_header = "Campaign Automation Dashboard"
admin.site.site_title = "Campaign Management"
admin.site.index_title = "Campaign Analytics & Management"
