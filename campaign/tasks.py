from celery import shared_task, chain
from django.utils import timezone
from django.conf import settings
import logging
from datetime import timedelta
from .models import MessageAssignment

logger = logging.getLogger(__name__)

# Rate limits - these could be moved to settings.py for easier configuration
EMAIL_RATE_LIMIT_PER_DAY = getattr(settings, 'EMAIL_RATE_LIMIT_PER_DAY', 50)
AI_RATE_LIMIT_PER_MINUTE = getattr(settings, 'AI_RATE_LIMIT_PER_MINUTE', 15)

def get_emails_sent_today():
    """
    Count how many emails have been sent today
    
    Returns:
        int: Number of emails sent today
    """
    today = timezone.now().date()
    return MessageAssignment.objects.filter(
        sent=True,
        sent_at__date=today
    ).count()

def can_send_more_emails_today():
    """
    Check if we can send more emails today based on the rate limit
    
    Returns:
        bool: True if we can send more emails, False otherwise
    """
    emails_sent = get_emails_sent_today()
    return emails_sent < EMAIL_RATE_LIMIT_PER_DAY

def get_remaining_email_quota():
    """
    Get the number of emails we can still send today
    
    Returns:
        int: Number of emails we can still send today
    """
    emails_sent = get_emails_sent_today()
    return max(0, EMAIL_RATE_LIMIT_PER_DAY - emails_sent)

@shared_task(rate_limit=f"{AI_RATE_LIMIT_PER_MINUTE}/m")
def personalize_message_task(message_assignment_id, skip=True):
    """
    Celery task to personalize a message using AI and save it to the database.
    Rate limited to respect AI API limits.
    
    Args:
        message_assignment_id: ID of the MessageAssignment to personalize
        skip: If True, skip AI and use simple replacement
        
    Returns:
        bool: True if successful, False otherwise
    """
    try:
        # Get the message assignment
        message_assignment = MessageAssignment.objects.get(id=message_assignment_id)
        
        # Use the model's method to personalize
        success = message_assignment.personalize_with_ai(skip=skip)
        
        if success:
            logger.info(f"Successfully personalized message for assignment ID {message_assignment_id}")
        else:
            logger.error(f"Failed to personalize message for assignment ID {message_assignment_id}")
            
        return success
        
    except MessageAssignment.DoesNotExist:
        logger.error(f"MessageAssignment with ID {message_assignment_id} does not exist")
        return False
    except Exception as e:
        logger.error(f"Error personalizing message: {str(e)}")
        return False

@shared_task
def personalize_campaign_messages_task(campaign_id, force=False):
    """
    Celery task to personalize all messages for a campaign.
    
    Args:
        campaign_id: ID of the Campaign
        force: Whether to force personalization even if already personalized
        
    Returns:
        dict: Results of the operation
    """
    try:
        # Get all message assignments for this campaign
        query = MessageAssignment.objects.filter(campaign_id=campaign_id)
        if not force:
            query = query.filter(personlized_msg_to_send='')
            
        count = query.count()
        logger.info(f"Personalizing {count} message assignments for campaign ID {campaign_id}")
        
        # Create a task for each message assignment
        for message_assignment in query:
            personalize_message_task.delay(message_assignment.id)
            
        return {
            'status': 'success',
            'message': f'Scheduled personalization for {count} messages',
            'campaign_id': campaign_id
        }
        
    except Exception as e:
        logger.error(f"Error scheduling personalization tasks: {str(e)}")
        return {
            'status': 'error',
            'message': str(e),
            'campaign_id': campaign_id
        }

