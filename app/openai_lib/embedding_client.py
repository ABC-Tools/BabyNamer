import openai

client = openai.OpenAI(api_key='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')


def create_single_embedding(msg: str):
    resp = client.embeddings.create(input=[msg], model="text-embedding-ada-002")
    return resp.data[0].embedding
