import logging
from layers.base import EventBase
import os
import boto3
import io
import csv
import time
import datetime

LOGGER = logging.getLogger(__name__)

def handler(e, c):
    event = Event(e, c)
    event.handle()
    #return event.response()

class Event(EventBase):
    def __init__(self, event, context):
        EventBase.__init__(self, event, context)
        self.__s3_client = boto3.client('s3')
        self.__acp_client = boto3.client('applicationcostprofiler')
        self.__bucket_name = os.environ['INPUT_BUCKET_NAME']

    def handle(self):
        self.report_old_csv()
        self.create_new_csv()

    def create_new_csv(self):
        time_obj = time.strptime(time.ctime())
        csvio = io.StringIO()
        writer = csv.writer(csvio)
        writer.writerow(['ApplicationId', 'TenantId', 'TenantDesc','UsageAccountId', 'StartTime', 'EndTime', 'ResourceId'])
        self.__s3_client.put_object(
            Body = csvio.getvalue(),
            ContentType = 'text/csv',
            Bucket = self.__bucket_name,
            StorageClass = 'INTELLIGENT_TIERING',
            Key = ''.join(['input_', time.strftime("%Y-%m-%d %H:%M:%S", time_obj).replace(":", "꞉").replace(" ", "_"), '.csv'])
        )
        csvio.close()

    def report_old_csv(self):
        old_time = datetime.datetime.now() - datetime.timedelta(hours=1)
        file_list = self.__s3_client.list_objects_v2(
            Bucket = self.__bucket_name,
            MaxKeys = 1,
            Prefix = ''.join(['input_', old_time.strftime("%Y-%m-%d_%H")])
        )

        file = file_list['Contents'][0]
        response = self.__acp_client.import_application_usage(
            sourceS3Location={
                'bucket': self.__bucket_name,
                'key': file['Key']
            }
        )
        print(response)

