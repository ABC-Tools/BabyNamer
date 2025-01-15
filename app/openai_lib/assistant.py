import logging
import openai
import os
import time

API_KEY = os.getenv("OPENAI_API_KEY")
client = openai.OpenAI(api_key='')


class TimeoutException(openai.Timeout):
    pass


class Assistant:
    def __init__(self):
        self.assistant = client.beta.assistants.create(
            name="Baby Namer",
            instructions="Help to name newborns.",
            tools=[],
            model="gpt-3.5-turbo-1106"
        )
        self.thread = client.beta.threads.create()

    def send_and_receive(self, user_msg: str) -> str:
        client.beta.threads.messages.create(
            thread_id=self.thread.id,
            role="user",
            content=user_msg
        )
        run = client.beta.threads.runs.create(
            thread_id=self.thread.id,
            assistant_id=self.assistant.id,
            instructions="""
Please help the user to name the baby, based on the information provided by user. 
Please provide a few name proposals in a JSON format, like
{name_1: "the reason why this is a good name",
 name2: ...
}
"""
        )

        try:
            while run.status in ['queued', 'in_progress']:
                logging.info(f'Thread id: %s, Status: %s, waiting 1 seconds', self.thread.id, run.status)
                time.sleep(1)

                run = client.beta.threads.runs.retrieve(thread_id=self.thread.id, run_id=run.id)
        except openai.error.Timeout as e:
            logging.exception(e, exc_info=True)
            raise TimeoutException(e)

        messages = client.beta.threads.messages.list(
            thread_id=self.thread.id
        )
        return Assistant.get_text_from_last_messages(messages)

    @staticmethod
    def get_text_from_last_messages(messages: openai.pagination.SyncCursorPage):
        for msg in messages:
            return msg.content[0].text.value
