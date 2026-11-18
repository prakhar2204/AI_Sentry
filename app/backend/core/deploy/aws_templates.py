"""Explicit CloudFormation resources for the existing three AWS deployment modes."""
from __future__ import annotations

import re

BEDROCK_HANDLER = '''import base64, json, os
import boto3
client = boto3.client("bedrock-runtime")
def handler(event, context):
    try:
        body = event.get("body") or "{}"
        if event.get("isBase64Encoded"):
            body = base64.b64decode(body).decode("utf-8")
        data = json.loads(body)
        if not isinstance(data, dict):
            raise ValueError("Expected an object")
        messages = data.get("messages")
        if not isinstance(messages, list) or not messages:
            return {"statusCode": 400, "body": json.dumps({"error": "Provide Bedrock Converse messages"})}
        for message in messages:
            if not isinstance(message, dict) or message.get("role") not in ("user", "assistant"):
                raise ValueError("Invalid message")
            content = message.get("content")
            if not isinstance(content, list) or not content:
                raise ValueError("Expected text content")
            for block in content:
                if not isinstance(block, dict) or set(block) != {"text"} or not isinstance(block["text"], str):
                    raise ValueError("Only plain text blocks are supported")
        # Caller-supplied guardContent blocks are rejected: selective guarding
        # would allow the caller to exclude other text from evaluation.
        result = client.converse(modelId=os.environ["MODEL_ID"], messages=messages,
            guardrailConfig={"guardrailIdentifier": os.environ["GUARDRAIL_ID"],
                             "guardrailVersion": os.environ["GUARDRAIL_VERSION"]})
        return {"statusCode": 200, "headers": {"content-type": "application/json"},
                "body": json.dumps({"output": result.get("output"), "stopReason": result.get("stopReason")})}
    except (ValueError, TypeError):
        return {"statusCode": 400, "body": json.dumps({"error": "Invalid request"})}
    except Exception:
        return {"statusCode": 502, "body": json.dumps({"error": "Model invocation failed; check model access and execution-role permissions"})}
'''


