import logging
from layers.base import EventBase, ResultBase, Response
import boto3
import uuid
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
        self.__secrets_manager_client = boto3.client('secretsmanager')
        self.__rds_client = boto3.client('rds')
        self.__sample_id = uuid.uuid4().hex

    def handle(self):
        result, data = self.create_aurora_cluster()
        self._response = Response(result, data).to_json()
        

    def create_aurora_cluster(self):
        try:
            data = {}
            data['randomPassword'] = self.generateRandomPassword()
            db_response = self.create_cluster(data)
            print(db_response)
            secret = {
                "engine": "mysql",
                "host": "samplehost",
                "username": self.__sample_id,
                "password": data['randomPassword'],
                "dbname": "sampledb",
                "port": 3306
            }
            data['newSecret'] = self.__secrets_manager_client.create_secret(
                Name = self.__sample_id,
                Description = "Sample Secret",
                SecretString = json.dumps(secret)
            )
        except Exception as e:
            LOGGER.error(e)
            return Result.UNKNOWN, {}
        else:
            return Result.CREATION_SUCCEEDED, data

    def generateRandomPassword(self):
        response = self.__secrets_manager_client.get_random_password(
            ExcludePunctuation = True,
            IncludeSpace = False
        )
        return response['RandomPassword']

    def create_cluster(self, data):
        dbname = ''.join(['db-',self.__sample_id])
        return self.__rds_client.create_db_cluster(
                DatabaseName= 'octanklmsdb',
                DBClusterIdentifier = dbname,
                Engine = 'aurora-postgresql',
                EngineVersion = '13.4',
                MasterUsername = self.__sample_id,
                MasterUserPassword = data['randomPassword'],
                Tags = [
                    {
                        'Key':'tenant_id',
                        'Value':self.__sample_id
                    }
                ],
                StorageEncrypted = True
        )