from django.core.management.base import BaseCommand
from campaign.models import Product, Lead, Message

class Command(BaseCommand):
    help = 'Import dummy data for testing'

    def handle(self, *args, **options):
        # Create product
        product, created = Product.objects.get_or_create(
            name="Cold Outreach Agent",
            defaults={
                'landing_page_url': "https://gatara.org/products/#cold-outreach"
            }
        )
        
        if created:
            self.stdout.write(self.style.SUCCESS(f'Created product: {product.name}'))
        else:
            self.stdout.write(self.style.WARNING(f'Product already exists: {product.name}'))
        
        # Create leads
        leads_data = [
            {
                'full_name': 'Work Omar',
                'email': 'fdudramo@gmail.com',
                'position': 'CEO',
                'company_name': 'SDO',
                'source': 'linkedin_scrape',
                'lead_type': 'cold',
            },
            {
                'full_name': 'Fdud Ramo',
                'email': 'woomarrk@gmail.com',
                'position': 'CEO',
                'company_name': 'Woomark',
                'source': 'linkedin_scrape',
                'lead_type': 'warm',
            },
        ]
        
        for lead_data in leads_data:
            lead, created = Lead.objects.get_or_create(
                email=lead_data['email'],
                defaults=lead_data
            )
            
            if created:
                self.stdout.write(self.style.SUCCESS(f'Created lead: {lead.full_name}'))
            else:
                self.stdout.write(self.style.WARNING(f'Lead already exists: {lead.full_name}'))




        # Create messages
        messages_data = [
            {
                'product': product,
                'subject': 'Welcome to our platform',
                'intro': 'Welcome message intro text here.',
                'content': 'Hello {first_name},\n\nWe are excited to welcome you to {company}. This is the main content of our welcome message.',
                'cta': 'Get Started Now',
                'ps': 'P.S. Feel free to reply to this email if you have any questions.',
                'pps': 'P.P.S. Check out our resources page for more information.'
            },
            {
                'product': product,
                'subject': 'Onboarding: Next steps with our platform',
                'intro': 'Onboarding message intro text here.',
                'content': 'Hello {first_name},\n\nIt\'s time to get you fully onboarded with {company}. Here are the next steps you should take.',
                'cta': 'Complete Your Profile',
                'ps': 'P.S. Our support team is available 24/7 to help you.',
                'pps': 'P.P.S. Don\'t forget to schedule your onboarding call.'
            },
            {
                'product': product,
                'subject': 'Outboarding: Thank you for your time',
                'intro': 'Outboarding message intro text here.',
                'content': 'Hello {first_name},\n\nWe\'re sorry to see you go from {company}. We appreciate the time you spent with us.',
                'cta': 'Provide Feedback',
                'ps': 'P.S. You can reactivate your account anytime within 30 days.',
                'pps': 'P.P.S. We\'d love to hear what we could have done better.'
            }
        ]
        
        for message_data in messages_data:
            message, created = Message.objects.get_or_create(
                subject=message_data['subject'],
                product=message_data['product'],
                defaults={
                    'intro': message_data['intro'],
                    'content': message_data['content'],
                    'cta': message_data['cta'],
                    'ps': message_data['ps'],
                    'pps': message_data['pps']
                }
            )
            
            if created:
                self.stdout.write(self.style.SUCCESS(f'Created message: {message.subject}'))
            else:
                self.stdout.write(self.style.WARNING(f'Message already exists: {message.subject}'))        
