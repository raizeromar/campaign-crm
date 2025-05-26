from django.core.management.base import BaseCommand, CommandError
from campaign.models import MessageAssignment
from campaign.tasks import personalize_message_task, personalize_campaign_messages_task, personalize_all_messages_task
import logging

logger = logging.getLogger(__name__)

class Command(BaseCommand):
    help = 'Personalize messages using AI and save them to the database (using Celery)'

    def add_arguments(self, parser):
        parser.add_argument('--id', type=int, help='ID of a specific message assignment to personalize')
        parser.add_argument('--all', action='store_true', help='Personalize all message assignments that need it')
        parser.add_argument('--campaign', type=int, help='Personalize all message assignments for a specific campaign')
        parser.add_argument('--force', action='store_true', help='Force personalization even if already personalized')
        parser.add_argument('--sync', action='store_true', help='Run synchronously (without Celery)')

    def handle(self, *args, **options):
        message_id = options.get('id')
        all_messages = options.get('all')
        campaign_id = options.get('campaign')
        force = options.get('force')
        sync = options.get('sync')
        
        if message_id:
            # Personalize a specific message
            self.stdout.write(f"Scheduling personalization for message assignment ID {message_id}...")
            
            if sync:
                # Run synchronously
                from campaign.ai_service import personalize_and_save_message
                success = personalize_and_save_message(message_id)
                if success:
                    self.stdout.write(self.style.SUCCESS(f"Successfully personalized message assignment ID {message_id}"))
                else:
                    self.stdout.write(self.style.ERROR(f"Failed to personalize message assignment ID {message_id}"))
            else:
                # Run asynchronously with Celery
                task = personalize_message_task.delay(message_id)
                self.stdout.write(self.style.SUCCESS(f"Scheduled personalization task (ID: {task.id}) for message assignment ID {message_id}"))
                
        elif all_messages:
            # Personalize all messages that need it
            if sync:
                # Count messages that need personalization
                query = MessageAssignment.objects.all()
                if not force:
                    query = query.filter(personlized_msg_to_send='')
                    
                count = query.count()
                self.stdout.write(f"Personalizing {count} message assignments synchronously...")
                
                # Process each message synchronously
                from campaign.ai_service import personalize_and_save_message
                success_count = 0
                for ma in query:
                    try:
                        if personalize_and_save_message(ma.id):
                            success_count += 1
                            self.stdout.write(f"Personalized {success_count}/{count}")
                    except Exception as e:
                        self.stdout.write(self.style.ERROR(f"Error personalizing message ID {ma.id}: {str(e)}"))
                        
                self.stdout.write(self.style.SUCCESS(f"Successfully personalized {success_count}/{count} message assignments"))
            else:
                # Schedule asynchronous task
                task = personalize_all_messages_task.delay(force)
                self.stdout.write(self.style.SUCCESS(f"Scheduled personalization task (ID: {task.id}) for all messages"))
            
        elif campaign_id:
            # Personalize all messages for a specific campaign
            if sync:
                # Count messages that need personalization
                query = MessageAssignment.objects.filter(campaign_id=campaign_id)
                if not force:
                    query = query.filter(personlized_msg_to_send='')
                    
                count = query.count()
                self.stdout.write(f"Personalizing {count} message assignments for campaign ID {campaign_id} synchronously...")
                
                # Process each message synchronously
                from campaign.ai_service import personalize_and_save_message
                success_count = 0
                for ma in query:
                    try:
                        if personalize_and_save_message(ma.id):
                            success_count += 1
                            self.stdout.write(f"Personalized {success_count}/{count}")
                    except Exception as e:
                        self.stdout.write(self.style.ERROR(f"Error personalizing message ID {ma.id}: {str(e)}"))
                        
                self.stdout.write(self.style.SUCCESS(f"Successfully personalized {success_count}/{count} message assignments for campaign ID {campaign_id}"))
            else:
                # Schedule asynchronous task
                task = personalize_campaign_messages_task.delay(campaign_id, force)
                self.stdout.write(self.style.SUCCESS(f"Scheduled personalization task (ID: {task.id}) for campaign ID {campaign_id}"))
            
        else:
            self.stdout.write(self.style.ERROR("Please specify --id, --all, or --campaign"))
