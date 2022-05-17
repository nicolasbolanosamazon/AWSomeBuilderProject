import uuid
import layers.logger as logger
import layers.utils as utils
import boto3
import json

dynamodb = boto3.resource('dynamodb')

def register_tenant(event, context):
    try:
        tenant_id = uuid.uuid1().hex
        tenant_details = json.loads(event['body'])

        tenant_details['tenantId'] = tenant_id

        logger.info(tenant_details)
    except Exception as e:
        logger.error('Error registering a new tenant')
        raise Exception('Error registering a new tenant', e)
    else:
        return utils.create_success_response("You have been registered in our system")