import os
import re
import json
import logging
import urllib.request
import time
from jose import jwk, jwt
from jose.utils import base64url_decode
from layers.base import EventBase

LOGGER = logging.getLogger(__name__)

def handler(e, c):
    event = Event(e, c)
    return event.handle()
    
class Event(EventBase):
    def __init__(self, event, context):
        EventBase.__init__(self, event, context)
        self.__region = os.environ['AWS_REGION']
        self.__user_pool_id = os.environ['COGNITO_POOL_ID']
        self.__user_pool_client_id = os.environ['COGNITO_POOL_CLIENT_ID']

    def handle(self):
        token = self._event['authorizationToken'].split(" ")
        if (token[0] != 'Bearer'):
            raise Exception('Authorization header should have a format Bearer <JWT> Token')
        jwt_bearer_token = token[1]
        print("Method ARN: " + self._event['methodArn'])
        unauthorized_claims = jwt.get_unverified_claims(jwt_bearer_token)
        print(unauthorized_claims)
        keys_url = 'https://cognito-idp.{}.amazonaws.com/{}/.well-known/jwks.json'.format(self.__region, self.__user_pool_id)
        with urllib.request.urlopen(keys_url) as f:
            response = f.read()
        keys = json.loads(response.decode('utf-8'))['keys']

        response = self.validateJWT(jwt_bearer_token, self.__user_pool_client_id, keys)
        
        if (response == False):
            LOGGER.error('Unauthorized')
            raise Exception('Unauthorized')
        else:
            print(response)
            principal_id = response["sub"]
            user_name = response["cognito:username"]
            tenant_id = response["custom:tenant_id"]
            user_role = response["custom:tenant_user_role"]

        tmp = self._event['methodArn'].split(':')
        api_gateway_arn_tmp = tmp[5].split('/')
        aws_account_id = tmp[4]

        policy = AuthPolicy(principal_id, aws_account_id)
        policy.restApiId = api_gateway_arn_tmp[0]
        policy.region = tmp[3]
        policy.stage = api_gateway_arn_tmp[1]

        if user_role == 'Admin':
            policy.allowAllMethods()
        elif user_role == 'Student' or user_role == 'Teacher':
            policy.denyMethod(HttpVerb.ALL, 'tenant_managment/*')
            policy.denyMethod(HttpVerb.ALL, 'user_manager/*')
            policy.denyMethod(HttpVerb.POST, 'onboard_tenant')
            if user_role == 'Teacher':
                policy.allowMethod(HttpVerb.ALL, 'lms/course_manager/*')

        authResponse = policy.build()
 
        context = {
            'userName': user_name,
            'userPoolId': self.__user_pool_id,
            'tenantId': tenant_id,
            'userRole': user_role
        }
        
        authResponse['context'] = context

        print(authResponse)
        
        return authResponse

    def validateJWT(self, token, app_client_id, keys):
        headers = jwt.get_unverified_headers(token)
        kid = headers['kid']
        key_index = -1
        for i in range(len(keys)):
            if kid == keys[i]['kid']:
                key_index = i
                break
        if key_index == -1:
            print('Public key not found in jwks.json')
            return False
        public_key = jwk.construct(keys[key_index])
        message, encoded_signature = str(token).rsplit('.', 1)
        decoded_signature = base64url_decode(encoded_signature.encode('utf-8'))
        if not public_key.verify(message.encode("utf8"), decoded_signature):
            print('Signature verification failed')
            return False
        print('Signature successfully verified')
        claims = jwt.get_unverified_claims(token)
        if time.time() > claims['exp']:
            print('Token is expired')
            return False
        if claims['aud'] != app_client_id:
            print('Token was not issued for this audience')
            return False
        print(claims)
        return claims
        
class HttpVerb:
    GET     = "GET"
    POST    = "POST"
    PUT     = "PUT"
    PATCH   = "PATCH"
    HEAD    = "HEAD"
    DELETE  = "DELETE"
    OPTIONS = "OPTIONS"
    ALL     = "*"

class AuthPolicy(object):
    awsAccountId = ""
    principalId = ""
    version = "2012-10-17"
    pathRegex = "^[/.a-zA-Z0-9-_\*]+$"

    allowMethods = []
    denyMethods = []

    restApiId = "*"
    region = "*"
    stage = "*"

    def __init__(self, principal, awsAccountId):
        self.awsAccountId = awsAccountId
        self.principalId = principal
        self.allowMethods = []
        self.denyMethods = []
    
    def _addMethod(self, effect, verb, resource, conditions):
        if verb != "*" and not hasattr(HttpVerb, verb):
            raise NameError("Invalid HTTP verb " + verb + ". Allowed verbs in HttpVerb class")
        resourcePattern = re.compile(self.pathRegex)
        if not resourcePattern.match(resource):
            raise NameError("Invalid resource path: " + resource + ". Path should match " + self.pathRegex)
        if resource[:1] == "/":
            resource = resource[1:]
        resourceArn = ("arn:aws:execute-api:" +
            self.region + ":" +
            self.awsAccountId + ":" +
            self.restApiId + "/" +
            self.stage + "/" +
            verb + "/" +
            resource)
        
        if effect.lower() == "allow":
            self.allowMethods.append({
                'resourceArn' : resourceArn,
                'conditions' : conditions
            })
        elif effect.lower() == "deny":
            self.denyMethods.append({
                'resourceArn' : resourceArn,
                'conditions' : conditions
            })
        
    def _getEmptyStatement(self, effect):
        statement = {
            'Action': 'execute-api:Invoke',
            'Effect': effect[:1].upper() + effect[1:].lower(),
            'Resource': []
        }

        return statement
    
    def _getStatementForEffect(self, effect, methods):
        statements = []

        if len(methods) > 0:
            statement = self._getEmptyStatement(effect)

            for curMethod in methods:
                if curMethod['conditions'] is None or len(curMethod['conditions']) == 0:
                    statement['Resource'].append(curMethod['resourceArn'])
                else:
                    conditionalStatement = self._getEmptyStatement(effect)
                    conditionalStatement['Resource'].append(curMethod['resourceArn'])
                    conditionalStatement['Condition'] = curMethod['conditions']
                    statements.append(conditionalStatement)

            statements.append(statement)

        return statements

    def allowAllMethods(self):
        self._addMethod("Allow", HttpVerb.ALL, "*", [])

    def denyAllMethods(self):
        self._addMethod("Deny", HttpVerb.ALL, "*", [])

    def allowMethod(self, verb, resource):
        self._addMethod("Allow", verb, resource, [])

    def denyMethod(self, verb, resource):
        self._addMethod("Deny", verb, resource, [])

    def allowMethodWithConditions(self, verb, resource, conditions):
        self._addMethod("Allow", verb, resource, conditions)

    def denyMethodWithConditions(self, verb, resource, conditions):
        self._addMethod("Deny", verb, resource, conditions)
    
    def build(self):
        if ((self.allowMethods is None or len(self.allowMethods) == 0) and
            (self.denyMethods is None or len(self.denyMethods) == 0)):
            raise NameError("No statements defined for the policy")

        policy = {
            'principalId' : self.principalId,
            'policyDocument' : {
                'Version' : self.version,
                'Statement' : []
            }
        }

        policy['policyDocument']['Statement'].extend(self._getStatementForEffect("Allow", self.allowMethods))
        policy['policyDocument']['Statement'].extend(self._getStatementForEffect("Deny", self.denyMethods))

        print(policy)

        return policy