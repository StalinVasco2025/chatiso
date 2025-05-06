from google import genai

client = genai.Client(api_key="AIzaSyCpzD4M30B2Yx6p8XwCBcDYzdoYxB-24p4")

response = client.models.generate_content(
    model="gemini-2.0-flash",
    contents="genera un caso para usar la ISO 37001",
)

print(response.text)