@shared_task
def personalize_all_messages_task(force=False):
    """
    Celery task to personalize all messages in the system.
    
    Args:
        force: Whether to force personalization even if already personalized
        
    Returns:
        dict: Results of the operation
    """
    try:
        # Get all message assignments
        query = MessageAssignment.objects.all()
        if not force:
            query = query.filter(personlized_msg_to_send='')
            
        count = query.count()
        logger.info(f"Personalizing {count} message assignments")
        
        # Create a task for each message assignment
        for message_assignment in query:
            personalize_message_task.delay(message_assignment.id)
            
        return {
            'status': 'success',
            'message': f'Scheduled personalization for {count} messages'
        }
        
    except Exception as e:
        logger.error(f"Error scheduling personalization tasks: {str(e)}")
        return {
            'status': 'error',
            'message': str(e)
        }

@shared_task
def send_email_task(message_assignment_id):
    """
    Celery task to send an email for a message assignment.
    Respects daily email sending limits.
    
    Args:
        message_assignment_id: ID of the MessageAssignment to send
        
    Returns:
        str/bool: "rate_limit_exceeded" if rate limit exceeded, True if successful, False otherwise
    """
    try:
        # Check if we can send more emails today
        if not can_send_more_emails_today():
            logger.warning(f"Email rate limit exceeded ({EMAIL_RATE_LIMIT_PER_DAY}/day). Cannot send message ID {message_assignment_id}")
            return "rate_limit_exceeded"
        
        # Get the message assignment
        message_assignment = MessageAssignment.objects.get(id=message_assignment_id)
        
        # Check if it has personalized content and hasn't been sent
        if not message_assignment.personlized_msg_to_send:
            logger.error(f"Message assignment ID {message_assignment_id} has no personalized content")
            return False
                
        if message_assignment.sent:
            logger.warning(f"Message assignment ID {message_assignment_id} has already been sent")
            return "already sent"
        
        # Send the email using the existing function
        from campaign.email_sender import send_campaign_email
        success = send_campaign_email(message_assignment)
        
        return success
        
    except MessageAssignment.DoesNotExist:
        logger.error(f"MessageAssignment with ID {message_assignment_id} does not exist")
        return False
    except Exception as e:
        logger.error(f"Error sending email: {str(e)}")
        return False

@shared_task
def send_campaign_emails_task(campaign_id, only_personalized=True):
    """
    Celery task to send emails for all message assignments in a campaign.
    
    Args:
        campaign_id: ID of the Campaign
        only_personalized: Only send emails that have personalized content
        
    Returns:
        dict: Results of the operation
    """
    try:
        # Get all message assignments for this campaign that haven't been sent
        query = MessageAssignment.objects.filter(
            campaign_id=campaign_id,
            sent=False
        )
        
        if only_personalized:
            query = query.filter(personlized_msg_to_send__gt='')
            
        count = query.count()
        logger.info(f"Sending {count} emails for campaign ID {campaign_id}")
        
        # Create a task for each message assignment
        for message_assignment in query:
            send_email_task.delay(message_assignment.id)
            
        return {
            'status': 'success',
            'message': f'Scheduled sending for {count} emails',
            'campaign_id': campaign_id
        }
        
    except Exception as e:
        logger.error(f"Error scheduling email sending tasks: {str(e)}")
        return {
            'status': 'error',
            'message': str(e),
            'campaign_id': campaign_id
        }

@shared_task
def send_all_emails_task(only_personalized=True):
    """
    Celery task to send all pending emails in the system.
    
    Args:
        only_personalized: Only send emails that have personalized content
        
    Returns:
        dict: Results of the operation
    """
    try:
        # Get all message assignments that haven't been sent
        query = MessageAssignment.objects.filter(sent=False)
        
        if only_personalized:
            query = query.filter(personlized_msg_to_send__gt='')
            
        count = query.count()
        logger.info(f"Sending {count} emails")
        
        # Create a task for each message assignment
        for message_assignment in query:
            send_email_task.delay(message_assignment.id)
            
        return {
            'status': 'success',
            'message': f'Scheduled sending for {count} emails'
        }
        
    except Exception as e:
        logger.error(f"Error scheduling email sending tasks: {str(e)}")
        return {
            'status': 'error',
            'message': str(e)
        }

