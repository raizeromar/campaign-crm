from celery import shared_task
import logging
from .models import MessageAssignment

logger = logging.getLogger(__name__)

@shared_task
def personalize_message_task(message_assignment_id, skip=True):
    """
    Celery task to personalize a message using AI and save it to the database.
    
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
    
    Args:
        message_assignment_id: ID of the MessageAssignment to send
        
    Returns:
        bool: True if successful, False otherwise
    """
    try:
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
