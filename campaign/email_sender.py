from django.core.mail import send_mail, EmailMultiAlternatives
from django.conf import settings
from django.utils import timezone
import logging
import html

logger = logging.getLogger(__name__)

def send_campaign_email(message_assignment):
    """
    Send an email for a message assignment with tracking
    
    Args:
        message_assignment: MessageAssignment object to send
        
    Returns:
        bool: True if successful, False otherwise
    """
    try:
        if message_assignment.sent == True:
            return "already sent"
        
        # Get personalized content with tracking URL
        subject = message_assignment.message.subject
        
        # Use personalized content if available, otherwise get default personalized content
        if message_assignment.personlized_msg_to_send:
            content = message_assignment.personlized_msg_to_send
        else:
            content = message_assignment.get_personalized_content()
        
        # Get recipient email
        recipient_email = message_assignment.campaign_lead.lead.email
        recipient_name = message_assignment.campaign_lead.lead.full_name
        
        # Log the email details for debugging
        logger.info(f"Preparing to send email to {recipient_name} <{recipient_email}>")
        logger.info(f"Subject: {subject}")
        logger.info(f"Content: {content[:100]}...")  # Log first 100 chars of content
        
        # Create plain text version (for email clients that don't support HTML)
        plain_text = content
        
        # Create HTML version with proper formatting
        html_content = format_email_as_html(content)
        
        # Create email message with both HTML and plain text versions
        email = EmailMultiAlternatives(
            subject=subject,
            body=plain_text,  # Plain text version
            from_email=settings.DEFAULT_FROM_EMAIL,
            to=[f"{recipient_name} <{recipient_email}>"],
            # reply_to=[settings.DEFAULT_FROM_EMAIL],
        )
        
        # Add HTML version
        email.attach_alternative(html_content, "text/html")
        
        # Send the email
        sent = email.send(fail_silently=False)
        
        # Record that the email was sent if successful
        if sent:
            logger.info(f"Successfully sent email to {recipient_email}")
            message_assignment.sent = True
            message_assignment.sent_at = timezone.now()
            message_assignment.save(update_fields=['sent', 'sent_at'])
            return True
        else:
            logger.error(f"Failed to send email to {recipient_email}")
            return False
            
    except Exception as e:
        logger.error(f"Error sending email: {str(e)}")
        return False

def format_email_as_html(content):
    """
    Format plain text content as HTML with proper line breaks and paragraphs
    
    Args:
        content: Plain text content to format
        
    Returns:
        str: HTML formatted content
    """
    # Escape HTML special characters to prevent injection
    escaped_content = html.escape(content)
    
    # Replace newlines with HTML line breaks
    html_content = escaped_content.replace('\n', '<br>')
    
    # Wrap in HTML structure
    html_content = f"""
    <!DOCTYPE html>
    <html>
    <head>
        <meta charset="UTF-8">
        <meta name="viewport" content="width=device-width, initial-scale=1.0">
        <style>
            body {{
                font-family: Arial, sans-serif;
                line-height: 1.6;
                color: #333333;
                margin: 0;
                padding: 20px;
            }}
            p {{
                margin-bottom: 16px;
            }}
            a {{
                color: #0066cc;
                text-decoration: none;
            }}
            a:hover {{
                text-decoration: underline;
            }}
            .signature {{
                margin-top: 30px;
                border-top: 1px solid #eeeeee;
                padding-top: 10px;
                color: #666666;
            }}
        </style>
    </head>
    <body>
        <div>{html_content}</div>
    </body>
    </html>
    """
    
    return html_content