@shared_task
def personalize_and_send_message_task(message_assignment_id, skip=True):
    """
    Celery task to personalize a message and then send it immediately if rate limits allow.
    
    Args:
        message_assignment_id: ID of the MessageAssignment to personalize and send
        skip: If True, skip AI and use simple replacement
        
    Returns:
        dict: Results of the operation
    """
    try:
        # Get the message assignment
        message_assignment = MessageAssignment.objects.get(id=message_assignment_id)
        
        # Use the model's method to personalize
        success = message_assignment.personalize_with_ai(skip=skip)
        
        if success:
            logger.info(f"Successfully personalized message for assignment ID {message_assignment_id}")
            
            # Check if we can send more emails today
            if can_send_more_emails_today():
                # Immediately send the email
                from campaign.email_sender import send_campaign_email
                send_result = send_campaign_email(message_assignment)
                
                if send_result is True:
                    logger.info(f"Successfully sent email for assignment ID {message_assignment_id}")
                    return {
                        'status': 'success',
                        'message': 'Successfully personalized and sent email',
                        'assignment_id': message_assignment_id
                    }
                else:
                    logger.error(f"Failed to send email for assignment ID {message_assignment_id}")
                    return {
                        'status': 'partial_success',
                        'message': 'Personalized but failed to send email',
                        'assignment_id': message_assignment_id
                    }
            else:
                logger.warning(f"Email rate limit exceeded ({EMAIL_RATE_LIMIT_PER_DAY}/day). Message ID {message_assignment_id} personalized but not sent")
                return {
                    'status': 'partial_success',
                    'message': 'Personalized but not sent due to rate limit',
                    'assignment_id': message_assignment_id,
                    'reason': 'rate_limit_exceeded'
                }
        else:
            logger.error(f"Failed to personalize message for assignment ID {message_assignment_id}")
            return {
                'status': 'error',
                'message': 'Failed to personalize message',
                'assignment_id': message_assignment_id
            }
            
    except MessageAssignment.DoesNotExist:
        logger.error(f"MessageAssignment with ID {message_assignment_id} does not exist")
        return {
            'status': 'error',
            'message': f"MessageAssignment with ID {message_assignment_id} does not exist",
            'assignment_id': message_assignment_id
        }
    except Exception as e:
        logger.error(f"Error personalizing and sending message: {str(e)}")
        return {
            'status': 'error',
            'message': str(e),
            'assignment_id': message_assignment_id
        }

@shared_task
def personalize_campaign_messages_and_send_task(campaign_id, force=False):
    """
    Celery task to personalize all messages for a campaign and send them immediately if rate limits allow.
    
    Args:
        campaign_id: ID of the Campaign
        force: Whether to force personalization even if already personalized
        
    Returns:
        dict: Results of the operation
    """
    try:
        # Get all message assignments for this campaign
        query = MessageAssignment.objects.filter(campaign_id=campaign_id, sent=False)
        if not force:
            query = query.filter(personlized_msg_to_send='')
            
        count = query.count()
        logger.info(f"Personalizing and sending {count} message assignments for campaign ID {campaign_id}")
        
        # Check how many emails we can send today
        remaining_quota = get_remaining_email_quota()
        
        if remaining_quota == 0:
            logger.warning(f"Email rate limit reached ({EMAIL_RATE_LIMIT_PER_DAY}/day). Will personalize but not send any emails.")
        elif remaining_quota < count:
            logger.warning(f"Email rate limit will be reached. Can only send {remaining_quota} of {count} emails today.")
        
        # Create a task for each message assignment
        for message_assignment in query:
            personalize_and_send_message_task.delay(message_assignment.id)
            
        return {
            'status': 'success',
            'message': f'Scheduled personalization and sending for {count} messages',
            'campaign_id': campaign_id,
            'email_quota_remaining': remaining_quota
        }
        
    except Exception as e:
        logger.error(f"Error scheduling personalization and sending tasks: {str(e)}")
        return {
            'status': 'error',
            'message': str(e),
            'campaign_id': campaign_id
        }
