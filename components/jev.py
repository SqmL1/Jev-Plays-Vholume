import os
import requests

class Requestor:
    def __init__(self):
        self.url = "https://openrouter.ai/api/alpha/decisions"
        self.auth = f"Bearer {os.environ['OPENROUTER_API_KEY']}"
        self.model = "typesafe/jev-1.13"

    def generate_response(self, state, questions):
        res = requests.post(
            self.url,
            headers={
                "Authorization": self.auth,
                "Content-Type": "application/json",
            },
            json={
                "model": self.model,
                "state": state,
                "questions": questions
            }
        )
        return res 

        