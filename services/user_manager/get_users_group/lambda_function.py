import logging
from layers.base import EventBase, ResultBase, Response
import boto3
import os

LOGGER = logging.getLogger(__name__)

def handler(e, c):
    event = Event(e, c)
    event.handle()
    return event.response()

class Result(ResultBase):
    QUERY_SUCCEEDED = (200, "QUERY SUCCEEDED", "Query succeeded")
    UNKNOWN = (500, "SERVER_ERROR", "Server Error")

class Event(EventBase):
    def __init__(self, event, context):
        EventBase.__init__(self, event, context)
        self.__cognito_idp_client = boto3.client('cognito-idp')

    def handle(self):
        result, data = self.get_users()
        self._response = Response(result, data).to_json()

    def get_users(self):
        response = self.__cognito_idp_client.list_users_in_group(
            UserPoolId = os.environ['COGNITO_POOL_ID'],
            GroupName = self._event['pathParameters']['tenant_id'],
        )
        userArray = []
        for user in response['Users']:
            newUser = {
                'Username': user['Username'],
                'Attributes': user['Attributes'],
                'Enabled': user['Enabled'],
                'UserStatus': user['UserStatus']
            }
            userArray.append(newUser)
        finalResponse = {
            'Users': userArray
        }
        return Result.QUERY_SUCCEEDED, finalResponse