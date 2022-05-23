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
    USERNAME_EXISTS = (409, "CONFLICT", "Username Already Exists")
    UNKNOWN = (500, "SERVER_ERROR", "Server Error")

class Event(EventBase):
    def __init__(self, event, context):
        EventBase.__init__(self, event, context)
        self.__cognito_idp_client = boto3.client('cognito-idp')
        self.__user_pool_id = os.environ['COGNITO_POOL_ID']

    def handle(self):
        result, data = self.create_user_cognito()
        self._response = Response(result, data).to_json()

    def create_user_cognito(self):
        try: 
            user_details = self._body
            userCreated = self.__cognito_idp_client.admin_create_user(
                Username = user_details['userEmail'],
                UserPoolId = self.__user_pool_id,
                ForceAliasCreation = True,
                UserAttributes = [
                    {
                        'Name': 'email',
                        'Value': user_details['userEmail']
                    },
                    {
                        'Name': 'custom:full_name',
                        'Value': user_details['full_name'] 
                    },            
                    {
                        'Name': 'custom:tenant_id',
                        'Value': user_details['tenant_id'] 
                    }
                ]
            )
            print("New User")
            print(userCreated)
            self.add_user_to_group(user_details)
            return Result.CREATION_SUCCEEDED, {}
        except self.__cognito_idp_client.exceptions.UsernameExistsException as e:
            LOGGER.error(e)
            return Result.USERNAME_EXISTS, {}
        except Exception as e:
            LOGGER.error(str(e))
            return Result.UNKNOWN, {}

    def add_user_to_group(self, user_details):
        userAdded =  self.__cognito_idp_client.admin_add_user_to_group(
                UserPoolId = self.__user_pool_id,
                Username = user_details['userEmail'],
                GroupName = user_details['tenant_id'] 
            )
        print("Added to group")
        print(userAdded)