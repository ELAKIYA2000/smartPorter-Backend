# import os
# import google.generativeai as genai
# from dotenv import load_dotenv


# load_dotenv()
# genai.configure(api_key=os.getenv("GEMINI_API_KEY"))

import google.generativeai as genai

genai.configure(api_key="AIzaSyCHe9OkM4VNDhu4uWVFUTru80B4SJNIscM")


def summarize_with_gemini(text):
    model = genai.GenerativeModel("gemini-1.5-flash")
    # prompt = f"Summarize the following changelog :\n\n{text}"
    prompt = f"You are an expert Java code reviewer. Analyze the following repo context suggest whether it is compatible with the following Maven dependency upgrades\n\n{text}"
    response = model.generate_content(prompt)
    return response.text
