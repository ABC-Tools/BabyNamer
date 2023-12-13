import openai
import time

client = openai.OpenAI(api_key='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')

assistant = client.beta.assistants.create(name="Baby Namer",
                                          instructions="Help to name newborns.",
                                          tools=[],
                                          model="gpt-3.5-turbo-1106")
thread = client.beta.threads.create()

data = 'name my newborn, who is a boy'
message = client.beta.threads.messages.create(thread_id=thread.id,
                                              role="user",
                                              content=data)
run = client.beta.threads.runs.create(
        thread_id=thread.id,
        assistant_id=assistant.id,
        instructions="Please address the user as San. The user has a premium account."
)

while run.status in ['queued', 'in_progress']:
    time.sleep(5)
    run = client.beta.threads.runs.retrieve(thread_id=thread.id, run_id=run.id)