def build_template(config, deployment_id, account):
    mode = config.get('deployment_mode')
    if mode not in ('bedrock', 'sagemaker', 'lambda'):
        raise ValueError('Choose a supported AWS deployment mode')
    if config.get('endpoint_scope') != 'public':
        raise ValueError('AWS private networking is not implemented. Select the IAM-authenticated public endpoint explicitly, or use private deployment artifacts.')
    role = config.get('execution_role_arn', '')
    if not re.fullmatch(r'arn:aws(?:-[a-z-]+)?:iam::' + re.escape(account) + r':role/[\w+=,.@/-]+', role):
        raise ValueError('Provide an existing execution role ARN in the confirmed AWS account')
    resources, outputs = {}, {}
    tags = [{'Key': 'SentryPhi', 'Value': 'true'}, {'Key': 'DeploymentId', 'Value': deployment_id}]
    if mode == 'sagemaker':
        image, model = config.get('container_image', ''), config.get('model_data_url', '')
        if not re.fullmatch(r'\d{12}\.dkr\.ecr\.[a-z0-9-]+\.amazonaws\.com(?:\.cn)?/[\w./:@-]+', image):
            raise ValueError('Provide the SageMaker-compatible ECR inference image URI')
        if not re.fullmatch(r's3://[a-z0-9][a-z0-9.-]+/[^\s]+', model):
            raise ValueError('Provide the S3 model artifact URL (model.tar.gz)')
        instance = config.get('instance_type', '')
        if not re.fullmatch(r'ml\.[a-z0-9]+\.[a-z0-9]+', instance):
            raise ValueError('Choose a SageMaker instance type')
        resources.update({
            'Model': {'Type': 'AWS::SageMaker::Model', 'Properties': {
                'ExecutionRoleArn': role, 'EnableNetworkIsolation': True,
                'PrimaryContainer': {'Image': image, 'ModelDataUrl': model}, 'Tags': tags}},
            'EndpointConfig': {'Type': 'AWS::SageMaker::EndpointConfig', 'Properties': {
                'ProductionVariants': [{'ModelName': {'Fn::GetAtt': ['Model', 'ModelName']},
                    'VariantName': 'AllTraffic', 'InitialInstanceCount': 1,
                    'InstanceType': instance, 'InitialVariantWeight': 1}], 'Tags': tags}},
            'Endpoint': {'Type': 'AWS::SageMaker::Endpoint', 'Properties': {
                'EndpointName': deployment_id, 'EndpointConfigName': {'Fn::GetAtt': ['EndpointConfig', 'EndpointConfigName']}, 'Tags': tags}},
        })
        outputs['EndpointUrl'] = {'Value': {'Fn::Sub': 'https://runtime.sagemaker.${AWS::Region}.${AWS::URLSuffix}/endpoints/${Endpoint.EndpointName}/invocations'}}
    else:
        props = {'Role': role, 'Timeout': 120, 'MemorySize': 1024, 'Tags': tags}
        if mode == 'lambda':
            image = config.get('container_image', '')
            if not re.fullmatch(r'\d{12}\.dkr\.ecr\.[a-z0-9-]+\.amazonaws\.com(?:\.cn)?/[\w./:@-]+', image):
                raise ValueError('Provide a Lambda-compatible ECR image URI containing your inference handler')
            props.update(PackageType='Image', Code={'ImageUri': image})
        else:
            model = config.get('model_id', '')
            if not re.fullmatch(r'[A-Za-z0-9.:/_-]{1,2048}', model):
                raise ValueError('Provide the Bedrock Converse-compatible model or inference profile ID')
            resources['Guardrail'] = {'Type': 'AWS::Bedrock::Guardrail', 'Properties': {
                'Name': deployment_id, 'BlockedInputMessaging': 'Request blocked by safety policy',
                'BlockedOutputsMessaging': 'Response blocked by safety policy', 'Tags': tags,
                'ContentPolicyConfig': {'FiltersConfig': [{'Type': kind, 'InputStrength': 'HIGH', 'OutputStrength': 'NONE' if kind == 'PROMPT_ATTACK' else 'HIGH'}
                    for kind in ('HATE', 'INSULTS', 'SEXUAL', 'VIOLENCE', 'MISCONDUCT', 'PROMPT_ATTACK')]}}}
            resources['GuardrailVersion'] = {'Type': 'AWS::Bedrock::GuardrailVersion', 'Properties': {
                'GuardrailIdentifier': {'Fn::GetAtt': ['Guardrail', 'GuardrailId']}}}
            props.update(Runtime='python3.12', Handler='index.handler', Code={'ZipFile': BEDROCK_HANDLER},
                         Environment={'Variables': {'MODEL_ID': model,
                            'GUARDRAIL_ID': {'Fn::GetAtt': ['Guardrail', 'GuardrailId']},
                            'GUARDRAIL_VERSION': {'Fn::GetAtt': ['GuardrailVersion', 'Version']}}})
        resources['Function'] = {'Type': 'AWS::Lambda::Function', 'Properties': props}
        resources.update({
            'Api': {'Type': 'AWS::ApiGatewayV2::Api', 'Properties': {'Name': deployment_id, 'ProtocolType': 'HTTP'}},
            'Integration': {'Type': 'AWS::ApiGatewayV2::Integration', 'Properties': {
                'ApiId': {'Ref': 'Api'}, 'IntegrationType': 'AWS_PROXY', 'PayloadFormatVersion': '2.0',
                'IntegrationUri': {'Fn::GetAtt': ['Function', 'Arn']}, 'TimeoutInMillis': 30000}},
            'Route': {'Type': 'AWS::ApiGatewayV2::Route', 'Properties': {
                'ApiId': {'Ref': 'Api'}, 'RouteKey': 'POST /invoke', 'AuthorizationType': 'AWS_IAM',
                'Target': {'Fn::Join': ['/', ['integrations', {'Ref': 'Integration'}]]}}},
            'Stage': {'Type': 'AWS::ApiGatewayV2::Stage', 'DependsOn': 'Route', 'Properties': {
                'ApiId': {'Ref': 'Api'}, 'StageName': '$default', 'AutoDeploy': True,
                'DefaultRouteSettings': {'ThrottlingBurstLimit': 10, 'ThrottlingRateLimit': 5}}},
            'InvokePermission': {'Type': 'AWS::Lambda::Permission', 'Properties': {
                'FunctionName': {'Ref': 'Function'}, 'Action': 'lambda:InvokeFunction',
                'Principal': 'apigateway.amazonaws.com',
                'SourceArn': {'Fn::Sub': 'arn:${AWS::Partition}:execute-api:${AWS::Region}:${AWS::AccountId}:${Api}/*/POST/invoke'}}},
        })
        outputs['EndpointUrl'] = {'Value': {'Fn::Join': ['', [{'Fn::GetAtt': ['Api', 'ApiEndpoint']}, '/invoke']]}}
    return {'AWSTemplateFormatVersion': '2010-09-09', 'Resources': resources, 'Outputs': outputs}
