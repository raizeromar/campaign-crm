def send_campaign_email(message_assignment):
    """Send an email for a message assignment with tracking"""
    if not message_assignment.url:
        # Create a link if one doesn't exist
        link = Link.objects.create(
            campaign=message_assignment.campaign_lead.campaign,
            campaign_lead=message_assignment.campaign_lead,
            url=message_assignment.campaign_lead.campaign.product.landing_page_url,
            utm_content=f"email_{message_assignment.id}"
        )
        message_assignment.url = link
        message_assignment.save()
    
    # Get personalized content with tracking URL
    subject = message_assignment.message.subject
    content = message_assignment.get_personalized_content()
    
    # Send the email
    # ...
    
    # Record that the email was sent
    message_assignment.sent_at = timezone.now()
    message_assignment.save()