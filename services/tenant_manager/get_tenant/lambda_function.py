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
        self.__dynamodb_table_resource = boto3.resource('dynamodb')
        self.__table_tenant_details = self.__dynamodb_table_resource.Table(os.environ['TABLE_NAME'])

    def handle(self):
        result, data = self.get_tenants()
        self._response = Response(result, data).to_json()

    def get_tenants(self):
        item = self.__table_tenant_details.get_item(
            Key={
                'tenant_id': self._event['pathParameters']['tenant_id'],
            }
        )
        response = {
            'Item': item['Item']
        }

        return Result.QUERY_SUCCEEDED, response