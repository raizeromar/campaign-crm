from django.db import models
from django.utils import timezone
import uuid






class Product(models.Model):
    name = models.CharField(max_length=255)
    description = models.TextField(blank=True)
    landing_page_url = models.URLField(blank=True)

    def __str__(self):
        return self.name







class Campaign(models.Model):
    name = models.CharField(max_length=255)
    short_name = models.SlugField(unique=True)
    product = models.ForeignKey(Product, on_delete=models.CASCADE)
    start_date = models.DateTimeField(default=timezone.now)
    end_date = models.DateTimeField(null=True, blank=True)
    is_active = models.BooleanField(default=True)

    def __str__(self):
        return f"{self.name} - {self.product.name}"









class Lead(models.Model):
    full_name = models.CharField(max_length=255)
    first_name = models.CharField(max_length=100, blank=True)
    last_name = models.CharField(max_length=100, blank=True)
    position = models.CharField(max_length=100, blank=True)
    email = models.EmailField(unique=True)
    phone_number = models.CharField(max_length=20, blank=True)
    linkedin_profile = models.URLField(blank=True)
    
    company_name = models.CharField(max_length=255)
    company_website = models.URLField(blank=True)
    industry = models.CharField(max_length=100, blank=True)
    employee_count = models.CharField(max_length=50, blank=True)

    location= models.CharField(max_length=255, blank=True)

    SOURCE_CHOICES = [
        ("linkedin_scrape", "LinkedIn Scrape"),
        ("social", "Social Media"),
        ("newsletter", "Newsletter Opt-in"),
        ("form", "Free Consultation Form"),
    ]
    TYPE_CHOICES = [
        ("cold", "Cold"),
        ("warm", "Warm"),
        ("hot", "Hot"),
        ("customer", "Customer"),
    ]
    source = models.CharField(max_length=50, choices=SOURCE_CHOICES)
    lead_type = models.CharField(max_length=20, choices=TYPE_CHOICES)

    created_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return f"{self.full_name} - {self.lead_type} -  {self.source}"





class NewsletterSubscriber(models.Model):
    lead = models.ForeignKey(Lead, null=True, blank=True, on_delete=models.SET_NULL)
    joined_at = models.DateTimeField(auto_now_add=True)
    unsubscribed = models.BooleanField(default=False)

    def __str__(self):
        return f"{self.lead.full_name} - {self.lead.email} - {self.joined_at}"





class CampaignLead(models.Model):
    campaign = models.ForeignKey(Campaign, on_delete=models.CASCADE)
    lead = models.ForeignKey(Lead, on_delete=models.CASCADE)

    is_converted= models.BooleanField(default=False)
    converted_at = models.DateTimeField(null=True, blank=True)

    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        unique_together = ('campaign', 'lead')

    def __str__(self):
        return f"{self.lead} - {self.campaign.name}"












class Message(models.Model):
    subject = models.CharField(max_length=255)
    intro = models.TextField(blank=True)
    content = models.TextField()
    cta = models.CharField(max_length=255, blank=True)
    ps = models.TextField(blank=True)
    pps = models.TextField(blank=True)

    def __str__(self):
        return f"{self.subject} - {self.cta}"







