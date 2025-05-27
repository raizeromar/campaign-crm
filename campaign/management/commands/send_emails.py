from django.core.management.base import BaseCommand, CommandError
from campaign.models import MessageAssignment
from campaign.tasks import send_email_task, send_campaign_emails_task, send_all_emails_task
import logging

logger = logging.getLogger(__name__)

class Command(BaseCommand):
    help = 'Send emails for message assignments using Celery'

    def add_arguments(self, parser):
        parser.add_argument('--id', type=int, help='ID of a specific message assignment to send')
        parser.add_argument('--all', action='store_true', help='Send all pending emails')
        parser.add_argument('--campaign', type=int, help='Send all emails for a specific campaign')
        parser.add_argument('--include-unpersonalized', action='store_true', help='Include messages without personalized content')
        parser.add_argument('--sync', action='store_true', help='Run synchronously (without Celery)')

    def handle(self, *args, **options):
        message_id = options.get('id')
        all_emails = options.get('all')
        campaign_id = options.get('campaign')
        include_unpersonalized = options.get('include_unpersonalized')
        sync = options.get('sync')
        
        if message_id:
            # Send a specific message
            self.stdout.write(f"Scheduling email sending for message assignment ID {message_id}...")
            
            if sync:
                # Run synchronously
                from campaign.email_sender import send_campaign_email
                message_assignment = MessageAssignment.objects.get(id=message_id)
                success = send_campaign_email(message_assignment)
                if success:
                    self.stdout.write(self.style.SUCCESS(f"Successfully sent email for message assignment ID {message_id}"))
                else:
                    self.stdout.write(self.style.ERROR(f"Failed to send email for message assignment ID {message_id}"))
            else:
                # Run asynchronously with Celery
                task = send_email_task.delay(message_id)
                self.stdout.write(self.style.SUCCESS(f"Scheduled email sending task (ID: {task.id}) for message assignment ID {message_id}"))
                
        elif all_emails:
            # Send all pending emails
            if sync:
                # Count emails that need sending
                query = MessageAssignment.objects.filter(sent=False)
                if not include_unpersonalized:
                    query = query.filter(personlized_msg_to_send__gt='')
                    
                count = query.count()
                self.stdout.write(f"Sending {count} emails synchronously...")
                
                # Process each email synchronously
                from campaign.email_sender import send_campaign_email
                success_count = 0
                for ma in query:
                    try:
                        if send_campaign_email(ma):
                            success_count += 1
                            self.stdout.write(f"Sent {success_count}/{count}")
                    except Exception as e:
                        self.stdout.write(self.style.ERROR(f"Error sending email for message ID {ma.id}: {str(e)}"))
                        
                self.stdout.write(self.style.SUCCESS(f"Successfully sent {success_count}/{count} emails"))
            else:
                # Schedule asynchronous task
                task = send_all_emails_task.delay(not include_unpersonalized)
                self.stdout.write(self.style.SUCCESS(f"Scheduled email sending task (ID: {task.id}) for all pending emails"))
            
        elif campaign_id:
            # Send all emails for a specific campaign
            if sync:
                # Count emails that need sending
                query = MessageAssignment.objects.filter(campaign_id=campaign_id, sent=False)
                if not include_unpersonalized:
                    query = query.filter(personlized_msg_to_send__gt='')
                    
                count = query.count()
                self.stdout.write(f"Sending {count} emails for campaign ID {campaign_id} synchronously...")
                
                # Process each email synchronously
                from campaign.email_sender import send_campaign_email
                success_count = 0
                for ma in query:
                    try:
                        if send_campaign_email(ma):
                            success_count += 1
                            self.stdout.write(f"Sent {success_count}/{count}")
                    except Exception as e:
                        self.stdout.write(self.style.ERROR(f"Error sending email for message ID {ma.id}: {str(e)}"))
                        
                self.stdout.write(self.style.SUCCESS(f"Successfully sent {success_count}/{count} emails for campaign ID {campaign_id}"))
            else:
                # Schedule asynchronous task
                task = send_campaign_emails_task.delay(campaign_id, not include_unpersonalized)
                self.stdout.write(self.style.SUCCESS(f"Scheduled email sending task (ID: {task.id}) for campaign ID {campaign_id}"))
            
        else:
            self.stdout.write(self.style.ERROR("Please specify --id, --all, or --campaign"))