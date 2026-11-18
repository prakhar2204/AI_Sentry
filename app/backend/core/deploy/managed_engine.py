"""Model-bound deployment jobs using official CLIs and public resource journals.

Planning is local. Deployment is asynchronous so image builds do not block IPC.
Only the explicit execute action creates or uploads anything in a cloud account.
"""
from dataclasses import asdict
import json
from pathlib import Path
import subprocess
import threading
import time
import uuid
from urllib.request import urlopen

from .base import (BaseDeployEngine, CredentialResult, CredentialStatus, DeployPlan,
                   DeployResource, DeployResult, DeployStatus, DryRunResult, RollbackResult)
from .managed_cli import ManagedCli
from .model_package import package_model, zip_context
from .model_recommender import recommendations
from .state_store import DeploymentStore


class ManagedModelEngine(BaseDeployEngine):
    def __init__(self, provider, store=None, cli_factory=ManagedCli):
        self.PROVIDER_ID = provider
        self.store = store or DeploymentStore()
        self.cli_factory = cli_factory
        self.jobs = {}
        self.lock = threading.RLock()

    def get_auth_url(self, redirect_port=9876):
        raise RuntimeError('Use the official CLI browser sign-in')

    def exchange_auth_code(self, code, state):
        raise RuntimeError('Custom OAuth is disabled')

    def validate_credentials(self, credentials):
        if self.PROVIDER_ID != 'private':
            self.cli_factory(self.PROVIDER_ID, credentials, credentials.get('region', '')).verify()
        return CredentialResult(CredentialStatus.VALID, credentials.get('account_id', 'local'), 'Identity verified')

    def _validated_config(self, config):
        if config.get('deployment_mode') != 'managed_model':
            raise ValueError('Expected a scanned-model deployment')
        result = recommendations(config['model_source'], {self.PROVIDER_ID: config}, config['model_fingerprint'])
        offer = next(o for o in result['offers'] if o['provider'] == self.PROVIDER_ID)
        if not offer['fits']:
            raise ValueError('Selected instance does not have enough memory for this configuration')
        expected = offer['config']
        # Never trust renderer-supplied Docker settings, prices or resource names.
        for key in ('region', 'instance_type', 'replicas', 'context_length', 'concurrency', 'accelerator', 'model_format', 'endpoint_scope'):
            if config.get(key) != expected[key]:
                raise ValueError(f'Deployment setting changed or is unsupported: {key}. Recalculate the recommendation.')
        return expected, offer

    def generate_plan(self, config, credentials, scan_report):
        config, offer = self._validated_config(config)
        if scan_report.get('model_profile', {}).get('fingerprint') != config['model_fingerprint']:
            raise ValueError('A completed scan of this exact artifact is required')
        from core.model_profile import artifact_digest
        scanned_digest = scan_report.get('model_profile', {}).get('content_sha256')
        if not scanned_digest or artifact_digest(offer['model']) != scanned_digest:
            raise ValueError('A content-verified scan of this model is required. Rescan before deployment.')
        config['model_sha256'] = scanned_digest
        if self.PROVIDER_ID != 'private' and credentials.get('region') != config['region']:
            raise ValueError('Confirm the same region as the selected recommendation')
        resources = {
            'aws': ['Private model upload bucket', 'ECR image repository', 'CodeBuild image builder and IAM roles', 'SageMaker model and authenticated endpoint'],
            'azure': ['Dedicated resource group', 'Container registry and remote image build', 'ML workspace and supporting storage/key vault', 'Entra-authenticated managed online endpoint'],
            'gcp': ['Artifact Registry image repository', 'Dedicated build service account and private source/log bucket', 'Cloud Build image build', 'Vertex AI model and authenticated endpoint'],
            'private': ['Local Docker image', 'Loopback-only model container'],
        }[self.PROVIDER_ID]
        plan = DeployPlan(deployment_id='sp-' + uuid.uuid4().hex[:16], provider=self.PROVIDER_ID,
            region=config['region'], raw_config=config,
            resources=[DeployResource(r, region=config['region']) for r in resources],
            estimated_cost={'low_usd': offer['estimate']['monthly_usd'], 'high_usd': offer['estimate']['monthly_usd'],
                'currency': 'USD', 'basis': 'reference_catalog', 'note': 'Compute estimate only; builds, storage, registry and traffic are additional.'},
            security_notes=[f'Model: {offer["model"]["source"]} ({offer["model"]["size_bytes"]:,} bytes).',
                'The selected model files will be uploaded to your chosen cloud and included in its container image.' if self.PROVIDER_ID != 'private' else 'Model stays local. Docker must already be installed and running.',
                'Cloud endpoint invocation requires provider identity; local endpoint binds to 127.0.0.1.',
                'No application tokens or cloud credential files are included in the model package.',
                'Keep the app open during upload and provisioning. Failed builds can leave billable resources; use removal after reviewing the deployment.'])
        record = {'deployment_id': plan.deployment_id, 'provider': self.PROVIDER_ID, 'kind': 'managed_model',
            'account_id': credentials.get('account_id', 'local'), 'region': plan.region,
            'plan': plan.to_dict(), 'status': 'pending', 'message': 'Plan ready for validation',
            'resources': [], 'endpoint_url': '', 'errors': [], 'owned': {}}
        self.store.save(record)
        return plan

    def estimate_cost(self, plan, credentials):
        return self._record(plan.deployment_id, credentials)['plan']['estimated_cost']

    def _record(self, deployment_id, scope):
        record = self.store.load(deployment_id)
        if not record or record.get('kind') != 'managed_model' or record.get('provider') != self.PROVIDER_ID:
            raise ValueError('Unknown model deployment')
        if record['account_id'] != scope.get('account_id', 'local'):
            raise ValueError('This deployment belongs to a different account')
        return record

    def _check_plan(self, plan, scope):
        record = self._record(plan.deployment_id, scope)
        if record['plan'] != plan.to_dict():
            raise ValueError('Plan changed after review. Generate a new plan.')
        self._validated_config(plan.raw_config)
        return record

    def dry_run(self, plan, credentials):
        try:
            self._check_plan(plan, credentials)
            if self.PROVIDER_ID == 'private':
                self._docker(['info', '--format', '{{.ServerVersion}}'])
            else:
                cli = self.cli_factory(self.PROVIDER_ID, credentials, plan.region)
                cli.verify()
                if self.PROVIDER_ID == 'azure':
                    cli.call(['extension', 'show', '--name', 'ml'])
            return DryRunResult(True, warnings=['Capacity and price are estimates. Provider quota, build availability and resource permissions are checked during provisioning.'],
                message='Model, configuration and signed-in identity validated. No cloud resources have been created.')
        except (ValueError, RuntimeError, OSError) as error:
            return DryRunResult(False, errors=[str(error)])

    def _save(self, record, message=None, **changes):
        if message:
            record['message'] = message
        record.update(changes)
        self.store.save(record)

    @staticmethod
    def _result(record):
        return DeployResult(DeployStatus(record['status']), record['deployment_id'], record.get('endpoint_url', ''),
            [DeployResource(**r) for r in record.get('resources', [])], record.get('errors', []), record.get('message', ''))

    def deploy(self, plan, credentials, confirmed=False):
        self._require_confirmed(confirmed)
        with self.lock:
            record = self._check_plan(plan, credentials)
            if record['status'] != 'pending':
                return self._result(record)  # Idempotent execute, never provision duplicates.
            if self.PROVIDER_ID != 'private':
                self.cli_factory(self.PROVIDER_ID, credentials, plan.region).verify()
            self._save(record, 'Packaging the scanned model', status='running')
            thread = threading.Thread(target=self._work, args=(record, dict(credentials)), daemon=True)
            self.jobs[plan.deployment_id] = thread
            thread.start()
            return self._result(record)

    def _work(self, record, scope):
        try:
            directory = self.store.directory / (record['deployment_id'] + '-build')
            context = package_model(record['plan']['raw_config'], directory / 'context')
            if self.PROVIDER_ID == 'private':
                endpoint = self._private(record, context)
            else:
                cli = self.cli_factory(self.PROVIDER_ID, scope, record['region'])
                cli.verify()  # Packaging can take a long time; recheck before first cloud mutation.
                endpoint = getattr(self, '_' + self.PROVIDER_ID)(record, cli, context)
            self._save(record, 'Model endpoint is ready. Invocation requires the displayed provider identity.',
                       status='complete', endpoint_url=endpoint)
        except Exception as error:
            # All external command errors are sanitized by the transport.
            self._save(record, 'Deployment stopped. Review resources before retrying or removing them.',
                       status='failed', errors=[str(error)])

    def get_deployment_status(self, deployment_id, credentials):
        record = self._record(deployment_id, credentials)
        if record['status'] == 'running' and deployment_id not in self.jobs:
            self._save(record, 'The app restarted during provisioning. Cloud work may still be running. Inspect provider resources before removal.',
                       status='failed', errors=['Provisioning was interrupted; automatic recreation is disabled to prevent duplicates.'])
        return self._result(record)

    @staticmethod
    def _json(directory, name, data):
        filename = directory / (name + '.json')
        filename.write_text(json.dumps(data), encoding='utf-8')
        return str(filename)

    def _poll(self, fetch, ready, failed, timeout=7200):
        deadline = time.monotonic() + timeout
        while True:
            value = fetch()
            if ready(value):
                return value
            if failed(value):
                raise RuntimeError('Provider reported a failed build or deployment. Review its activity logs.')
            if time.monotonic() >= deadline:
                raise RuntimeError('Provisioning timed out; resources may still be active. Inspect before removal.')
            time.sleep(10)

    def _own(self, record, kind, identifier):
        record['owned'][kind] = identifier
        record['resources'].append(asdict(DeployResource(kind, identifier, record['region'], identifier, 'created')))
        self.store.save(record)

    def _aws(self, record, cli, context):
        from .managed_templates import bootstrap_template, endpoint_template
        name = record['deployment_id']
        def stack(suffix, template):
            stack_name = name + suffix
            path = self._json(context.parent, suffix.strip('-'), template)
            # Journal the intended stack name before the request (lost responses remain recoverable).
            self._own(record, suffix, stack_name)
            created = cli.call(['cloudformation', 'create-stack', '--stack-name', stack_name,
                '--template-body', 'file://' + path, '--capabilities', 'CAPABILITY_IAM',
                '--tags', 'Key=SentryPhi,Value=true', 'Key=DeploymentId,Value=' + name,
                '--client-request-token', name + suffix])
            record['owned'][suffix] = created['StackId']
            self.store.save(record)
            response = self._poll(lambda: cli.call(['cloudformation', 'describe-stacks', '--stack-name', created['StackId']])['Stacks'][0],
                lambda r: r['StackStatus'] == 'CREATE_COMPLETE',
                lambda r: 'FAILED' in r['StackStatus'] or 'ROLLBACK' in r['StackStatus'])
            return {o['OutputKey']: o['OutputValue'] for o in response.get('Outputs', [])}
        self._save(record, 'Creating private build resources')
        output = stack('-build', bootstrap_template(name))
        self._own(record, 'source_bucket', output['Bucket'])
        self._save(record, 'Uploading the model package to your private bucket')
        cli.call(['s3', 'cp', str(zip_context(context)), 's3://' + output['Bucket'] + '/source.zip', '--only-show-errors'], output=False, timeout=7200)
        self._save(record, 'Building the model container in AWS CodeBuild')
        build = cli.call(['codebuild', 'start-build', '--project-name', output['BuildProject'], '--idempotency-token', name])['build']['id']
        self._own(record, 'build_job', build)
        self._poll(lambda: cli.call(['codebuild', 'batch-get-builds', '--ids', build])['builds'][0],
            lambda r: r['buildStatus'] == 'SUCCEEDED', lambda r: r['buildStatus'] in ('FAILED', 'FAULT', 'STOPPED', 'TIMED_OUT'))
        self._save(record, 'Starting the SageMaker model endpoint and waiting for health checks')
        stack('-endpoint', endpoint_template(name, record['plan']['raw_config'], output['Image'], output['Role']))
        info = cli.call(['sagemaker', 'describe-endpoint', '--endpoint-name', name])
        if info.get('EndpointStatus') != 'InService':
            raise RuntimeError('SageMaker has not reported the model endpoint InService')
        return f'https://runtime.sagemaker.{record["region"]}.amazonaws.com/endpoints/{name}/invocations'

    def _azure(self, record, cli, context):
        name, region = record['deployment_id'], record['region']
        compact = name.replace('-', '')
        self._own(record, 'resource_group', name)
        self._save(record, 'Creating the model resource group and registry')
        cli.call(['group', 'create', '--name', name, '--location', region, '--tags', 'SentryPhi=true', 'DeploymentId=' + name])
        registry = cli.call(['acr', 'create', '--resource-group', name, '--name', compact, '--sku', 'Basic', '--admin-enabled', 'false'])
        self._save(record, 'Uploading and building the model container in Azure Container Registry')
        cli.call(['acr', 'build', '--registry', compact, '--image', 'model:scanned', '--no-logs', str(context)], output=False, timeout=7200)
        self._save(record, 'Creating the Azure ML workspace')
        workspace_file = self._json(context.parent, 'workspace', {'name': name, 'location': region,
            'container_registry': registry['id'], 'tags': {'SentryPhi': 'true', 'DeploymentId': name}})
        cli.call(['ml', 'workspace', 'create', '--resource-group', name, '--file', workspace_file], timeout=1800)
        shared = ['--resource-group', name, '--workspace-name', name]
        endpoint_file = self._json(context.parent, 'endpoint', {'name': name, 'auth_mode': 'aad_token',
            'identity': {'type': 'system_assigned'}, 'tags': {'SentryPhi': 'true', 'DeploymentId': name}})
        endpoint = cli.call(['ml', 'online-endpoint', 'create', *shared, '--file', endpoint_file], timeout=1800)
        principal = endpoint.get('identity', {}).get('principal_id')
        if not principal:
            raise RuntimeError('Azure did not return an endpoint managed identity')
        cli.call(['role', 'assignment', 'create', '--assignee-object-id', principal, '--assignee-principal-type', 'ServicePrincipal', '--role', 'AcrPull', '--scope', registry['id']])
        cfg = record['plan']['raw_config']
        deployment = {'name': 'model', 'endpoint_name': name, 'instance_type': cfg['instance_type'],
            'instance_count': cfg['replicas'], 'environment': {'image': registry['loginServer'] + '/model:scanned',
                'inference_config': {'liveness_route': {'port': 8080, 'path': '/health'},
                    'readiness_route': {'port': 8080, 'path': '/health'}, 'scoring_route': {'port': 8080, 'path': '/invocations'}}},
            'liveness_probe': {'initial_delay': 300, 'period': 10, 'failure_threshold': 30},
            'readiness_probe': {'initial_delay': 10, 'period': 10, 'failure_threshold': 60},
            'request_settings': {'request_timeout_ms': 180000, 'max_concurrent_requests_per_instance': cfg['concurrency']}}
        path = self._json(context.parent, 'deployment', deployment)
        self._save(record, 'Loading the model in Azure ML and waiting for health checks')
        cli.call(['ml', 'online-deployment', 'create', *shared, '--file', path, '--all-traffic', '--skip-script-validation'], timeout=7200)
        status = cli.call(['ml', 'online-deployment', 'show', *shared, '--endpoint-name', name, '--name', 'model'])
        endpoint = cli.call(['ml', 'online-endpoint', 'show', *shared, '--name', name])
        if status.get('provisioning_state') != 'Succeeded' or not endpoint.get('scoring_uri'):
            raise RuntimeError('Azure has not reported a ready scoring endpoint')
        return endpoint['scoring_uri']

    def _gcp(self, record, cli, context):
        name, region, project = record['deployment_id'], record['region'], record['account_id']
        self._save(record, 'Enabling model build and serving APIs')
        cli.call(['services', 'enable', 'aiplatform.googleapis.com', 'artifactregistry.googleapis.com', 'cloudbuild.googleapis.com'], output=False, timeout=900)
        self._own(record, 'repository', name)
        cli.call(['artifacts', 'repositories', 'create', name, '--location', region, '--repository-format', 'docker', '--labels', 'sentryphi=true,deployment-id=' + name])
        account = name + '@' + project + '.iam.gserviceaccount.com'
        self._own(record, 'build_account', account)
        cli.call(['iam', 'service-accounts', 'create', name, '--display-name', name, '--description', 'SentryPhi deployment ' + name])
        cli.call(['iam', 'service-accounts', 'add-iam-policy-binding', account,
            '--member', 'user:' + cli.scope['identity'], '--role', 'roles/iam.serviceAccountUser'])
        cli.call(['artifacts', 'repositories', 'add-iam-policy-binding', name, '--location', region,
            '--member', 'serviceAccount:' + account, '--role', 'roles/artifactregistry.writer'])
        bucket = 'gs://' + project + '-' + name
        self._own(record, 'source_bucket', bucket)
        cli.call(['storage', 'buckets', 'create', bucket, '--location', region, '--uniform-bucket-level-access',
            '--public-access-prevention', '--soft-delete-duration', '0', '--labels', 'sentryphi=true,deployment-id=' + name])
        cli.call(['storage', 'buckets', 'add-iam-policy-binding', bucket, '--member', 'serviceAccount:' + account,
            '--role', 'roles/storage.objectAdmin'])
        image = f'{region}-docker.pkg.dev/{project}/{name}/model:scanned'
        self._save(record, 'Uploading and building the model container with Cloud Build')
        build = cli.call(['builds', 'submit', str(context), '--tag', image, '--region', region, '--suppress-logs', '--async',
            '--service-account', 'projects/' + project + '/serviceAccounts/' + account,
            '--gcs-source-staging-dir', bucket + '/source', '--gcs-log-dir', bucket + '/logs', '--timeout', '5400s'], timeout=7200)
        self._own(record, 'build_job', build['id'])
        self._poll(lambda: cli.call(['builds', 'describe', build['id'], '--region', region]),
            lambda r: r['status'] == 'SUCCESS', lambda r: r['status'] in ('FAILURE', 'INTERNAL_ERROR', 'TIMEOUT', 'CANCELLED', 'EXPIRED'))
        self._save(record, 'Registering the built model with Vertex AI')
        self._own(record, 'model', name)
        cli.call(['ai', 'models', 'upload', '--region', region, '--model-id', name, '--display-name', name,
            '--container-image-uri', image, '--container-ports', '8080', '--container-health-route', '/health',
            '--container-predict-route', '/predict', '--container-deployment-timeout-seconds', '1800',
            '--labels', 'sentryphi=true,deployment-id=' + name], timeout=1800)
        endpoint_id = str(uuid.uuid4().int % (10 ** 18))
        self._own(record, 'endpoint', endpoint_id)
        cli.call(['ai', 'endpoints', 'create', '--region', region, '--endpoint-id', endpoint_id,
            '--display-name', name, '--labels', 'sentryphi=true,deployment-id=' + name], timeout=1800)
        cfg = record['plan']['raw_config']
        args = ['ai', 'endpoints', 'deploy-model', endpoint_id, '--region', region, '--model', name,
            '--display-name', name, '--machine-type', cfg['instance_type'].split('+')[0],
            '--min-replica-count', str(cfg['replicas']), '--max-replica-count', str(cfg['replicas']), '--traffic-split', '0=100']
        if cfg['accelerator'] == 'gpu':
            args += ['--accelerator', 'type=nvidia-tesla-t4,count=1']
        self._save(record, 'Loading the model on Vertex AI and waiting for health checks')
        cli.call(args, timeout=7200)
        endpoint = cli.call(['ai', 'endpoints', 'describe', endpoint_id, '--region', region])
        if not endpoint.get('deployedModels') or not endpoint.get('trafficSplit'):
            raise RuntimeError('Vertex AI has not reported a deployed model with traffic')
        return f'https://{region}-aiplatform.googleapis.com/v1/projects/{project}/locations/{region}/endpoints/{endpoint_id}:predict'

    @staticmethod
    def _docker(args, timeout=60):
        try:
            result = subprocess.run(['docker', *args], stdout=subprocess.PIPE, stderr=subprocess.PIPE,
                text=True, timeout=timeout, shell=False,
                creationflags=getattr(subprocess, 'CREATE_NO_WINDOW', 0))
        except (FileNotFoundError, subprocess.TimeoutExpired):
            raise RuntimeError('Docker is missing, not running, or timed out. Start Docker Desktop and retry.') from None
        if result.returncode:
            raise RuntimeError('Docker failed. Check Docker Desktop, available memory and whether port 8080 is free.')
        return result.stdout

    def _private(self, record, context):
        name = record['deployment_id']
        self._save(record, 'Building the model image with local Docker')
        self._docker(['build', '--label', 'ai.sentryphi.deployment=' + name, '-t', name, str(context)], timeout=7200)
        self._own(record, 'docker_image', name)
        self._own(record, 'docker_container', name)
        self._docker(['run', '-d', '--name', name, '--label', 'ai.sentryphi.deployment=' + name,
            '--restart', 'unless-stopped', '-p', '127.0.0.1:8080:8080', name])
        self._save(record, 'Waiting for local model readiness')
        def healthy():
            try:
                with urlopen('http://127.0.0.1:8080/health', timeout=5) as response:
                    return response.status == 200
            except OSError:
                return False
        self._poll(healthy, bool, lambda _: False, timeout=1800)
        return 'http://127.0.0.1:8080/v1/chat/completions'

    def rollback(self, deployment_id, credentials):
        with self.lock:
            record = self._record(deployment_id, credentials)
            job = self.jobs.get(deployment_id)
            if job and job.is_alive():
                return RollbackResult(False, errors=['Provisioning is still running. Wait for it to finish before removing resources.'])
            if record['status'] == 'rolled_back':
                return RollbackResult(True, message='Resources already removed')
            cli = None
            if self.PROVIDER_ID != 'private':
                cli = self.cli_factory(self.PROVIDER_ID, credentials, record['region'])
                cli.verify()
            try:
                self._remove(record, cli)
                self._save(record, 'Deployment resources removed', status='rolled_back', errors=[], endpoint_url='')
                return RollbackResult(True, deleted=list(record['owned'].values()), message=record['message'])
            except Exception as error:
                return RollbackResult(False, errors=[str(error)], message='Removal incomplete. Inspect provider resources before retrying.')

    def _remove(self, record, cli):
        owned, name, region = record['owned'], record['deployment_id'], record['region']
        if self.PROVIDER_ID == 'aws':
            for key in ('-endpoint', '-build'):
                if key not in owned:
                    continue
                stack = cli.call(['cloudformation', 'describe-stacks', '--stack-name', owned[key]])['Stacks'][0]
                tags = {t['Key']: t['Value'] for t in stack.get('Tags', [])}
                if tags.get('DeploymentId') != name or tags.get('SentryPhi') != 'true':
                    raise ValueError('Stack ownership could not be verified; removal refused')
                if stack['StackStatus'] == 'DELETE_COMPLETE':
                    continue
                if key == '-build':
                    if 'build_job' in owned:
                        cli.call(['codebuild', 'stop-build', '--id', owned['build_job']])
                    outputs = {v['OutputKey']: v['OutputValue'] for v in stack.get('Outputs', [])}
                    if outputs.get('Bucket'):
                        cli.call(['s3', 'rm', 's3://' + outputs['Bucket'] + '/source.zip', '--only-show-errors'], output=False)
                cli.call(['cloudformation', 'delete-stack', '--stack-name', owned[key]])
                cli.call(['cloudformation', 'wait', 'stack-delete-complete', '--stack-name', owned[key]], output=False, timeout=7200)
        elif self.PROVIDER_ID == 'azure' and 'resource_group' in owned:
            group = cli.call(['group', 'show', '--name', owned['resource_group']])
            if group.get('tags', {}).get('DeploymentId') != name:
                raise ValueError('Resource-group ownership could not be verified; removal refused')
            cli.call(['group', 'delete', '--name', owned['resource_group'], '--yes'], output=False, timeout=7200)
        elif self.PROVIDER_ID == 'gcp':
            if 'build_job' in owned:
                build = cli.call(['builds', 'describe', owned['build_job'], '--region', region])
                if build.get('status') in ('QUEUED', 'WORKING', 'PENDING'):
                    cli.call(['builds', 'cancel', owned['build_job'], '--region', region])
                    self._poll(lambda: cli.call(['builds', 'describe', owned['build_job'], '--region', region]),
                        lambda r: r['status'] not in ('QUEUED', 'WORKING', 'PENDING'), lambda _: False, timeout=600)
            for kind in ('endpoint', 'model', 'repository'):
                if kind not in owned:
                    continue
                prefix = ['artifacts', 'repositories'] if kind == 'repository' else ['ai', kind + 's']
                location = ['--location', region] if kind == 'repository' else ['--region', region]
                info = cli.call([*prefix, 'describe', owned[kind], *location])
                if info.get('labels', {}).get('deployment-id') != name:
                    raise ValueError('Resource ownership could not be verified; removal refused')
                if kind == 'endpoint':
                    for deployed in info.get('deployedModels', []):
                        cli.call(['ai', 'endpoints', 'undeploy-model', owned[kind], *location,
                            '--deployed-model-id', deployed['id']], timeout=7200)
                cli.call([*prefix, 'delete', owned[kind], *location], output=False, timeout=1800)
            if 'source_bucket' in owned:
                bucket = cli.call(['storage', 'buckets', 'describe', owned['source_bucket']])
                if bucket.get('labels', {}).get('deployment-id') != name:
                    raise ValueError('Source-bucket ownership could not be verified; removal refused')
                cli.call(['storage', 'rm', '--recursive', owned['source_bucket']], output=False, timeout=1800)
            if 'build_account' in owned:
                account = cli.call(['iam', 'service-accounts', 'describe', owned['build_account']])
                if account.get('description') != 'SentryPhi deployment ' + name:
                    raise ValueError('Build-account ownership could not be verified; removal refused')
                cli.call(['iam', 'service-accounts', 'delete', owned['build_account']], output=False)
        elif self.PROVIDER_ID == 'private':
            if 'docker_container' in owned:
                values = json.loads(self._docker(['inspect', owned['docker_container']]))
                if values[0]['Config']['Labels'].get('ai.sentryphi.deployment') != name:
                    raise ValueError('Container ownership could not be verified; removal refused')
                self._docker(['rm', '-f', owned['docker_container']])
            if 'docker_image' in owned:
                self._docker(['image', 'rm', owned['docker_image']])


MANAGED_ENGINES = {provider: ManagedModelEngine(provider) for provider in ('aws', 'azure', 'gcp', 'private')}
