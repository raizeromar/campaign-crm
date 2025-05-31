from import_export import resources
from .models import Lead

class LeadResource(resources.ModelResource):
    class Meta:
        model = Lead
        import_id_fields = ('email',) # Use email as the unique identifier during import
        fields = ('full_name', 'first_name', 'last_name', 'position', 'email', 'phone_number', 'linkedin_profile', 'company_name', 'company_website', 'industry', 'employee_count', 'campany_linkedin_page', 'location', 'source', 'lead_type', 'created_at') 