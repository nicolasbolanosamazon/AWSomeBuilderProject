import logging
from layers.base import EventBase, ResultBase, Response
import boto3
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
        self.__tenant_id = self._body['tenant_id']

    def handle(self):
        result, data = self.create_aurora_cluster()
        self._response = Response(result, data).to_json()
        

    def create_aurora_cluster(self):
        try:
            data = {}
            data['randomPassword'] = self.generateRandomPassword()
            self.create_instance(data)
            self.store_db_secret(data)
        except Exception as e:
            LOGGER.error(e)
            return Result.UNKNOWN, {}
        else:
            return Result.CREATION_SUCCEEDED, self.create_response(data)

    def generateRandomPassword(self):
        response = self.__secrets_manager_client.get_random_password(
            ExcludePunctuation = True,
            IncludeSpace = False
        )
        return response['RandomPassword']

    def create_instance(self, data):
        dbname = ''.join(['db-',self.__tenant_id])
        db_masteruser = ''.join(['masteruser',self.__tenant_id])
        data['cluster'] = self.__rds_client.create_db_cluster(
                DatabaseName= 'octanklmsdb',
                DBClusterIdentifier = dbname,
                Engine = 'aurora-postgresql',
                EngineVersion = '13.4',
                MasterUsername = db_masteruser,
                MasterUserPassword = data['randomPassword'],
                Tags = [
                    {
                        'Key':'tenant_id',
                        'Value':self.__tenant_id
                    }
                ],
                StorageEncrypted = True
        )
        data['instances'] = []
        data['instances'].append(self.__rds_client.create_db_instance(
                DBInstanceIdentifier = dbname,
                DBInstanceClass = 'db.r6g.large',
                DBClusterIdentifier = dbname,
                Engine = 'aurora-postgresql',
                EngineVersion = '13.4',
                Tags = [
                    {
                        'Key':'tenant_id',
                        'Value':self.__tenant_id
                    }
                ],
                PubliclyAccessible = True
        ))
        
    def store_db_secret(self, data):
        secret = {
                "engine": data['cluster']['DBCluster']['Engine'],
                "host": data['cluster']['DBCluster']['Endpoint'],
                "username": data['cluster']['DBCluster']['MasterUsername'],
                "password": data['randomPassword'],
                "dbname": data['cluster']['DBCluster']['DatabaseName'],
                "port": data['cluster']['DBCluster']['Port']
            }
        data['newSecret'] = self.__secrets_manager_client.create_secret(
            Name = self.__tenant_id,
            Description = ''.join(["Amazon Aurora Cluster access credentials for tenant ID: ", self.__tenant_id]),
            SecretString = json.dumps(secret)
        )

    def create_response(self, data):
        return {
                    "dbCredentials": data['newSecret']['ARN'],
        }