import boto3
from layers.base import EventBase, ResultBase, Response, DBConnection
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
        self.__insert_user_sql = 'INSERT INTO public.user_table (user_id, full_name, user_type, email, tenant_id) VALUES(%s, %s, %s, %s, %s);'

    def handle(self):
        result, data = self.create_user()
        self._response = Response(result, data).to_json()

    def create_user(self):
        #try: 
        user_details = self._body
        user = self.create_user_cognito(user_details)
        self.add_user_to_cognito_group(user_details)
        self.insert_user_in_db(user)
        return Result.CREATION_SUCCEEDED, {}
        #except self.__cognito_idp_client.exceptions.UsernameExistsException as e:
        #    LOGGER.error(e)
        return Result.USERNAME_EXISTS, {}
       # except Exception as e:
         #   LOGGER.error(str(e))
            #return Result.UNKNOWN, {}

    def create_user_cognito(self, user_details):
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
                },
                {
                    'Name': 'custom:tenant_user_role',
                    'Value': user_details['role'] 
                }
            ]
        )
        return userCreated['User']
        

    def add_user_to_cognito_group(self, user_details):
        userAdded =  self.__cognito_idp_client.admin_add_user_to_group(
                UserPoolId = self.__user_pool_id,
                Username = user_details['userEmail'],
                GroupName = user_details['tenant_id'] 
            )
        print("Added to group")
        print(userAdded)

    def insert_user_in_db(self, user):
        user_attributes = user['Attributes']
        user_id = user['Username']
        full_name = user_attributes[0]['Value']
        user_type = user_attributes[4]['Value']
        email = user_attributes[3]['Value']
        tenant_id = user_attributes[2]['Value']
        DBconn = DBConnection(os.environ['TABLE_NAME'], tenant_id)
        conn = DBconn.get_conn()
        cur = conn.cursor()
        cur.execute(self.__insert_user_sql, (user_id, full_name, user_type, email, tenant_id))
        conn.commit()
        cur.close()
        conn.close()