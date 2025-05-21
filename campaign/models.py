from django.db import models
from django.utils import timezone






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
    url = models.URLField()
    utm_source = models.CharField(max_length=100)
    utm_medium = models.CharField(max_length=100)
    utm_campaign = models.CharField(max_length=100)
    utm_term = models.CharField(max_length=100, blank=True)
    utm_content = models.CharField(max_length=100, blank=True)
    ref = models.CharField(max_length=50, help_text="e.g. L12 for Lead #12")

    visited_at = models.DateTimeField(null=True, blank=True)

    def full_url(self):
        # You can compute and return the full URL with all UTM parameters here
        return f"{self.url}?utm_source={self.utm_source}&utm_medium={self.utm_medium}&utm_campaign={self.utm_campaign}&utm_term={self.utm_term}&utm_content={self.utm_content}&ref={self.ref}"













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
