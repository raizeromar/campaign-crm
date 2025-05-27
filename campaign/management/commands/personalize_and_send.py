from django.core.management.base import BaseCommand
from campaign.models import MessageAssignment, Campaign
from campaign.tasks import (
    personalize_and_send_message_task,
    personalize_campaign_messages_and_send_task,
    get_remaining_email_quota
)
import logging

logger = logging.getLogger(__name__)

class Command(BaseCommand):
    help = 'Personalize messages using AI and send them immediately (using Celery)'

    def add_arguments(self, parser):
        parser.add_argument('--id', type=int, help='ID of a specific message assignment to personalize and send')
        parser.add_argument('--campaign', type=int, help='Personalize and send all messages for a specific campaign')
        parser.add_argument('--force', action='store_true', help='Force personalization even if already personalized')
        parser.add_argument('--sync', action='store_true', help='Run synchronously (without Celery)')

    def handle(self, *args, **options):
        message_id = options.get('id')
        campaign_id = options.get('campaign')
        force = options.get('force')
        sync = options.get('sync')
        
        # Check remaining email quota
        remaining_quota = get_remaining_email_quota()
        self.stdout.write(f"Remaining email quota for today: {remaining_quota}")
        
        if message_id:
            # Personalize and send a specific message
            self.stdout.write(f"Scheduling personalization and sending for message assignment ID {message_id}...")
            
            if sync:
                # Run synchronously
                from campaign.ai_service import personalize_and_save_message
                from campaign.email_sender import send_campaign_email
                
                message_assignment = MessageAssignment.objects.get(id=message_id)
                
                # Personalize
                personalize_success = personalize_and_save_message(message_id)
                if not personalize_success:
                    self.stdout.write(self.style.ERROR(f"Failed to personalize message assignment ID {message_id}"))
                    return
                
                # Check quota
                if remaining_quota <= 0:
                    self.stdout.write(self.style.WARNING(f"Email rate limit reached. Message personalized but not sent."))
                    return
                
                # Send
                send_success = send_campaign_email(message_assignment)
                if send_success:
                    self.stdout.write(self.style.SUCCESS(f"Successfully personalized and sent message assignment ID {message_id}"))
                else:
                    self.stdout.write(self.style.ERROR(f"Personalized but failed to send message assignment ID {message_id}"))
            else:
                # Run asynchronously with Celery
                task = personalize_and_send_message_task.delay(message_id)
                self.stdout.write(self.style.SUCCESS(f"Scheduled personalization and sending task (ID: {task.id}) for message assignment ID {message_id}"))
                
        elif campaign_id:
            # Personalize and send all messages for a specific campaign
            try:
                campaign = Campaign.objects.get(id=campaign_id)
                
                # Count messages that need personalization
                query = MessageAssignment.objects.filter(campaign_id=campaign_id, sent=False)
                if not force:
                    query = query.filter(personlized_msg_to_send='')
                    
                count = query.count()
                
                if count == 0:
                    self.stdout.write(self.style.WARNING(f"No messages to personalize and send for campaign '{campaign.name}'"))
                    return
                
                self.stdout.write(f"Personalizing and sending {count} message assignments for campaign '{campaign.name}'...")
                
                # Check if we'll hit the rate limit
                if remaining_quota < count:
                    self.stdout.write(self.style.WARNING(
                        f"Email rate limit will be reached. Only {remaining_quota} of {count} emails can be sent today."
                    ))
                
                if sync:
                    # Process each message synchronously
                    from campaign.ai_service import personalize_and_save_message
                    from campaign.email_sender import send_campaign_email
                    
                    personalized_count = 0
                    sent_count = 0
                    
                    for ma in query:
                        try:
                            # Personalize
                            if personalize_and_save_message(ma.id):
                                personalized_count += 1
                                self.stdout.write(f"Personalized {personalized_count}/{count}")
                                
                                # Check if we can send
                                if sent_count < remaining_quota:
                                    # Send
                                    if send_campaign_email(ma):
                                        sent_count += 1
                                        self.stdout.write(f"Sent {sent_count}/{min(count, remaining_quota)}")
                                
                        except Exception as e:
                            self.stdout.write(self.style.ERROR(f"Error processing message ID {ma.id}: {str(e)}"))
                            
                    self.stdout.write(self.style.SUCCESS(
                        f"Successfully personalized {personalized_count}/{count} and sent {sent_count}/{count} "
                        f"message assignments for campaign '{campaign.name}'"
                    ))
                else:
                    # Schedule asynchronous task
                    task = personalize_campaign_messages_and_send_task.delay(campaign_id, force)
                    self.stdout.write(self.style.SUCCESS(
                        f"Scheduled personalization and sending task (ID: {task.id}) for campaign '{campaign.name}'"
                    ))
                
            except Campaign.DoesNotExist:
                self.stdout.write(self.style.ERROR(f"Campaign with ID {campaign_id} does not exist"))
            except Exception as e:
                self.stdout.write(self.style.ERROR(f"Error: {str(e)}"))
            
        else:
            self.stdout.write(self.style.ERROR("Please specify --id or --campaign"))