import json
import layers.utils as utils
import boto3
from os import environ

dynamodb = boto3.resource('dynamodb')

table_tenant_details = dynamodb.Table(environ.get('TABLE_NAME'))

def create_tenant(event, context):
    return {
        "statusCode": 200,
        "headers": {
            "Access-Control-Allow-Headers" : "Content-Type, Origin, X-Requested-With, Accept, Authorization, Access-Control-Allow-Methods, Access-Control-Allow-Headers, Access-Control-Allow-Origin",
            "Access-Control-Allow-Origin": "*",
            "Access-Control-Allow-Methods": "OPTIONS,POST,GET,PUT"
        },
        "body": json.dumps({
            "message": event
        }),
    }
    """
    tenant_details = json.loads(event['body'])

    try:          
        response = table_tenant_details.put_item(
            Item={
                    'tenantId': tenant_details['tenantId'],
                    'tenantName' : tenant_details['tenantName'],
                    'tenantDescription': tenant_details['tenantDescription'],                  
                    'isActive': True                    
                }
            )                    
    except Exception as e:
        raise Exception('Error creating a new tenant', e)
    else:
        return utils.create_success_response("Tenant Created")
    """