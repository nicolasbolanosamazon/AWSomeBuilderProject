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
    CREATION_SUCCEEDED = (200, "CREATION SUCCEEDED", "Creation succeeded")
    UNKNOWN = (500, "SERVER_ERROR", "Server Error")


class Event(EventBase):
    def __init__(self, event, context):
        EventBase.__init__(self, event, context)
        self.__dynamodb_table_resource = boto3.resource('dynamodb')
        self.__table_tenant_details = self.__dynamodb_table_resource.Table(os.environ['TABLE_NAME'])

    def handle(self):
        result, data = self.create_tenant()
        self._response = Response(result, data).to_json()

    def create_tenant(self):
        tenant_details = self._body

        try:         
            response = self.__table_tenant_details.put_item(
                Item={
                        'tenant_id': tenant_details['tenant_id'],
                        'tenantName' : tenant_details['tenantName'],
                        'tenantDescription': tenant_details['tenantDescription'],
                        'dbCredentialsARN': tenant_details['dbCredentialsARN'],   
                        'isActive': True                    
                    }
                )                    
            print(response)
        except Exception as e:
            LOGGER.error(e)
            return Result.UNKNOWN, {}
        else:
            return Result.CREATION_SUCCEEDED, response
