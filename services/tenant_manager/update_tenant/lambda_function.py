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
    UPDATE_SUCCEEDED = (200, "UPDATE SUCCEEDED", "Update succeeded")
    UNKNOWN = (500, "SERVER_ERROR", "Server Error")

class Event(EventBase):
    def __init__(self, event, context):
        EventBase.__init__(self, event, context)
        self.__dynamodb_table_resource = boto3.resource('dynamodb')
        self.__table_tenant_details = self.__dynamodb_table_resource.Table(os.environ['TABLE_NAME'])

    def handle(self):
        result, data = self.update_tenant()
        self._response = Response(result, data).to_json()

    def update_tenant(self):
        tenant_details = self._body
        response_update = self.__table_tenant_details.update_item(
            Key={
                'tenant_id': tenant_details['tenant_id'],
            },
            UpdateExpression="set tenantName = :tenantName, tenantDescription = :tenantDescription",
            ExpressionAttributeValues={
                ':tenantName' : tenant_details['tenantName'],
                ':tenantDescription': tenant_details['tenantDescription'],             
            },
            ReturnValues="UPDATED_NEW"
        )
        response = {
            'Result Update': response_update
        }

        return Result.UPDATE_SUCCEEDED, response