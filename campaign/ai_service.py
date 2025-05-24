
import json
from django.conf import settings




def personalize_message(message_assignment):
    """
    Use AI to personalize a message based on lead and campaign data.
    
    Args:
        message_assignment: MessageAssignment object containing the template and related data
        
    Returns:
        str: Personalized message text
    """
    try:
        # Get data needed for personalization
        data = message_assignment.get_ai_personalization_data()
        
        # Convert to proper JSON
        json_string = json.dumps(data, indent=2)
        
        # Write to file for debugging/inspection
        with open('campaign/json.json', 'w') as f:
            f.write(json_string)
            print("Successfully wrote data to campaign/json.json")
        
        # Here you would call your AI service (OpenAI, Anthropic, etc.)
        personalized_text = call_ai_service(data)
        
        return personalized_text
        
    except Exception as e:
        # Return the template as fallback
        return message_assignment.personlized_msg_tmp




















def call_ai_service(data):
    
    # For now, return a simple personalized message as placeholder
    lead_name = data['lead'].get('first_name', 'there')
    company = data['lead'].get('company_name', 'your company')
    template = data['message'].get('template', '')
    
    # Simple placeholder personalization
    personalized = template.replace('{first_name}', lead_name)
    personalized = personalized.replace('{company}', company)
    
    return personalized











def construct_prompt(data):
    """
    Construct a prompt for the AI based on the data.
    
    Args:
        data: Dictionary containing lead, campaign, and message template data
        
    Returns:
        str: Prompt for the AI
    """
    lead = data['lead']
    campaign = data['campaign']
    template = data['message'].get('template', '')
    
    prompt = f"""
    Please personalize the following email template for a lead with these details:
    
    LEAD INFORMATION:
    - Name: {lead.get('full_name', 'Unknown')}
    - Position: {lead.get('position', 'Unknown')}
    - Company: {lead.get('company_name', 'Unknown')}
    - Industry: {lead.get('industry', 'Unknown')}
    - Lead type: {lead.get('lead_type', 'Unknown')}
    
    CAMPAIGN INFORMATION:
    - Campaign: {campaign.get('name', 'Unknown')}
    - Product: {campaign.get('product_name', 'Unknown')}
    - Product description: {campaign.get('product_description', 'Unknown')}
    
    EMAIL TEMPLATE:
    {template}
    
    Please rewrite this email to make it more personalized and engaging for this specific lead.
    Keep the same general structure but add personalized details and make it sound natural.
    Do not add any placeholders - replace all variables with actual content.
    """
    
    return prompt