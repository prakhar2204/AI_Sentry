"""AWS deployment through the same isolated official CLI profile as sign-in.

CloudFormation owns dependencies, readiness and rollback. Journals retain only
public account/resource metadata; tokens never pass through this process.
"""
from __future__ import annotations

import json

from .aws_cli import AwsCli, AwsCliError
from .aws_templates import build_template
from .base import (BaseDeployEngine, CredentialResult, CredentialStatus, DeployPlan,
                   DeployResource, DeployResult, DeployStatus, DryRunResult, RollbackResult)
from .state_store import DeploymentStore


class AwsDeployEngine(BaseDeployEngine):
    PROVIDER_ID = 'aws'

    def __init__(self, store=None, cli_factory=None):
        self.store = store or DeploymentStore()
        self.cli_factory = cli_factory or AwsCli

    def get_auth_url(self, redirect_port=9876):
        raise RuntimeError('Use official AWS CLI sign-in through CloudAuth')

    def exchange_auth_code(self, code, state):
        raise RuntimeError('OAuth codes are handled exclusively by the official CLI')

    def _client(self, credentials, region):
        cli = self.cli_factory(credentials, region)
        cli.verify()
        return cli

    def validate_credentials(self, credentials):
        try:
            self._client(credentials, credentials.get('region', ''))
            return CredentialResult(CredentialStatus.VALID, credentials['account_id'], 'AWS identity verified')
        except (ValueError, RuntimeError) as exc:
            return CredentialResult(CredentialStatus.INVALID, message=str(exc))

    def generate_plan(self, config, credentials, scan_report):
        DeploymentStore._check_no_credentials(config)
        plan = DeployPlan(provider='aws', region=config.get('region', ''), raw_config=dict(config))
        template = build_template(config, plan.deployment_id, credentials.get('account_id', ''))
        plan.resources = [DeployResource(item['Type'], resource_id=key, region=plan.region)
                          for key, item in template['Resources'].items()]
        plan.security_notes = [
            'Requests require AWS IAM authentication (SigV4). Internet reachable; no private VPC endpoint is created.',
            'The supplied execution role must trust Lambda or SageMaker and grant access to its model artifacts/services.',
            'CloudFormation manages only this deployment stack. Existing execution roles and model artifacts are not deleted.',
        ]
        if config['deployment_mode'] == 'bedrock':
            plan.security_notes += ['The gateway applies a versioned Bedrock guardrail to every Converse request.']
        plan.estimated_cost = self.estimate_cost(plan, credentials)
        return plan

    def estimate_cost(self, plan, credentials):
        return {'currency': 'USD', 'basis': 'not_estimated',
                'note': 'Account-specific pricing is not calculated. Review AWS pricing, model usage and instance charges before confirming.'}

    def dry_run(self, plan, credentials):
        try:
            template = self._template(plan, credentials)
            cli = self._client(credentials, plan.region)
            cli.call('cloudformation', 'validate-template', {'TemplateBody': json.dumps(template)})
            return DryRunResult(True, warnings=[
                'Template validation does not verify deployment permissions, IAM role policies, model access, image compatibility or quotas.',
                'No budget alert is created. Configure AWS Budgets separately before deploying.',
                'HTTP API requests time out after 30 seconds; use SageMaker for longer inference requests.',
            ], message='Identity and CloudFormation template validated. No resources have been created.')
        except (ValueError, RuntimeError) as exc:
            return DryRunResult(False, errors=[str(exc)])

    def _template(self, plan, credentials):
        self.store._path(plan.deployment_id)
        if plan.provider != 'aws' or plan.region != plan.raw_config.get('region'):
            raise ValueError('Deployment plan provider or region mismatch')
        return build_template(plan.raw_config, plan.deployment_id, credentials.get('account_id', ''))

    def _record(self, deployment_id, credentials):
        record = self.store.load(deployment_id)
        if not record or record.get('provider') != 'aws':
            raise ValueError('No AWS deployment journal found for this deployment ID')
        if record['account'] != credentials.get('account_id'):
            raise ValueError('Deployment belongs to a different AWS account')
        return record

    def deploy(self, plan, credentials, confirmed=False):
        self._require_confirmed(confirmed)
        template = self._template(plan, credentials)
        cli = self._client(credentials, plan.region)  # Reverify immediately before any mutation.
        existing = self.store.load(plan.deployment_id)
        if existing:
            if existing.get('config') != plan.raw_config:
                raise ValueError('Deployment ID already belongs to a different plan')
            return self.get_deployment_status(plan.deployment_id, credentials)
        record = {'deployment_id': plan.deployment_id, 'provider': 'aws', 'region': plan.region,
                  'account': credentials['account_id'], 'identity': credentials['identity'],
                  'config': plan.raw_config, 'status': 'pending', 'stack_id': '', 'endpoint_url': ''}
        # Persist intent before submission. A timeout must not cause a second stack.
        self.store.save(record)
        try:
            response = cli.call('cloudformation', 'create-stack', {
                'StackName': plan.deployment_id, 'TemplateBody': json.dumps(template),
                'ClientRequestToken': plan.deployment_id, 'OnFailure': 'ROLLBACK',
                'Tags': [{'Key': 'SentryPhi', 'Value': 'true'},
                         {'Key': 'DeploymentId', 'Value': plan.deployment_id}],
            })
            record.update(stack_id=response.get('StackId', ''), status='running')
            self.store.save(record)
            return DeployResult(DeployStatus.RUNNING, plan.deployment_id,
                                message='AWS accepted the stack. Waiting for resource readiness.')
        except AwsCliError:
            # Request outcome may be ambiguous; recovery checks actual stack ownership.
            return DeployResult(DeployStatus.UNKNOWN, plan.deployment_id,
                                errors=['Stack submission was not confirmed. Refresh status before retrying.'])

    def _stack(self, cli, record):
        stacks = cli.call('cloudformation', 'describe-stacks', {
            'StackName': record['stack_id'] or record['deployment_id']}).get('Stacks', [])
        if len(stacks) != 1:
            raise ValueError('AWS did not return a unique deployment stack')
        stack = stacks[0]
        tags = {tag['Key']: tag['Value'] for tag in stack.get('Tags', [])}
        arn = stack.get('StackId', '')
        parts = arn.split(':')
        if (len(parts) < 6 or parts[2] != 'cloudformation' or parts[3] != record['region'] or
                parts[4] != record['account'] or tags.get('SentryPhi') != 'true' or
                tags.get('DeploymentId') != record['deployment_id'] or
                stack.get('StackName') != record['deployment_id'] or
                (record['stack_id'] and arn != record['stack_id'])):
            raise ValueError('Stack ownership verification failed; no resources were changed')
        record['stack_id'] = arn
        return stack

    def get_deployment_status(self, deployment_id, credentials):
        record = self._record(deployment_id, credentials)
        cli = self._client(credentials, record['region'])
        try:
            stack = self._stack(cli, record)
        except AwsCliError as exc:
            if exc.code != 'NOT_FOUND':
                raise
            status = DeployStatus.ROLLED_BACK if record.get('delete_requested') else DeployStatus.UNKNOWN
            record.update(status=status.value, endpoint_url='')
            self.store.save(record)
            return DeployResult(status, deployment_id, message='AWS stack not found. No successful deployment is recorded.')
        cloud_status = stack.get('StackStatus', '')
        if cloud_status == 'CREATE_COMPLETE':
            status = DeployStatus.COMPLETE
        elif cloud_status == 'DELETE_COMPLETE':
            status = DeployStatus.ROLLED_BACK
        elif cloud_status.endswith('_IN_PROGRESS'):
            status = DeployStatus.RUNNING
        else:
            status = DeployStatus.FAILED  # ROLLBACK_COMPLETE is failed provisioning, not success.
        endpoint = next((item.get('OutputValue', '') for item in stack.get('Outputs', [])
                         if item.get('OutputKey') == 'EndpointUrl'), '') if status == DeployStatus.COMPLETE else ''
        if status == DeployStatus.COMPLETE and not endpoint.startswith('https://'):
            status = DeployStatus.FAILED
        record.update(status=status.value, endpoint_url=endpoint)
        self.store.save(record)
        return DeployResult(status, deployment_id, endpoint,
            resources=[DeployResource('CloudFormation stack', deployment_id, record['region'], record['stack_id'], cloud_status)],
            errors=[f'AWS provisioning status: {cloud_status}; inspect stack events in the AWS console.'] if status == DeployStatus.FAILED else [],
            message=f'AWS stack status: {cloud_status}')

    def rollback(self, deployment_id, credentials):
        record = self._record(deployment_id, credentials)
        cli = self._client(credentials, record['region'])
        self._stack(cli, record)  # Exact ARN/account/region/tags, never broad resource discovery.
        cli.call('cloudformation', 'delete-stack', {'StackName': record['stack_id']})
        record.update(status='deleting', endpoint_url='', delete_requested=True)
        self.store.save(record)
        return RollbackResult(True, message='Stack deletion requested. Poll status until AWS confirms deletion.')
