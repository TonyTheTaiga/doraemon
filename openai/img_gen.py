import openai

openai.api_key = "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"

response = openai.Image.create(prompt="A mountain the size of a volcano covered in strawberry jelly", n=5, size="1024x1024")

print(response)

