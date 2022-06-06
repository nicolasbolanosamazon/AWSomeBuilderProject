import logging
from layers.base import EventBase, ResultBase, Response
import gzip
import json
import base64
import boto3
import os

LOGGER = logging.getLogger(__name__)

def handler(e, c):
    event = Event(e, c)
    event.handle()
    #return event.response()

class Event(EventBase):
    def __init__(self, event, context):
        EventBase.__init__(self, event, context)
        self.__sqs_client = boto3.client('sqs')

    def handle(self):
        transformed_log = self.transform_log()
        self.send_to_queue(transformed_log)

    def transform_log(self):
        cw_data = self.event()['awslogs']['data']
        compressed_payload = base64.b64decode(cw_data)
        uncompressed_payload = gzip.decompress(compressed_payload)
        payload = json.loads(uncompressed_payload)
        log_events = payload['logEvents']
        transformedDicc = {
            'ApplicationId':'OcktankLMS',
            'UsageAccountId':self._context.invoked_function_arn.split(":")[4]
        }
        for log_event in log_events:
            message = log_event['message']
            if "START" in message:
                transformedDicc['StartTime'] = log_event['timestamp']
                continue
            if "Tenant Id" in message:
                transformedDicc['TenantId'] = message.split(': ')[1].replace('\n', '')
                continue
            if "ARN" in message:
                transformedDicc['ResourceId'] = message.split(': ')[1].replace('\n', '')
                continue
            if "END" in message:
                transformedDicc['EndTime'] = log_event['timestamp']
                continue
        return json.dumps(transformedDicc)

    def send_to_queue(self, message):
        queueUrl = ''.join(['https://sqs.', os.environ['AWS_REGION'], '.amazonaws.com/', self._context.invoked_function_arn.split(":")[4], '/' ,os.environ['SQS_NAME']])
        response = self.__sqs_client.send_message(
            QueueUrl = queueUrl,
            MessageBody = message
        )
        return