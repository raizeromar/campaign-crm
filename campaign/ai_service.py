
import json
import logging
import os
from google import genai
from google.genai import types

    
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
        
        # Optional: Write to file for debugging/inspection only
        # with open('campaign/json.json', 'w') as f:
        #     f.write(json.dumps(data, indent=2))
        #     print("Successfully wrote data to campaign/json.json")
        
        # Call AI service with the data dictionary
        personalized_text = call_ai_service(data)
        
        return personalized_text
        
    except Exception as e:
        # Return the template as fallback
        return message_assignment.personlized_msg_tmp



def call_ai_service(data):
    """
    Call the Gemini AI service to personalize a message.
    
    Args:
        data: Dictionary containing lead, campaign, and message template data
        
    Returns:
        str: Personalized message from the AI
    """
    try:
        client = genai.Client(api_key='AIzaSyBDrSRJhI-gINvIO9RgCmDEQndpuDLaipk')

        # Construct the prompt for Gemini
        prompt = construct_prompt(data)
        prompt = str(prompt)
        
        # System instruction for Gemini
        system_instruction = """
        You are an expert cold email copywriter specializing in personalization only.

        Your role is NOT to rewrite or improve the tone of the message — only to personalize an existing template using lead and campaign information. The template has already been written with the sender’s tone, and it must be preserved exactly.

        The sender’s tone is:
        - **Casual-professional**
        - **Direct and concise**
        - **Slightly informal**
        - **Conversational and friendly, but not fluffy**
        - Written in a way that sounds like a real person, not a corporate marketer

        Do NOT:
        - Add or remove sentences
        - Rephrase or rewrite sections for engagement
        - Introduce adjectives or expressions not already present

        ONLY:
        - Insert relevant personalization based on the lead's name, company, position, and industry
        - Make the email feel natural by fitting in the personal details
        - Replace all placeholders

        Never add placeholders or suggestions. All variables must be replaced with actual content.

        """
        
        # Call Gemini API with system instruction
        response = client.models.generate_content(
            model="gemini-2.0-flash",
            config=types.GenerateContentConfig(
                system_instruction=system_instruction,
            ),
            contents=[prompt]
        )
        
        # Log success

        
        # Return the generated text
        return response.text
        
    except Exception as e:

        # Fallback to simple personalization
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
    Please personalize the following email template using the lead and campaign details provided.

    IMPORTANT INSTRUCTIONS:
    - DO NOT change the tone, sentence structure, or wording style of the email template.
    - ONLY add light personalization where appropriate based on the lead's name, company, role, or industry.
    - The email was written by me. My tone is casual-professional, concise, slightly informal, and direct — do not modify it.
    - Avoid "fluff", buzzwords, or additional phrasing not found in the original.
    - DO NOT "rewrite" or "make it more engaging" — just personalize it in my style.
    - Replace all placeholders with the actual values from the lead and campaign data.
    - Leave everything else as-is, you are allowed to correct things if neccessary, like typing error, captalizing...
    
    LEAD INFORMATION:
    - Full Name: {lead.get('full_name', 'Unknown')}
    - First Name: {lead.get('first_name', 'Unknown')}
    - Last Name: {lead.get('last_name', 'Unknown')}
    - Position: {lead.get('position', 'Unknown')}
    - Company: {lead.get('company_name', 'Unknown')}
    - Industry: {lead.get('industry', 'Unknown') or 'Not specified'}
    - Lead type: {lead.get('lead_type', 'Unknown')}
    - Source: {lead.get('source', 'Unknown')}
    
    CAMPAIGN INFORMATION:
    - Campaign: {campaign.get('name', 'Unknown')}
    - Campaign ID: {campaign.get('short_name', 'Unknown')}
    - Product: {campaign.get('product_name', 'Unknown')}
    - Product description: {campaign.get('product_description', 'Unknown') or 'Not provided'}
    
    EMAIL TEMPLATE:
    {template}
    """
    
    return prompt
