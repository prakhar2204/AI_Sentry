"""AWS resources for building and hosting the inspected model image."""
import json


def bootstrap_template(name):
    ref = lambda value: {'Ref': value}
    attr = lambda value, key: {'Fn::GetAtt': [value, key]}
    sub = lambda value: {'Fn::Sub': value}
    def role(service, statements):
        return {'Type': 'AWS::IAM::Role', 'Properties': {
            'AssumeRolePolicyDocument': {'Version': '2012-10-17', 'Statement': [{
                'Effect': 'Allow', 'Principal': {'Service': service}, 'Action': 'sts:AssumeRole'}]},
            'Policies': [{'PolicyName': 'ModelResources', 'PolicyDocument': {
                'Version': '2012-10-17', 'Statement': statements}}]}}
    def allow(actions, resource):
        return {'Effect': 'Allow', 'Action': actions, 'Resource': resource}
    ecr_read = ['ecr:BatchCheckLayerAvailability', 'ecr:BatchGetImage', 'ecr:GetDownloadUrlForLayer']
    logs = sub('arn:${AWS::Partition}:logs:${AWS::Region}:${AWS::AccountId}:log-group:/aws/*:*')
    buildspec = {'version': '0.2', 'phases': {
        'pre_build': {'commands': ['aws ecr get-login-password --region "$AWS_DEFAULT_REGION" | docker login --username AWS --password-stdin "$REGISTRY"']},
        'build': {'commands': ['docker build -t "$IMAGE" .']},
        'post_build': {'commands': ['docker push "$IMAGE"']}}}
    resources = {
        'Source': {'Type': 'AWS::S3::Bucket', 'Properties': {
            'PublicAccessBlockConfiguration': {k: True for k in ('BlockPublicAcls', 'BlockPublicPolicy', 'IgnorePublicAcls', 'RestrictPublicBuckets')},
            'BucketEncryption': {'ServerSideEncryptionConfiguration': [{'ServerSideEncryptionByDefault': {'SSEAlgorithm': 'AES256'}}]}}},
        'Repository': {'Type': 'AWS::ECR::Repository', 'Properties': {
            'RepositoryName': name, 'EmptyOnDelete': True, 'ImageTagMutability': 'IMMUTABLE',
            'ImageScanningConfiguration': {'ScanOnPush': True}}},
        'BuildRole': role('codebuild.amazonaws.com', [
            allow(['s3:GetObject', 's3:GetObjectVersion'], sub('${Source.Arn}/*')),
            allow(['s3:GetBucketLocation'], attr('Source', 'Arn')),
            allow(['ecr:GetAuthorizationToken'], '*'),
            allow(ecr_read + ['ecr:InitiateLayerUpload', 'ecr:UploadLayerPart', 'ecr:CompleteLayerUpload', 'ecr:PutImage'], attr('Repository', 'Arn')),
            allow(['logs:CreateLogGroup', 'logs:CreateLogStream', 'logs:PutLogEvents'], logs)]),
        'ServeRole': role('sagemaker.amazonaws.com', [
            allow(['ecr:GetAuthorizationToken'], '*'), allow(ecr_read, attr('Repository', 'Arn')),
            allow(['logs:CreateLogGroup', 'logs:CreateLogStream', 'logs:PutLogEvents'], logs),
            allow(['cloudwatch:PutMetricData'], '*')]),
        'Build': {'Type': 'AWS::CodeBuild::Project', 'Properties': {
            'Name': name, 'ServiceRole': attr('BuildRole', 'Arn'), 'TimeoutInMinutes': 90,
            'Artifacts': {'Type': 'NO_ARTIFACTS'},
            'Source': {'Type': 'S3', 'Location': sub('${Source}/source.zip'), 'BuildSpec': json.dumps(buildspec)},
            'Environment': {'Type': 'LINUX_CONTAINER', 'ComputeType': 'BUILD_GENERAL1_MEDIUM',
                'Image': 'aws/codebuild/standard:7.0', 'PrivilegedMode': True,
                'EnvironmentVariables': [
                    {'Name': 'REGISTRY', 'Value': sub('${AWS::AccountId}.dkr.ecr.${AWS::Region}.${AWS::URLSuffix}')},
                    {'Name': 'IMAGE', 'Value': sub('${Repository.RepositoryUri}:model')} ]}}},
    }
    return {'AWSTemplateFormatVersion': '2010-09-09', 'Resources': resources, 'Outputs': {
        'Bucket': {'Value': ref('Source')}, 'Image': {'Value': sub('${Repository.RepositoryUri}:model')},
        'Role': {'Value': attr('ServeRole', 'Arn')}, 'BuildProject': {'Value': ref('Build')}}}


def endpoint_template(name, config, image, role):
    return {'AWSTemplateFormatVersion': '2010-09-09', 'Resources': {
        'Model': {'Type': 'AWS::SageMaker::Model', 'Properties': {
            'ModelName': name, 'ExecutionRoleArn': role, 'EnableNetworkIsolation': True,
            'PrimaryContainer': {'Image': image, 'Mode': 'SingleModel'}}},
        'Configuration': {'Type': 'AWS::SageMaker::EndpointConfig', 'Properties': {
            'ProductionVariants': [{'ModelName': {'Fn::GetAtt': ['Model', 'ModelName']},
                'VariantName': 'model', 'InitialInstanceCount': config['replicas'],
                'InstanceType': config['instance_type'], 'InitialVariantWeight': 1,
                'ContainerStartupHealthCheckTimeoutInSeconds': 600}]}},
        'Endpoint': {'Type': 'AWS::SageMaker::Endpoint', 'Properties': {
            'EndpointName': name, 'EndpointConfigName': {'Fn::GetAtt': ['Configuration', 'EndpointConfigName']}}},
    }}
