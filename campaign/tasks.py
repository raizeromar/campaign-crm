from celery import shared_task
import logging
from .models import MessageAssignment

logger = logging.getLogger(__name__)

@shared_task
def personalize_message_task(message_assignment_id):
    """
    Celery task to personalize a message using AI and save it to the database.
    
    Args:
        message_assignment_id: ID of the MessageAssignment to personalize
        
    Returns:
        bool: True if successful, False otherwise
    """
    try:
        # Get the message assignment
        message_assignment = MessageAssignment.objects.get(id=message_assignment_id)
        
        # Use the model's method to personalize
        success = message_assignment.personalize_with_ai()
        
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