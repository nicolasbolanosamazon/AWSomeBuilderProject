import logging
from layers.base import EventBase
from io import StringIO
import json
import boto3
import os
import time
import pandas as pd

LOGGER = logging.getLogger(__name__)

def handler(e, c):
    event = Event(e, c)
    event.handle()

class Event(EventBase):
    def __init__(self, event, context):
        EventBase.__init__(self, event, context)
        self.__s3_client = boto3.client('s3')
        self.__dynamodb_table_resource = boto3.resource('dynamodb')
        self.__table_tenant_details = self.__dynamodb_table_resource.Table(os.environ['TABLE_NAME'])
        self.__bucket_name = os.environ['INPUT_BUCKET_NAME']

    def handle(self):
        content, key = self.get_file()
        self.insert_rows(content, key)

    def get_file(self):
        time_obj = time.strptime(time.ctime())
        file_list = self.__s3_client.list_objects_v2(
            Bucket = self.__bucket_name,
            MaxKeys = 1,
            Prefix = ''.join(['input_', time.strftime("%Y-%m-%d %H", time_obj).replace(" ", "_")])
        )
        file = file_list['Contents'][0]
        s3_object = self.__s3_client.get_object(
            Bucket = self.__bucket_name,
            Key = file['Key']
        )
        content = s3_object["Body"].read().decode('utf-8')
        return content, file['Key']

    def insert_rows(self, content, key):
        csvio = StringIO(content)
        print(csvio.read())
        records = self.event()['Records']
        for record in records:
            message = json.loads(record['body'])
            item = self.__table_tenant_details.get_item(
                Key={
                    'tenant_id': message['TenantId'],
                }
            )
            description = item['Item']['tenantName']
            newline = "".join(
                [
                    '\n', 
                    message['ApplicationId'], ',', 
                    message['TenantId'], ',',
                    description, ',',
                    message['UsageAccountId'], ',',
                    str(float(message['StartTime'])), ',',
                    str(float(message['EndTime'])), ',',
                    message['ResourceId']
                ]
            )
            csvio.write(newline)
        """
        df = pd.read_csv(StringIO(content))
        csvio.close()
        records = self.event()['Records']
        for record in records:
            message = json.loads(record['body'])
            df2 = pd.DataFrame(
                [[message['ApplicationId'], message['UsageAccountId'], message['StartTime'], message['TenantId'], message['ResourceId'], message['EndTime']]], 
                columns=['ApplicationId', 'UsageAccountId', 'StartTime', 'TenantId', 'ResourceId', 'EndTime']
            )
            df = pd.concat([df, df2], ignore_index = True)
        csv_buffer = StringIO()
        df.to_csv(csv_buffer)
        """
        self.__s3_client.put_object(
            Body = csvio.getvalue(),
            Bucket = self.__bucket_name,
            StorageClass = 'INTELLIGENT_TIERING',
            Key = key
        )
        csvio.close()

