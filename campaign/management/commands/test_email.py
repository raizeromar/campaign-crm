from django.core.management.base import BaseCommand
from django.core.mail import send_mail, EmailMultiAlternatives
from django.conf import settings
from campaign.models import MessageAssignment
from campaign.email_sender import send_campaign_email
import logging

logger = logging.getLogger(__name__)

class Command(BaseCommand):
    help = 'Test email sending with Zoho Mail'

    def add_arguments(self, parser):
        parser.add_argument('--id', type=int, help='ID of a specific message assignment to send')
        parser.add_argument('--test', action='store_true', help='Send a simple test email')
        parser.add_argument('--recipient', type=str, help='Email address to send test email to')

    def handle(self, *args, **options):
        message_id = options.get('id')
        test = options.get('test')
        recipient = options.get('recipient')
        
        if test:
            if not recipient:
                self.stdout.write(self.style.ERROR("Please provide a recipient email with --recipient"))
                return
                
            self.stdout.write(f"Sending test email to {recipient}...")
            
            try:
                # Simple test email
                subject = "Test Email from Django"
                message = "This is a test email sent from Django using Zoho Mail."
                html_message = "<h1>Test Email</h1><p>This is a <strong>test email</strong> sent from Django using Zoho Mail.</p>"
                
                # Create email message with both HTML and plain text versions
                email = EmailMultiAlternatives(
                    subject=subject,
                    body=message,  # Plain text version
                    from_email=settings.DEFAULT_FROM_EMAIL,
                    to=[recipient],
                    reply_to=[settings.DEFAULT_FROM_EMAIL],
                )
                
                # Add HTML version
                email.attach_alternative(html_message, "text/html")
                
                # Send the email
                sent = email.send(fail_silently=False)
                
                if sent:
                    self.stdout.write(self.style.SUCCESS(f"Successfully sent test email to {recipient}"))
                else:
                    self.stdout.write(self.style.ERROR(f"Failed to send test email to {recipient}"))
                    
            except Exception as e:
                self.stdout.write(self.style.ERROR(f"Error sending test email: {str(e)}"))
                
        elif message_id:
            # Send a specific message
            self.stdout.write(f"Sending email for message assignment ID {message_id}...")
            
            try:
                message_assignment = MessageAssignment.objects.get(id=message_id)
                success = send_campaign_email(message_assignment)
                
                if success:
                    self.stdout.write(self.style.SUCCESS(f"Successfully sent email for message assignment ID {message_id}"))
                else:
                    self.stdout.write(self.style.ERROR(f"Failed to send email for message assignment ID {message_id}"))
                    
            except MessageAssignment.DoesNotExist:
                self.stdout.write(self.style.ERROR(f"Message assignment with ID {message_id} does not exist"))
            except Exception as e:
                self.stdout.write(self.style.ERROR(f"Error sending email: {str(e)}"))
                
        else:
            self.stdout.write(self.style.ERROR("Please specify --id or --test"))