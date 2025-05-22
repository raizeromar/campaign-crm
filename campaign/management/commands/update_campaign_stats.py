from django.core.management.base import BaseCommand
from campaign.models import Campaign, CampaignStats

class Command(BaseCommand):
    help = 'Update statistics for all campaigns'

    def handle(self, *args, **options):
        campaigns = Campaign.objects.all()
        updated = 0
        
        for campaign in campaigns:
            stats, created = CampaignStats.objects.get_or_create(campaign=campaign)
            stats.update_from_campaign()
            updated += 1
            
        self.stdout.write(self.style.SUCCESS(f'Successfully updated stats for {updated} campaigns'))