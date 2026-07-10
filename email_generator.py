import openai

openai.api_key = "your-openai-api-key"

def generate_email(template, data):
    response = openai.Completion.create(
        engine="text-davinci-003",
        prompt=f"Generate the following email using the provided template and data:\nTemplate: {template}\nData: {data}",
        max_tokens=500
    )
    return response.choices[0].text.strip()
