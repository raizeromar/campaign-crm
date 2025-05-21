from django.db import models
from django.utils import timezone
# from django.contrib.postgres.fields import JSONField


# --------------------------------------
# LEAD & PRODUCT
# --------------------------------------

class Lead(models.Model):
    fullname = models.CharField(max_length=255)
    first_name = models.CharField(max_length=100)
    last_name = models.CharField(max_length=100)
    email = models.EmailField(unique=True)
    phone_number = models.CharField(max_length=30, blank=True, null=True)
    current_position = models.CharField(max_length=150, blank=True)
    linkedin_profile = models.URLField(blank=True)
    company_name = models.CharField(max_length=150, blank=True)
    company_website = models.URLField(blank=True)
    industry = models.CharField(max_length=100, blank=True)
    employee_count = models.CharField(max_length=50, blank=True)  # e.g., "11-50"
    linkedin_company_page = models.URLField(blank=True)
    LEAD_TYPE_CHOICES = [
        ('cold', 'Cold'),
        ('warm', 'Warm'),
        ('outbound', 'Outbound'),
    ]
    lead_type = models.CharField(max_length=20, choices=LEAD_TYPE_CHOICES)

    created_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return self.fullname


class Product(models.Model):
    name = models.CharField(max_length=255)
    description = models.TextField()
    #features = JSONField(blank=True, null=True)  # Optional: structured data

    created_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return self.name


# --------------------------------------
# CAMPAIGN & CAMPAIGN LEAD (M2M)
# --------------------------------------

class Campaign(models.Model):
    name = models.CharField(max_length=255)
    short_name = models.SlugField(unique=True)
    product = models.ForeignKey(Product, on_delete=models.SET_NULL, null=True, blank=True)

    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    def __str__(self):
        return self.name


class CampaignLead(models.Model):
    campaign = models.ForeignKey(Campaign, on_delete=models.CASCADE)
    lead = models.ForeignKey(Lead, on_delete=models.CASCADE)

    STATUS_CHOICES = [
        ('pending', 'Pending'),
        ('sent', 'Sent'),
        ('opened', 'Opened'),
        ('clicked', 'Clicked'),
        ('replied', 'Replied'),
    ]
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default='pending')

    sent_at = models.DateTimeField(null=True, blank=True)
    opened_at = models.DateTimeField(null=True, blank=True)
    clicked_at = models.DateTimeField(null=True, blank=True)
    replied_at = models.DateTimeField(null=True, blank=True)

    def __str__(self):
        return f"{self.campaign.name} - {self.lead.fullname}"


# --------------------------------------
# MESSAGE & ASSIGNMENTS (A/B testing + personalization)
# --------------------------------------

class MessageTemplate(models.Model):
    subject = models.CharField(max_length=255)
    intro = models.TextField()
    body = models.TextField()
    cta = models.TextField(blank=True, null=True)
    ps = models.TextField(blank=True, null=True)
    pps = models.TextField(blank=True, null=True)

    created_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return self.subject


class MessageAssignment(models.Model):
    campaign_lead = models.ForeignKey(CampaignLead, on_delete=models.CASCADE)
    message_template = models.ForeignKey(MessageTemplate, on_delete=models.SET_NULL, null=True)

    rendered_subject = models.CharField(max_length=255)  # final personalized output
    rendered_body = models.TextField()

    created_at = models.DateTimeField(auto_now_add=True)


# --------------------------------------
# LINK & TRACKING
# --------------------------------------

class Link(models.Model):
    base_url = models.URLField()
    utm_source = models.CharField(max_length=100)
    utm_medium = models.CharField(max_length=100)
    utm_campaign = models.CharField(max_length=100)
    utm_term = models.CharField(max_length=100, blank=True)
    utm_content = models.CharField(max_length=100, blank=True)

    def __str__(self):
        return self.base_url


class TrackedLink(models.Model):
    campaign_lead = models.ForeignKey(CampaignLead, on_delete=models.CASCADE)
    link = models.ForeignKey(Link, on_delete=models.CASCADE)

    full_url = models.URLField()  # final url with UTM + ?ref=LeadID
    clicked = models.BooleanField(default=False)
    clicked_at = models.DateTimeField(null=True, blank=True)

    def __str__(self):
        return self.full_url


# --------------------------------------
# ENGAGEMENT TRACKING
# --------------------------------------

class Engagement(models.Model):
    campaign_lead = models.ForeignKey(CampaignLead, on_delete=models.CASCADE)
    event_type = models.CharField(max_length=50, choices=[
        ('open', 'Open'),
        ('click', 'Click'),
        ('reply', 'Reply'),
        ('unsubscribe', 'Unsubscribe'),
    ])
    timestamp = models.DateTimeField(default=timezone.now)
    #metadata = JSONField(blank=True, null=True)  # optional extra data (browser, location, IP, etc.)

    def __str__(self):
        return f"{self.event_type} - {self.campaign_lead.lead.email} - {self.timestamp}"
