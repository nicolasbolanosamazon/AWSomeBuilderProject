import uuid
import logging
import json
from layers.base import EventBase, ResultBase, Response
import os
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
            headers['x-api-key'] = os.environ['API_KEYS']
            paths = ['/user_manager/create_user_group', '/tenant_managment/create_tenant']
            data = {}
            data['responses'] = []
            for path in paths:
                url = ''.join(['https://', host, '/', stage_name, path])
                response = requests.post(url, data=json.dumps(tenant_details), headers=headers)
                if response.status_code != 200:
                    raise Exception(''.join(["Error during request to ", url]))
                data['responses'].append(response.text)
            data['response'] = ''.join(["Tenant ",self.__tenant_id, " created!"])
            data['tenant_id'] = self.__tenant_id
            print(data)
        except Exception as e:
            LOGGER.error(e)
            return Result.UNKNOWN, {}
        else:
            return Result.CREATION_SUCCEEDED, data