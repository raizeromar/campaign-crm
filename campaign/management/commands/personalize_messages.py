from django.core.management.base import BaseCommand, CommandError
from campaign.models import MessageAssignment
from campaign.ai_service import personalize_and_save_message
import logging

logger = logging.getLogger(__name__)

class Command(BaseCommand):
    help = 'Personalize messages using AI and save them to the database'

    def add_arguments(self, parser):
        parser.add_argument('--id', type=int, help='ID of a specific message assignment to personalize')
        parser.add_argument('--all', action='store_true', help='Personalize all message assignments that need it')
        parser.add_argument('--campaign', type=int, help='Personalize all message assignments for a specific campaign')
        parser.add_argument('--force', action='store_true', help='Force personalization even if already personalized')

    def handle(self, *args, **options):
        message_id = options.get('id')
        all_messages = options.get('all')
        campaign_id = options.get('campaign')
        force = options.get('force')
        
        if message_id:
            # Personalize a specific message
            self.stdout.write(f"Personalizing message assignment ID {message_id}...")
            success = personalize_and_save_message(message_id)
            if success:
                self.stdout.write(self.style.SUCCESS(f"Successfully personalized message assignment ID {message_id}"))
            else:
                self.stdout.write(self.style.ERROR(f"Failed to personalize message assignment ID {message_id}"))
                
        elif all_messages:
            # Personalize all messages that need it
            query = MessageAssignment.objects.all()
            if not force:
                query = query.filter(personlized_msg_to_send='')
                
            count = query.count()
            self.stdout.write(f"Personalizing {count} message assignments...")
            
            success_count = 0
            for ma in query:
                try:
                    if personalize_and_save_message(ma.id):
                        success_count += 1
                        self.stdout.write(f"Personalized {success_count}/{count}")
                except Exception as e:
                    self.stdout.write(self.style.ERROR(f"Error personalizing message ID {ma.id}: {str(e)}"))
                    
            self.stdout.write(self.style.SUCCESS(f"Successfully personalized {success_count}/{count} message assignments"))
            
        elif campaign_id:
            # Personalize all messages for a specific campaign
            query = MessageAssignment.objects.filter(campaign_id=campaign_id)
            if not force:
                query = query.filter(personlized_msg_to_send='')
                
            count = query.count()
            self.stdout.write(f"Personalizing {count} message assignments for campaign ID {campaign_id}...")
            
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
            self.stdout.write(self.style.ERROR("Please specify --id, --all, or --campaign"))