import enum
import json
import os
import boto3
import psycopg2
from distutils.util import strtobool


class EventBase:
    def __init__(self, event, context):
        self._event = event
        self._response = {}
        self._body = self.__get_body()
        self._query = self.__get_query()
        self._context = context
        self._log()

    def _log(self):
        if _is_log_enabled():
            print('{\'event\':' + str(self._event))

    def __get_body(self):
        body = {}
        raw_body = self._event.get('body')
        if raw_body:
            body = json.loads(raw_body)
        return body

    def __get_query(self):
        query = {}
        raw_query = self._event.get('queryStringParameters')
        if raw_query:
            query = raw_query
        return query

    def response(self):
        return self._response

    def event(self):
        return self._event


def _is_log_enabled():
    log_enabled = os.environ["LOG_ENABLED"]
    return log_enabled is not None and bool(strtobool(log_enabled))


class Response:
    def __init__(self, result, data={}, include_message=True):
        self.__status_code = result.status_code
        self.__data = data
        if include_message:
            self.__data['message'] = result.message
            self.__data['code'] = result.code

    def to_json(self):
        return {
            'isBase64Encoded': False,
            'statusCode': self.__status_code,
            'body': json.dumps(self.__data),
            'headers': {
                'Content-Type': 'application/json'
            }
        }


class ResultBase(enum.Enum):

    def __init__(self, status_code, code, message):
        self.__status_code = status_code
        self.__code = code
        self.__message = message

    @property
    def status_code(self):
        return self.__status_code

    @property
    def code(self):
        return self.__code

    @property
    def message(self):
        return self.__message

class DBConnection:
    def __init__(self, table_name, tenant_id):
        self.__dynamodb_table_resource = boto3.resource('dynamodb')
        self.__table_tenant_details = self.__dynamodb_table_resource.Table(table_name)
        self.__secrets_manager_client = boto3.client('secretsmanager')
        self.__tenant_id = tenant_id

    def get_conn(self):
        dbcredentials = json.loads(self.obtain_creds(self.__tenant_id)['SecretString'])
        return psycopg2.connect(
            dbname = dbcredentials['dbname'],
            user = dbcredentials['username'],
            password = dbcredentials['password'],
            host = dbcredentials['host'],
            port = dbcredentials['port']
        )

    def obtain_creds(self, tenant_id):
        dynamo_item = self.fetch_dynamo_item(tenant_id)
        credentialSecretARN = dynamo_item['Item']['dbCredentialsARN']
        return self.__secrets_manager_client.get_secret_value(
            SecretId = credentialSecretARN
        )

    def fetch_dynamo_item(self, tenant_id):
        return self.__table_tenant_details.get_item(
            Key = {
                'tenant_id': tenant_id
            },
            AttributesToGet=[
                'dbCredentialsARN'
            ]
        )