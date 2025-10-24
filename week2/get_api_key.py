def get_api_key():

    import os
    import requests
    from dotenv import load_dotenv
    from openai import OpenAI
    from IPython.display import Markdown, display

    load_dotenv(override=True)
    openai_api_key = os.getenv('OPENAI_API_KEY')
    anthropic_api_key = os.getenv('ANTHROPIC_API_KEY')
    google_api_key = os.getenv('GOOGLE_API_KEY')

    if openai_api_key:
        print(f"OpenAI API Key exists and begins {openai_api_key[:8]}")
    else:
        print("OpenAI API Key not set")
        
    if anthropic_api_key:
        print(f"Anthropic API Key exists and begins {anthropic_api_key[:7]}")
    else:
        print("Anthropic API Key not set (and this is optional)")

    if google_api_key:
        print(f"Google API Key exists and begins {google_api_key[:2]}")
    else:
        print("Google API Key not set (and this is optional)")

    openai = OpenAI()

    anthropic_url = "https://api.anthropic.com/v1/"
    gemini_url = "https://generativelanguage.googleapis.com/v1beta/openai/"

    anthropic = OpenAI(api_key=anthropic_api_key, base_url=anthropic_url)
    gemini = OpenAI(api_key=google_api_key, base_url=gemini_url)

    return openai, anthropic, gemini