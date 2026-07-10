import openai

openai.api_key = "your-openai-api-key"

def generate_summary(text):
    response = openai.Completion.create(
        engine="text-davinci-003",
        prompt=f"Generate a summary of the following text:\n{text}",
        max_tokens=150
    )
    return response.choices[0].text.strip()

def generate_questions(resume_text, jd_text):
    response = openai.Completion.create(
        engine="text-davinci-003",
        prompt=f"Generate technical interview questions based on the following resume and job description:\nResume: {resume_text}\nJD: {jd_text}",
        max_tokens=500
    )
    return response.choices[0].text.strip()
