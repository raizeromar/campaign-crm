from django.db import models
from django.utils import timezone
import uuid
from urllib.parse import urlparse, urlunparse, parse_qs, urlencode
from django.db.models.signals import post_save
from django.dispatch import receiver

class Product(models.Model):
    name = models.CharField(max_length=255)
    description = models.TextField(blank=True)
    landing_page_url = models.URLField(blank=True)

    def clean(self):
        """Clean the model fields before validation"""
        super().clean()
        
        # Clean the landing page URL
        if self.landing_page_url:
            self.landing_page_url = self._normalize_url(self.landing_page_url)
    
    def _normalize_url(self, url):
        """Normalize URL to ensure consistent format"""
        if not url:
            return ""
            
        # Parse the URL into components
        parsed = urlparse(url)
        
        # Normalize path (ensure consistent trailing slash handling)
        path = parsed.path
        if not path:
            path = "/"
        elif path != "/" and not path.endswith("/"):
            # Add trailing slash for consistency
            path = path + "/"
            
        # Rebuild the URL with normalized path
        normalized = urlunparse((
            parsed.scheme,
            parsed.netloc,
            path,
            parsed.params,
            parsed.query,
            parsed.fragment  # Preserve fragment (#) if present
        ))
        
        return normalized
    
    def save(self, *args, **kwargs):
        # Clean the URL before saving
        if self.landing_page_url:
            self.landing_page_url = self._normalize_url(self.landing_page_url)
        
        super().save(*args, **kwargs)

    def __str__(self):
        return self.name







class Campaign(models.Model):
    name = models.CharField(max_length=255)
    short_name = models.SlugField(unique=True, blank=True)
    product = models.ForeignKey(Product, on_delete=models.CASCADE)
    start_date = models.DateTimeField(default=timezone.now)
    end_date = models.DateTimeField(null=True, blank=True)
    is_active = models.BooleanField(default=True)

    def save(self, *args, **kwargs):
        # Generate short_name if not provided
        if not self.short_name:
            # First save to get an ID if this is a new campaign
            if not self.id:
                super().save(*args, **kwargs)
                
            # Get first letter of each word in campaign name
            name_initials = ''.join([word[0].lower() for word in self.name.split() if word])
            
            # Create short_name with campaign ID and initials
            self.short_name = f"c{self.id}-{name_initials}"
            
            # Save again with the generated short_name
            kwargs['force_insert'] = False
            
        super().save(*args, **kwargs)

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
    campany_linkedin_page= models.URLField(blank=True)

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

    def save(self, *args, **kwargs):
        # Auto-populate first_name and last_name from full_name if not set
        if self.full_name and (not self.first_name or not self.last_name):
            name_parts = self.full_name.strip().split()
            
            if len(name_parts) > 0:
                # First name is the first part
                self.first_name = name_parts[0]
                
                # Last name is everything else (including middle names)
                if len(name_parts) > 1:
                    self.last_name = ' '.join(name_parts[1:])
        
        super().save(*args, **kwargs)

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

    def convert(self):
        """Mark this lead as converted"""
        if not self.is_converted:
            self.is_converted = True
            self.converted_at = timezone.now()
            self.save()
            
            # Update campaign stats
            stats, created = CampaignStats.objects.get_or_create(campaign=self.campaign)
            stats.update_from_campaign()
            
            return True
        return False












