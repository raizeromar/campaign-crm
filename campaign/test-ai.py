



from google import genai
from google.genai import types





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
        prompt = data
        
        # System instruction for Gemini
        system_instruction = """
        You are an expert email copywriter specializing in personalized outreach.
        Your task is to rewrite email templates to make them more personalized, engaging, and effective.
        Focus on creating natural-sounding messages that connect with the recipient based on their industry, position, and company.
        Always maintain a professional tone and ensure the message is clear and concise.
        Do not include any placeholders in your response - replace all variables with actual content.
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



if __name__ == "__main__":
    data = """
        Please personalize the following email template for a lead with these details:
    
    LEAD INFORMATION:
    - Full Name: Fdud Ramo
    - First Name: Fdud
    - Last Name: Ramo
    - Position: CEO
    - Company: Woomark
    - Industry: Not specified
    - Lead type: Warm
    - Source: LinkedIn Scrape
    
    CAMPAIGN INFORMATION:
    - Campaign: first campain
    - Campaign ID: c1-fc
    - Product: Cold Outreach Agent
    - Product description: Not provided
    
    EMAIL TEMPLATE:
        Hello {first_name},\n\nWe are excited to welcome you to {company}. This is the main content of our welcome message.
    
    Please rewrite this email to make it more personalized and engaging for this specific lead.
    Keep the same general structure but add personalized details and make it sound natural.
    Do not add any placeholders - replace all variables with actual content.
    If the industry is not specified, make reasonable assumptions based on the company name and position.
"""
    print(call_ai_service(data))
