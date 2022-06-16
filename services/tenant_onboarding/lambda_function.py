import uuid
import logging
import json
from layers.base import EventBase, ResultBase, Response
import boto3
import requests

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
        self.__tenant_id = uuid.uuid4().hex
        self.__secrets_manager_client = boto3.client('secretsmanager')

    def handle(self):
        result, data = self.register_tenant()
        self._response = Response(result, data).to_json()

    def register_tenant(self):
        try:
            
            tenant_details = self._body
            tenant_details['tenant_id'] = self.__tenant_id
            stage_name = self._event['requestContext']['stage']
            host = self._event['headers']['Host']
            headers = self._event['headers']
            retreived_secret = {}
            retreived_secret['Secret'] = self.__secrets_manager_client.get_secret_value(
                SecretId='dev-api-keys'
            )
            secret = json.loads(retreived_secret['Secret']['SecretString'])
            headers['x-api-key'] = secret['dev-api-keys']
            paths = ["/user_manager/create_user_group", "/resource_manager/create_aurora_cluster","/tenant_managment/create_tenant"]
            data = {}
            request_body = json.dumps(tenant_details)
            for path in paths:
                url = ''.join(['https://', host, '/', stage_name, path])
                response = requests.post(url, data=request_body, headers=headers, timeout=(5, 30))
                print(response.text)
                if response.status_code != 200:
                    return Result.UNKNOWN, {}
                if path == "/resource_manager/create_aurora_cluster":
                   response_body = json.loads(response.text)
                   tenant_details['dbCredentialsARN'] = response_body['dbCredentials']
                   request_body = json.dumps(tenant_details)
                
            data['response'] = ''.join(["Tenant ",self.__tenant_id, " created!"])
            data['tenant_id'] = self.__tenant_id
        except Exception as e:
            LOGGER.exception('Error!')
            return Result.UNKNOWN, {}
        else:
            return Result.CREATION_SUCCEEDED, data