import logging
from layers.base import EventBase, ResultBase, Response
import boto3
import os
import psycopg2
import json

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
        self.__secrets_manager_client = boto3.client('secretsmanager')
        self.__sql_scripts = "CREATE TABLE public.user_table ( user_id varchar NOT NULL, full_name varchar NOT NULL, user_type varchar NOT NULL, email varchar NOT NULL, tenant_id varchar NOT NULL, CONSTRAINT user_table_pk PRIMARY KEY (user_id)); CREATE TABLE public.course_table ( course_id varchar NOT NULL, teacher_id varchar NOT NULL, course_name varchar NOT NULL, course_description varchar NOT NULL, CONSTRAINT course_table_pk PRIMARY KEY (course_id), CONSTRAINT course_table_fk FOREIGN KEY (teacher_id) REFERENCES public.user_table(user_id)); CREATE TABLE public.course_asistants ( course_id varchar NOT NULL, student_id varchar NOT NULL, CONSTRAINT course_asistants_fk FOREIGN KEY (course_id) REFERENCES public.course_table(course_id), CONSTRAINT course_asistants_fk_1 FOREIGN KEY (student_id) REFERENCES public.user_table(user_id)); CREATE TABLE public.course_grades ( course_id varchar NOT NULL, student_id varchar NOT NULL, course_grade decimal NOT NULL, CONSTRAINT course_grades_fk FOREIGN KEY (course_id) REFERENCES public.course_table(course_id), CONSTRAINT course_grades_fk_1 FOREIGN KEY (student_id) REFERENCES public.user_table(user_id));"

    def handle(self):
        dbcredentials = self.get_db_credentials()
        result, data = self.run_sql_scripts(dbcredentials)
        self._response = Response(result, data).to_json()

    def get_db_credentials(self):
        sns = self._event['Records'][0]['Sns']
        sns_message = json.loads(sns['Message'])
        source_id = sns_message['Source ID'].replace("db-", "")
        dynamo_item = self.fetch_dynamo_item(source_id)
        credentialSecretARN = dynamo_item['Item']['dbCredentialsARN']
        return self.get_secret_value(credentialSecretARN)

    def run_sql_scripts(self, dbcredentials):
        conn = psycopg2.connect(
            dbname = dbcredentials['dbname'],
            user = dbcredentials['username'],
            password = dbcredentials['password'],
            host = dbcredentials['host'],
            port = dbcredentials['port']
        )
        cur = conn.cursor()
        cur.execute(self.__sql_scripts)
        conn.commit()
        cur.close()
        conn.close()
        response = {
            'response':''.join(['SQL Scripts successfully executed on host: ', dbcredentials['host']])
        }
        return Result.CREATION_SUCCEEDED, response

    def fetch_dynamo_item(self, source_id):
        return self.__table_tenant_details.get_item(
            Key = {
                'tenant_id': source_id
            },
            AttributesToGet=[
                'dbCredentialsARN'
            ]
        )
    
    def get_secret_value(self, secretARN):
        dbcredentials = self.__secrets_manager_client.get_secret_value(
            SecretId = secretARN
        )
        return json.loads(dbcredentials['SecretString'])