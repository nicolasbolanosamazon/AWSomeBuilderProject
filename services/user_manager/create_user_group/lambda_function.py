import boto3
from layers.base import EventBase, ResultBase, Response
import os
import logging

LOGGER = logging.getLogger(__name__)

def handler(e, c):
    event = Event(e, c)
    event.handle()
    return event.response()

class Result(ResultBase):
    CREATION_SUCCEEDED = (200, "CREATION SUCCEEDED", "Creation succeeded")
    UNKNOWN = (500, "SERVER_ERROR", "Server Error")

class Event(EventBase):
    def __init__(self, event, context):
        EventBase.__init__(self, event, context)
        self.__cognito_idp_client = boto3.client('cognito-idp')
        self.__user_pool_id = os.environ['COGNITO_POOL_ID']

    def handle(self):
        result, data = self.create_user_group()
        self._response = Response(result, data).to_json()

    def create_user_group(self):
        try:
            response = self.__cognito_idp_client.create_group(
                GroupName = self._body['tenant_id'],
                UserPoolId = self.__user_pool_id,
                Description = ''.join(['User Pool Group for tenant ID: ', self._body['tenant_id']])
            )
            print(response)
            data = {}
            data['response'] = ''.join(["User gruop for tenant ", self._body['tenant_id'], " created!"])
        except Exception as e:
            LOGGER.error(e)
            return Result.UNKNOWN, {}
        else:
            return Result.CREATION_SUCCEEDED, data
        