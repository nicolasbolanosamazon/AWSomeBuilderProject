from layers.base import EventBase, ResultBase, Response, DBConnection
import os
import logging

OGGER = logging.getLogger(__name__)

def handler(e, c):
    event = Event(e, c)
    event.handle()
    return event.response()

class Result(ResultBase):
    QUERY_SUCCEEDED = (200, "QUERY SUCCEEDED", "Query succeeded")
    UNKNOWN = (500, "SERVER_ERROR", "Server Error")
    UNAUTHORIZED = (403, "UNAUTHORIZED", "Course does not belong to teacher")

class Event(EventBase):
    def __init__(self, event, context):
        EventBase.__init__(self, event, context)
        self.__update_student_grade_sql = "UPDATE public.course_grades SET course_id=%s, student_id=%s, course_grade=%s;"
        self.__select_course_sql = "SELECT course_id, teacher_id, course_name, course_description FROM public.course_table WHERE teacher_id = %s AND course_id = %s;"
        self.__dynamo_table_name = os.environ['TABLE_NAME']

    def handle(self):
        result, data = self.grade_student()
        self._response = Response(result, data).to_json()

    def grade_student(self):
        authorizer = self._event['requestContext']['authorizer']
        tenant_id = authorizer['tenantId']
        self.log_tenant()
        teacher_id = authorizer['userName']
        dbconn = DBConnection(self.__dynamo_table_name, tenant_id)
        conn = dbconn.get_conn()
        cur = conn.cursor()
        cur.execute(self.__select_course_sql, (teacher_id, self._event['pathParameters']['course_id']))
        if cur.rowcount == 0:
            return Result.UNAUTHORIZED, {}
        cur.execute(self.__update_student_grade_sql, (self._body['course_id'], self._body['student_id'], self._body['grade']))
        conn.commit()
        cur.close()
        conn.close()
        return Result.QUERY_SUCCEEDED, {}