import logging
from layers.base import EventBase
import os
import boto3
import io
import csv
import time

LOGGER = logging.getLogger(__name__)

def handler(e, c):
    event = Event(e, c)
    event.handle()
    #return event.response()

class Event(EventBase):
    def __init__(self, event, context):
        EventBase.__init__(self, event, context)
        self.__s3_client = boto3.client('s3')
        self.__bucket_name = os.environ['INPUT_BUCKET_NAME']

    def handle(self):
        time_obj = time.strptime(time.ctime())
        csvio = io.StringIO()
        writer = csv.writer(csvio)
        writer.writerow(['ApplicationId', 'TenantId', 'UsageAccountId', 'StartTime', 'EndTime', 'ResourceId'])
        self.__s3_client.put_object(
            Body = csvio.getvalue(),
            ContentType = 'text/csv',
            Bucket = self.__bucket_name,
            StorageClass = 'INTELLIGENT_TIERING',
            Key = ''.join(['input_', time.strftime("%Y-%m-%d %H:%M:%S", time_obj).replace(":", "꞉").replace(" ", "_"), '.csv'])
        )
        csvio.close()