class Message(models.Model):
    product = models.ForeignKey(Product, on_delete=models.CASCADE)
    subject = models.CharField(max_length=255)
    intro = models.TextField(blank=True)
    content = models.TextField()
    cta = models.CharField(max_length=255, blank=True)
    ps = models.TextField(blank=True)
    pps = models.TextField(blank=True)

    def __str__(self):
        return f"{self.subject}"







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

    def clean_url(self):
        """Normalize the URL to prevent issues with trailing slashes and fragments"""
        if not self.url:
            return ""
            
        # Parse the URL into components
        parsed = urlparse(self.url)
        
        # Normalize path (ensure consistent trailing slash handling)
        path = parsed.path
        if not path:
            path = "/"
        elif path != "/" and not path.endswith("/"):
            # Add trailing slash for consistency
            path = path + "/"
            
        # Rebuild the URL with normalized path
        normalized = urlunparse((
            parsed.scheme,
            parsed.netloc,
            path,
            parsed.params,
            parsed.query,
            parsed.fragment  # Preserve fragment (#) if present
        ))
        
        return normalized
    
    def save(self, *args, **kwargs):
        # Normalize the URL before saving
        if self.url:
            self.url = self.clean_url()
            
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
        """Get the full URL with all UTM parameters while preserving fragments"""
        if not self.url:
            return ""
            
        # Parse the base URL
        parsed = urlparse(self.url)
        
        # Get existing query parameters
        query_params = parse_qs(parsed.query)
        
        # Add UTM parameters
        utm_params = {
            'utm_source': self.utm_source,
            'utm_medium': self.utm_medium,
            'utm_campaign': self.utm_campaign
        }
        
        # Only add non-empty parameters
        if self.utm_term:
            utm_params['utm_term'] = self.utm_term
        if self.utm_content:
            utm_params['utm_content'] = self.utm_content
        if self.ref:
            utm_params['ref'] = self.ref
            
        # Update query parameters with UTM parameters
        query_params.update(utm_params)
        
        # Convert query parameters to string
        query_string = urlencode(query_params, doseq=True)
        
        # Rebuild the URL with the new query string, preserving the fragment
        result = urlunparse((
            parsed.scheme,
            parsed.netloc,
            parsed.path,
            parsed.params,
            query_string,
            parsed.fragment  # Preserve fragment (#) if present
        ))
        
        return result

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

    def get_tracking_url(self):
        """Get the tracking URL for this message assignment"""
        if self.url:
            return self.url.get_redirect_url()
        return ""
    
    def get_personalized_content(self):
        """Get the personalized message content with tracking URL"""
        content = self.personlized_msg or self.message.content
        
        # Replace placeholders with actual values
        if self.campaign_lead and self.campaign_lead.lead:
            lead = self.campaign_lead.lead
            content = content.replace('{first_name}', lead.first_name)
            content = content.replace('{last_name}', lead.last_name)
            content = content.replace('{company}', lead.company_name)
        
        # Replace CTA placeholder with tracking URL if available
        if self.url:
            tracking_url = self.get_tracking_url()
            content = content.replace('{cta_url}', tracking_url)
        
        return content

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
        
    @property
    def click_to_conversion_rate(self):
        return round(self.total_conversions / self.total_clicks * 100, 2) if self.total_clicks else 0

    def update_from_campaign(self):
        """Update stats based on campaign data"""
        # Count leads
        self.total_leads = self.campaign.campaignlead_set.count()
        
        # Count messages sent
        message_assignments = MessageAssignment.objects.filter(
            campaign_lead__campaign=self.campaign,
            sent_at__isnull=False
        )
        self.total_messages_sent = message_assignments.count()
        
        # Count clicks (from link visits)
        links = Link.objects.filter(campaign=self.campaign)
        self.total_clicks = sum(link.visit_count for link in links)
        
        # Count conversions
        self.total_conversions = self.campaign.campaignlead_set.filter(
            is_converted=True
        ).count()
        
        # Find best performing CTA (link with most visits)
        if links.exists():
            self.best_cta = links.order_by('-visit_count').first()
        
        # Find best performing message (most clicks)
        if message_assignments.exists():
            # Group by message and count clicks
            message_clicks = {}
            for ma in message_assignments:
                if ma.url and ma.url.visit_count > 0:
                    message_id = ma.message_id
                    if message_id in message_clicks:
                        message_clicks[message_id] += ma.url.visit_count
                    else:
                        message_clicks[message_id] = ma.url.visit_count
            
            # Find message with most clicks
            if message_clicks:
                best_message_id = max(message_clicks, key=message_clicks.get)
                self.best_message_id = best_message_id
        
        self.save()

    def __str__(self):
        return f"Stats for {self.campaign.name}"

@receiver(post_save, sender=Link)
def update_campaign_stats_on_link_visit(sender, instance, **kwargs):
    """Update campaign stats when a link is visited"""
    if instance.visit_count > 0 and instance.campaign:
        # Get or create campaign stats
        stats, created = CampaignStats.objects.get_or_create(campaign=instance.campaign)
        
        # Update stats
        stats.update_from_campaign()
        
        # If this link is associated with a campaign lead, check for conversion
        if instance.campaign_lead and instance.campaign_lead.is_converted:
            # This could be a good place to trigger conversion tracking
            pass
