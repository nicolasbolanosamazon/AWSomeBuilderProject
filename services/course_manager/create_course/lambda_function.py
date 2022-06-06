import boto3
import uuid
from layers.base import EventBase, ResultBase, Response, DBConnection
import logging
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
        self.__course_id = uuid.uuid4().hex
        self.__insert_course_sql = 'INSERT INTO public.course_table(course_id, teacher_id, course_name, course_description) VALUES(%s, %s, %s, %s);'

    def handle(self):
        result, data = self.create_course()
        self._response = Response(result, data).to_json()

    def create_course(self):
        authorizer = self._event['requestContext']['authorizer']
        tenant_id = authorizer['tenantId']
        teacher_id = authorizer['userName']
        course_id = uuid.uuid4().hex
        course_name = self._body['courseName']
        course_description = self._body['courseDescription']
        dbconn = DBConnection(os.environ['TABLE_NAME'], tenant_id)
        conn = dbconn.get_conn()
        cur = conn.cursor()
        cur.execute(
            self.__insert_course_sql,
            (
                course_id,
                teacher_id,
                course_name,
                course_description
            )
        )
        conn.commit()
        cur.close()
        conn.close()
        return Result.CREATION_SUCCEEDED, {'result': 'Success!'}
        