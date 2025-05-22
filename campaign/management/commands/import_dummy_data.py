from django.core.management.base import BaseCommand
from campaign.models import Product, Lead

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