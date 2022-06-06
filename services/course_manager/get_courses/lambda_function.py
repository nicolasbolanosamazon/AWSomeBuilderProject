import boto3
from layers.base import EventBase, ResultBase, Response, DBConnection
import os
import logging

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
        self.__select_courses_sql = "SELECT course_id, teacher_id, course_name, course_description FROM public.course_table WHERE teacher_id = %s;"
        self.__dynamo_table_name = os.environ['TABLE_NAME']

    def handle(self):
        result, data = self.get_courses()
        self._response = Response(result, data).to_json()

    def get_courses(self):
        authorizer = self._event['requestContext']['authorizer']
        tenant_id = authorizer['tenantId']
        self.log_tenant()
        teacher_id = authorizer['userName']
        dbconn = DBConnection(self.__dynamo_table_name, tenant_id)
        conn = dbconn.get_conn()
        cur = conn.cursor()
        cur.execute(self.__select_courses_sql, (teacher_id,))
        res = cur.fetchall()
        finalRes = []
        for course in res:
            finalCourse = {
                'course_id': course[0],
                'teacher_id': course[1],
                'course_name': course[2],
                'course_description': course[3]
            }
            finalRes.append(finalCourse)
        cur.close()
        conn.close()

        return Result.QUERY_SUCCEEDED, {'Courses':finalRes}