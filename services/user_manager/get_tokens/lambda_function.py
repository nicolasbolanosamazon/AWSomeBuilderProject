from layers.base import EventBase, ResultBase, Response
import os
import logging
import requests
import json

LOGGER = logging.getLogger(__name__)

def handler(e, c):
    event = Event(e, c)
    event.handle()
    return event.response()

class Result(ResultBase):
    CREATION_SUCCEEDED = (200, "LOGIN SUCCEEDED", "Creation succeeded")
    UNKNOWN = (500, "SERVER_ERROR", "Server Error")

class Event(EventBase):
    def __init__(self, event, context):
        EventBase.__init__(self, event, context)
        self.__user_pool_client_id = os.environ['COGNITO_POOL_CLIENT_ID']
        self.__cognito_token_url = "https://octanklmsuserportal.auth.us-east-1.amazoncognito.com/oauth2/token"

    def handle(self):
        result, data = self.get_tokens()
        self._response = Response(result, data).to_json()

    def get_tokens(self):
        code = self._body['code']
        payload=''.join(['grant_type=authorization_code&client_id=',self.__user_pool_client_id ,'&redirect_uri=https%3A%2F%2Fmain.d2p5zbpxldnu9d.amplifyapp.com%2F&code=', code])
        headers = {
        'Content-Type': 'application/x-www-form-urlencoded'
        }
        res = requests.request("POST", self.__cognito_token_url, headers=headers, data=payload)
        response = {
            'response': json.loads(res.text)
        }
        return Result.CREATION_SUCCEEDED, response
