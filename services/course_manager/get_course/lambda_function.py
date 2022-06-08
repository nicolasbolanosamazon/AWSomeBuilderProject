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
        self.__select_course_sql = "SELECT course_id, teacher_id, course_name, course_description FROM public.course_table WHERE teacher_id = %s AND course_id = %s;"
        self.__select_assistants_ids = "SELECT student_id FROM public.course_asistants WHERE course_id = %s;"
        self.__select_student = "SELECT user_id, full_name, email FROM public.user_table WHERE user_id= %s;"
        self.__select_student_grade = "SELECT course_grade FROM public.course_grades WHERE course_id = %s AND student_id = %s ;"
        self.__dynamo_table_name = os.environ['TABLE_NAME']

    def handle(self):
        result, data = self.get_course()
        self._response = Response(result, data).to_json()

    def get_course(self):
        authorizer = self._event['requestContext']['authorizer']
        tenant_id = authorizer['tenantId']
        self.log_tenant()
        teacher_id = authorizer['userName']
        dbconn = DBConnection(self.__dynamo_table_name, tenant_id)
        conn = dbconn.get_conn()
        cur = conn.cursor()
        cur.execute(self.__select_course_sql, (teacher_id, self._event['pathParameters']['course_id']))
        res = cur.fetchone()
        course = {
            'course_id': res[0],
            'teacher_id': res[1],
            'course_name': res[2],
            'course_description': res[3]
        }
        cur.execute(self.__select_assistants_ids, (self._event['pathParameters']['course_id'],))
        assistants = cur.fetchall()
        students = [] 
        for studentId in assistants:
            cur.execute(self.__select_student, (studentId[0],))
            student = cur.fetchone()
            stundent_info = {
                'user_id': student[0],
                'full_name': student[1],
                'email': student[2]
            }
            cur.execute(self.__select_student_grade, (self._event['pathParameters']['course_id'], studentId[0]))
            if cur.rowcount == 0:
                stundent_info['grade'] = 'Empty'
            else:
                grade = cur.fetchone()
                stundent_info['grade'] = str(grade[0])
            students.append(stundent_info)
        cur.close()
        conn.close()
        return Result.QUERY_SUCCEEDED, {'course': course, 'students': students}