class Link(models.Model):
    campaign = models.ForeignKey(Campaign, on_delete=models.CASCADE)
    campaign_lead = models.ForeignKey(CampaignLead, on_delete=models.CASCADE, null=True, blank=True)
    
    # Base URL from product's landing page
    url = models.URLField()
    
    # UTM parameters with defaults
    utm_source = models.CharField(max_length=100, default="email_outreach")
    utm_medium = models.CharField(max_length=100, default="email")
    utm_campaign = models.CharField(max_length=100)  # Will be auto-populated from campaign.short_name
    utm_term = models.CharField(max_length=100, blank=True)
    utm_content = models.CharField(max_length=100, blank=True)
    
    # Reference code for tracking
    ref = models.CharField(max_length=50, unique=True, blank=True, 
                          help_text="Unique reference code for tracking")
    
    # Tracking
    visited_at = models.DateTimeField(null=True, blank=True)
    visit_count = models.IntegerField(default=0)

    def save(self, *args, **kwargs):
        # Auto-populate utm_campaign from campaign short_name if not set
        if not self.utm_campaign and self.campaign:
            self.utm_campaign = self.campaign.short_name
            
        # Generate unique ref if not set
        if not self.ref:
            if self.campaign_lead:
                # Base on campaign lead ID with unique suffix
                base_ref = f"L{self.campaign_lead.lead.id}-CL{self.campaign_lead.id}-C{self.campaign.id}"
                # Add unique suffix to prevent duplicates
                unique_suffix = uuid.uuid4().hex[:6]
                self.ref = f"{base_ref}-{unique_suffix}"
            else:
                # If no campaign lead, generate completely random ref
                self.ref = f"R-{uuid.uuid4().hex[:10]}"
            
        # Auto-populate URL from product if not set
        if not self.url and self.campaign:
            self.url = self.campaign.product.landing_page_url
            
        super().save(*args, **kwargs)
    
    def get_redirect_url(self):
        """Get the Django redirect URL for tracking"""
        from django.urls import reverse
        return reverse('redirect_and_track', kwargs={'ref_code': self.ref})

    def full_url(self):
        # Compute and return the full URL with all UTM parameters
        params = {
            'utm_source': self.utm_source,
            'utm_medium': self.utm_medium,
            'utm_campaign': self.utm_campaign
        }
        
        # Only add non-empty parameters
        if self.utm_term:
            params['utm_term'] = self.utm_term
        if self.utm_content:
            params['utm_content'] = self.utm_content
        if self.ref:
            params['ref'] = self.ref
            
        # Build query string
        query_string = '&'.join([f"{k}={v}" for k, v in params.items()])
        return f"{self.url}?{query_string}"

    def track_visit(self):
        """Record a visit to this link"""
        self.visit_count += 1
        self.visited_at = timezone.now()
        self.save()

    def __str__(self):
        return f"{self.url} - {self.ref}"










class MessageAssignment(models.Model):
    campaign_lead = models.ForeignKey(CampaignLead, on_delete=models.CASCADE)
    message = models.ForeignKey(Message, on_delete=models.CASCADE)
    url = models.ForeignKey(Link, null=True, blank=True, on_delete=models.SET_NULL)

    personlized_msg = models.TextField(blank=True)
    
    scheduled_at = models.DateTimeField(null=True, blank=True)
    sent_at = models.DateTimeField(null=True, blank=True)
    #opened_at = models.DateTimeField(null=True, blank=True)
    #clicked_at = models.DateTimeField(null=True, blank=True)

    responded = models.BooleanField(default=False)
    responded_content = models.TextField(blank=True)

    def __str__(self):
        return f"{self.campaign_lead} - {self.message.subject}"







class CampaignStats(models.Model):
    campaign = models.OneToOneField(Campaign, on_delete=models.CASCADE)

    total_leads = models.IntegerField(default=0)
    total_messages_sent = models.IntegerField(default=0)
    total_opens = models.IntegerField(default=0)
    total_clicks = models.IntegerField(default=0)
    total_conversions = models.IntegerField(default=0)

    best_cta = models.ForeignKey(Link, null=True, blank=True, on_delete=models.SET_NULL, related_name='+')
    best_message = models.ForeignKey(Message, null=True, blank=True, on_delete=models.SET_NULL, related_name='+')

    updated_at = models.DateTimeField(auto_now=True)

    @property
    def open_rate(self):
        return round(self.total_opens / self.total_messages_sent * 100, 2) if self.total_messages_sent else 0

    @property
    def click_rate(self):
        return round(self.total_clicks / self.total_opens * 100, 2) if self.total_opens else 0

    @property
    def conversion_rate(self):
        return round(self.total_conversions / self.total_leads * 100, 2) if self.total_leads else 0

    def __str__(self):
        return f"Stats for {self.campaign.name}"
