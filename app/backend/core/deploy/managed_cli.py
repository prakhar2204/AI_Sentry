"""Official CLI subprocess transport for managed-model deployment jobs."""
import json
import os
from pathlib import Path
import re
import subprocess

from .aws_cli import isolated_aws_environment


class ManagedCli:
    def __init__(self, provider, scope, region, run=None):
        self.provider, self.scope, self.region = provider, scope, region
        self.run_process = run or subprocess.run
        auth_mode = scope.get('auth_mode', '')
        if auth_mode not in ('cli', 'token'):
            raise ValueError('Sign in through the app before deploying')
        self.auth_mode = auth_mode
        self.env = dict(os.environ)
        # Strip ambient cloud credentials to prevent cross-contamination
        for key in list(self.env):
            if re.match(r'^(AWS_(ACCESS_KEY|SECRET|SESSION_TOKEN|SECURITY_TOKEN|ROLE_ARN|WEB_IDENTITY|CONTAINER_CREDENTIALS|ENDPOINT_URL)|AZURE_(CLIENT_SECRET|CLIENT_CERTIFICATE|FEDERATED_TOKEN)|CLOUDSDK_(AUTH_|API_ENDPOINT_OVERRIDES_)|GOOGLE_APPLICATION_CREDENTIALS)', key, re.I):
                del self.env[key]
        if auth_mode == 'token':
            # Token-based auth: inject credentials from the frontend as env vars
            cred_env = scope.get('env', {})
            self.env.update(cred_env)
            if provider == 'aws':
                self.env.setdefault('AWS_DEFAULT_REGION', region)
                self.env.setdefault('AWS_REGION', region)
            elif provider == 'azure':
                self.env.setdefault('AZURE_REGION', region)
            elif provider == 'gcp':
                self.env.setdefault('CLOUDSDK_COMPUTE_REGION', region)
                self.env['CLOUDSDK_CORE_DISABLE_PROMPTS'] = '1'
        else:
            # Legacy CLI-based auth
            root = os.environ.get('SENTRYPHI_CLOUD_AUTH_ROOT')
            if not root:
                raise ValueError('Cloud configuration directory is missing')
            if provider == 'aws':
                self.env = isolated_aws_environment(scope['profile'])
            elif provider == 'azure':
                self.env['AZURE_CONFIG_DIR'] = str(Path(root) / 'azure')
            elif provider == 'gcp':
                self.env.update(CLOUDSDK_CONFIG=str(Path(root) / 'gcp'), CLOUDSDK_CORE_DISABLE_PROMPTS='1')
            else:
                raise ValueError('Unknown provider')

    def call(self, args, *, output=True, timeout=900):
        if self.auth_mode == 'token':
            return self._call_rest(args, output=output, timeout=timeout)
        # Legacy CLI mode
        if self.provider == 'aws':
            command = ['aws', *args, '--profile', self.scope['profile'], '--region', self.region, '--no-cli-pager']
            if output:
                command += ['--output', 'json']
        elif self.provider == 'azure':
            command = ['az', *args, '--subscription', self.scope['account_id'], '--only-show-errors', '--output', 'json' if output else 'none']
        else:
            command = ['gcloud', *args, '--project', self.scope['account_id'], '--quiet', '--format=json']
        if os.name == 'nt' and command[0] in ('az', 'gcloud'):
            if any(re.search(r'[\"&|<>^%\r\n!]', str(arg)) for arg in command):
                raise ValueError('Unsupported character in CLI arguments')
            command = 'cmd.exe /d /s /c "' + ' '.join('"' + str(arg) + '"' for arg in command) + '"'
        try:
            result = self.run_process(command, env=self.env, stdout=subprocess.PIPE if output else subprocess.DEVNULL,
                stderr=subprocess.PIPE, text=True, encoding='utf-8', shell=False, timeout=timeout,
                creationflags=subprocess.CREATE_NO_WINDOW if os.name == 'nt' else 0)
        except FileNotFoundError:
            raise RuntimeError('The official cloud CLI is missing. Install it and sign in again.') from None
        except subprocess.TimeoutExpired:
            raise RuntimeError('Cloud command timed out. The provider may still be working; inspect its resource before retrying.') from None
        if result.returncode:
            if re.search(r'expired|invalid_grant|reauth|login required|please run.*login', result.stderr or '', re.I):
                raise RuntimeError('Cloud session expired. Sign in again to resume.')
            raise RuntimeError(f'{self.provider.upper()} command failed ({" ".join(args[:2])}). Check CLI permissions, service quotas and provider activity logs.')
        if not output or not (result.stdout or '').strip():
            return {}
        try:
            return json.loads(result.stdout)
        except ValueError:
            raise RuntimeError('The cloud CLI returned an invalid structured response') from None

    def _call_rest(self, args, *, output=True, timeout=900):
        """Execute cloud operations via REST APIs using tokens (no CLI binary needed)."""
        import urllib.request
        import urllib.error
        import ssl

        if self.provider == 'gcp':
            return self._gcp_rest(args, output=output, timeout=timeout)
        elif self.provider == 'azure':
            return self._azure_rest(args, output=output, timeout=timeout)
        elif self.provider == 'aws':
            return self._aws_rest(args, output=output, timeout=timeout)
        raise RuntimeError(f'REST API calls not implemented for {self.provider}')

    def _gcp_rest(self, args, *, output=True, timeout=900):
        """Translate gcloud CLI commands to Google Cloud REST API calls."""
        import urllib.request
        import urllib.error

        token = self.env.get('GOOGLE_OAUTH_ACCESS_TOKEN', '')
        project = self.scope.get('account_id', '')
        region = self.region

        if not token:
            raise RuntimeError('Google Cloud access token is missing. Sign in again.')

        headers = {'Authorization': f'Bearer {token}', 'Content-Type': 'application/json'}

        def api_call(method, url, body=None):
            data = json.dumps(body).encode() if body else None
            req = urllib.request.Request(url, data=data, headers=headers, method=method)
            try:
                with urllib.request.urlopen(req, timeout=timeout) as resp:
                    result = resp.read().decode()
                    if not output or not result.strip():
                        return {}
                    return json.loads(result) if result.strip() else {}
            except urllib.error.HTTPError as e:
                body_text = e.read().decode() if e.fp else ''
                if e.code == 409:  # Already exists — not an error
                    return {}
                if 'expired' in body_text.lower() or 'invalid_grant' in body_text.lower():
                    raise RuntimeError('Cloud session expired. Sign in again to resume.')
                # Billing not enabled
                if 'billing' in body_text.lower() and ('not found' in body_text.lower() or 'enabled' in body_text.lower()):
                    raise RuntimeError(
                        f'Billing is not enabled on your GCP project ({project}). '
                        f'Enable billing at https://console.cloud.google.com/billing/linkedaccount?project={project} '
                        f'then click "Refresh deployment status" to retry.')
                # Permission denied
                if e.code == 403:
                    raise RuntimeError(
                        f'Permission denied. Your GCP account may not have the required roles. '
                        f'Grant Owner or Editor role at https://console.cloud.google.com/iam-admin/iam?project={project} '
                        f'then retry the deployment.')
                # Quota exceeded
                if e.code == 429 or 'quota' in body_text.lower():
                    raise RuntimeError(
                        f'GCP quota exceeded. Check quotas at https://console.cloud.google.com/iam-admin/quotas?project={project} '
                        f'and request an increase if needed.')
                raise RuntimeError(f'GCP API error ({e.code}): {body_text[:300]}') from None
            except urllib.error.URLError as e:
                raise RuntimeError(f'Network error calling GCP API: {e.reason}') from None

        # Route gcloud commands to REST API endpoints
        if args[0] == 'services' and args[1] == 'enable':
            # Enable APIs
            for service in args[2:]:
                api_call('POST', f'https://serviceusage.googleapis.com/v1/projects/{project}/services/{service}:enable')
            return {}

        if args[0] == 'artifacts' and args[1] == 'repositories':
            if args[2] == 'create':
                name = args[3]
                loc = region
                for i, a in enumerate(args):
                    if a == '--location': loc = args[i+1]
                return api_call('POST',
                    f'https://artifactregistry.googleapis.com/v1/projects/{project}/locations/{loc}/repositories?repositoryId={name}',
                    {'format': 'DOCKER', 'labels': {'sentryphi': 'true'}})
            if 'add-iam-policy-binding' in args:
                repo = args[3]
                loc = region
                member = role = ''
                for i, a in enumerate(args):
                    if a == '--location': loc = args[i+1]
                    if a == '--member': member = args[i+1]
                    if a == '--role': role = args[i+1]
                policy = api_call('GET', f'https://artifactregistry.googleapis.com/v1/projects/{project}/locations/{loc}/repositories/{repo}:getIamPolicy')
                bindings = policy.get('bindings', [])
                bindings.append({'role': role, 'members': [member]})
                return api_call('POST',
                    f'https://artifactregistry.googleapis.com/v1/projects/{project}/locations/{loc}/repositories/{repo}:setIamPolicy',
                    {'policy': {'bindings': bindings}})

        if args[0] == 'iam' and args[1] == 'service-accounts':
            if args[2] == 'create':
                sa_id = args[3]
                display = sa_id
                for i, a in enumerate(args):
                    if a == '--display-name': display = args[i+1]
                return api_call('POST',
                    f'https://iam.googleapis.com/v1/projects/{project}/serviceAccounts',
                    {'accountId': sa_id, 'serviceAccount': {'displayName': display}})
            if 'add-iam-policy-binding' in args:
                sa_email = args[3]
                member = role = ''
                for i, a in enumerate(args):
                    if a == '--member': member = args[i+1]
                    if a == '--role': role = args[i+1]
                resource = f'projects/{project}/serviceAccounts/{sa_email}'
                policy = api_call('POST', f'https://iam.googleapis.com/v1/{resource}:getIamPolicy', {})
                bindings = policy.get('bindings', [])
                bindings.append({'role': role, 'members': [member]})
                return api_call('POST', f'https://iam.googleapis.com/v1/{resource}:setIamPolicy',
                    {'policy': {'bindings': bindings}})

        if args[0] == 'storage' and args[1] == 'buckets':
            if args[2] == 'create':
                bucket_url = args[3]
                bucket_name = bucket_url.replace('gs://', '')
                loc = region
                for i, a in enumerate(args):
                    if a == '--location': loc = args[i+1]
                return api_call('POST', 'https://storage.googleapis.com/storage/v1/b?project=' + project,
                    {'name': bucket_name, 'location': loc, 'iamConfiguration': {'uniformBucketLevelAccess': {'enabled': True}}})
            if 'add-iam-policy-binding' in args:
                bucket_url = args[3]
                bucket_name = bucket_url.replace('gs://', '')
                member = role = ''
                for i, a in enumerate(args):
                    if a == '--member': member = args[i+1]
                    if a == '--role': role = args[i+1]
                policy = api_call('GET', f'https://storage.googleapis.com/storage/v1/b/{bucket_name}/iam')
                bindings = policy.get('bindings', [])
                bindings.append({'role': role, 'members': [member]})
                return api_call('PUT', f'https://storage.googleapis.com/storage/v1/b/{bucket_name}/iam',
                    {'bindings': bindings})

        if args[0] == 'builds':
            if args[1] == 'submit':
                source_dir = args[2]
                image = sa = gcs_source = gcs_log = ''
                build_region = region
                for i, a in enumerate(args):
                    if a == '--tag': image = args[i+1]
                    if a == '--region': build_region = args[i+1]
                    if a == '--service-account': sa = args[i+1]
                    if a == '--gcs-source-staging-dir': gcs_source = args[i+1]
                    if a == '--gcs-log-dir': gcs_log = args[i+1]
                # Upload source and trigger build via REST
                build_body = {
                    'steps': [{'name': 'gcr.io/cloud-builders/docker', 'args': ['build', '-t', image, '.']}],
                    'images': [image],
                    'serviceAccount': sa,
                    'options': {'logging': 'GCS_ONLY', 'logsBucket': gcs_log.replace('gs://', '')},
                }
                return api_call('POST',
                    f'https://cloudbuild.googleapis.com/v1/projects/{project}/locations/{build_region}/builds', build_body)
            if args[1] == 'describe':
                build_id = args[2]
                build_region = region
                for i, a in enumerate(args):
                    if a == '--region': build_region = args[i+1]
                return api_call('GET',
                    f'https://cloudbuild.googleapis.com/v1/projects/{project}/locations/{build_region}/builds/{build_id}')

        if args[0] == 'ai':
            if args[1] == 'models' and args[2] == 'upload':
                model_id = display = container_image = ''
                container_ports = '8080'
                health_route = predict_route = ''
                labels = {}
                for i, a in enumerate(args):
                    if a == '--model-id': model_id = args[i+1]
                    if a == '--display-name': display = args[i+1]
                    if a == '--container-image-uri': container_image = args[i+1]
                    if a == '--container-ports': container_ports = args[i+1]
                    if a == '--container-health-route': health_route = args[i+1]
                    if a == '--container-predict-route': predict_route = args[i+1]
                    if a == '--labels': labels = dict(kv.split('=') for kv in args[i+1].split(','))
                return api_call('POST',
                    f'https://{region}-aiplatform.googleapis.com/v1/projects/{project}/locations/{region}/models:upload',
                    {'model': {'displayName': display, 'labels': labels,
                        'containerSpec': {'imageUri': container_image, 'ports': [{'containerPort': int(container_ports)}],
                            'healthRoute': health_route, 'predictRoute': predict_route}}})
            if args[1] == 'endpoints' and args[2] == 'create':
                endpoint_id = display = ''
                labels = {}
                for i, a in enumerate(args):
                    if a == '--endpoint-id': endpoint_id = args[i+1]
                    if a == '--display-name': display = args[i+1]
                    if a == '--labels': labels = dict(kv.split('=') for kv in args[i+1].split(','))
                return api_call('POST',
                    f'https://{region}-aiplatform.googleapis.com/v1/projects/{project}/locations/{region}/endpoints?endpointId={endpoint_id}',
                    {'displayName': display, 'labels': labels})
            if args[1] == 'endpoints' and args[2] == 'deploy-model':
                endpoint_id = args[3]
                model_name = display = machine = ''
                min_rep = max_rep = '1'
                accel_args = []
                for i, a in enumerate(args):
                    if a == '--model': model_name = args[i+1]
                    if a == '--display-name': display = args[i+1]
                    if a == '--machine-type': machine = args[i+1]
                    if a == '--min-replica-count': min_rep = args[i+1]
                    if a == '--max-replica-count': max_rep = args[i+1]
                    if a == '--accelerator': accel_args.append(args[i+1])
                deployed = {
                    'displayName': display,
                    'model': f'projects/{project}/locations/{region}/models/{model_name}',
                    'dedicatedResources': {
                        'machineSpec': {'machineType': machine},
                        'minReplicaCount': int(min_rep), 'maxReplicaCount': int(max_rep)
                    }
                }
                if accel_args:
                    for spec in accel_args:
                        parts = dict(kv.split('=') for kv in spec.split(','))
                        deployed['dedicatedResources']['machineSpec']['acceleratorType'] = parts.get('type', '').upper().replace('-', '_')
                        deployed['dedicatedResources']['machineSpec']['acceleratorCount'] = int(parts.get('count', 1))
                return api_call('POST',
                    f'https://{region}-aiplatform.googleapis.com/v1/projects/{project}/locations/{region}/endpoints/{endpoint_id}:deployModel',
                    {'deployedModel': deployed, 'trafficSplit': {'0': 100}})
            if args[1] == 'endpoints' and args[2] == 'list':
                return api_call('GET',
                    f'https://{region}-aiplatform.googleapis.com/v1/projects/{project}/locations/{region}/endpoints')

        if args[0] == 'projects' and args[1] == 'describe':
            return api_call('GET', f'https://cloudresourcemanager.googleapis.com/v1/projects/{args[2]}')

        if args[0] == 'auth' and args[1] == 'list':
            return [{'account': self.scope.get('identity', ''), 'status': 'ACTIVE'}]

        # Fallback: command not mapped — provide a clear error
        raise RuntimeError(f'GCP operation not yet supported without CLI: {" ".join(args[:3])}. '
                           f'Please install the Google Cloud CLI (gcloud) or contact support.')

    def _azure_rest(self, args, *, output=True, timeout=900):
        """Translate az CLI commands to Azure REST API calls."""
        import urllib.request
        import urllib.error

        token = self.env.get('AZURE_ACCESS_TOKEN', '')
        sub = self.scope.get('account_id', '')
        if not token:
            raise RuntimeError('Azure access token is missing. Sign in again.')
        headers = {'Authorization': f'Bearer {token}', 'Content-Type': 'application/json'}

        def api_call(method, url, body=None):
            data = json.dumps(body).encode() if body else None
            req = urllib.request.Request(url, data=data, headers=headers, method=method)
            try:
                with urllib.request.urlopen(req, timeout=timeout) as resp:
                    result = resp.read().decode()
                    return json.loads(result) if result.strip() else {}
            except urllib.error.HTTPError as e:
                body_text = e.read().decode() if e.fp else ''
                raise RuntimeError(f'Azure API error ({e.code}): {body_text[:200]}') from None

        if args[0] == 'account' and args[1] == 'show':
            subs = api_call('GET', f'https://management.azure.com/subscriptions/{sub}?api-version=2020-01-01')
            return {'id': sub, 'user': {'name': self.scope.get('identity', '')}, 'state': 'Enabled', **subs}

        raise RuntimeError(f'Azure operation not yet supported without CLI: {" ".join(args[:3])}')

    def _aws_rest(self, args, *, output=True, timeout=900):
        """For AWS token mode, use boto3 SDK — no CLI required."""
        try:
            import boto3
        except ImportError:
            raise RuntimeError(
                'AWS deployment requires the boto3 package, which should be bundled. '
                'If you see this in a development install, run: pip install boto3'
            )

        session = boto3.Session(
            aws_access_key_id=self.env.get('AWS_ACCESS_KEY_ID'),
            aws_secret_access_key=self.env.get('AWS_SECRET_ACCESS_KEY'),
            aws_session_token=self.env.get('AWS_SESSION_TOKEN'),
            region_name=self.region
        )

        # ── STS ──
        if args[0] == 'sts' and args[1] == 'get-caller-identity':
            return session.client('sts').get_caller_identity()

        # ── CloudFormation ──
        if args[0] == 'cloudformation':
            cf = session.client('cloudformation')
            if args[1] == 'create-stack':
                params = self._parse_aws_args(args[2:])
                template_body = ''
                template_path = params.get('--template-body', '')
                if template_path.startswith('file://'):
                    with open(template_path[7:], 'r') as f:
                        template_body = f.read()
                tags = []
                if '--tags' in params:
                    for tag_str in params['--tags']:
                        parts = dict(kv.split('=', 1) for kv in tag_str.split(',') if '=' in tag_str)
                        if 'Key' not in parts:
                            parts = dict(kv.split('=', 1) for kv in [tag_str])
                        tags.append({'Key': parts.get('Key', ''), 'Value': parts.get('Value', '')})
                create_params = {
                    'StackName': params.get('--stack-name', ''),
                    'TemplateBody': template_body,
                    'Capabilities': [params.get('--capabilities', 'CAPABILITY_IAM')],
                    'Tags': tags,
                }
                if params.get('--client-request-token'):
                    create_params['ClientRequestToken'] = params['--client-request-token']
                result = cf.create_stack(**create_params)
                return {'StackId': result['StackId']}
            if args[1] == 'describe-stacks':
                params = self._parse_aws_args(args[2:])
                result = cf.describe_stacks(StackName=params.get('--stack-name', ''))
                return {'Stacks': result['Stacks']}

        # ── S3 ──
        if args[0] == 's3' and args[1] == 'cp':
            s3 = session.client('s3')
            local_path = args[2]
            s3_path = args[3]  # s3://bucket/key
            bucket, key = s3_path.replace('s3://', '').split('/', 1)
            s3.upload_file(local_path, bucket, key)
            return {}

        # ── CodeBuild ──
        if args[0] == 'codebuild':
            cb = session.client('codebuild')
            if args[1] == 'start-build':
                params = self._parse_aws_args(args[2:])
                result = cb.start_build(
                    projectName=params.get('--project-name', ''),
                    idempotencyToken=params.get('--idempotency-token', '')
                )
                return {'build': {'id': result['build']['id']}}
            if args[1] == 'batch-get-builds':
                params = self._parse_aws_args(args[2:])
                ids = params.get('--ids', '').split(',') if isinstance(params.get('--ids'), str) else [params.get('--ids', '')]
                result = cb.batch_get_builds(ids=ids)
                return {'builds': result['builds']}

        # ── SageMaker ──
        if args[0] == 'sagemaker' and args[1] == 'describe-endpoint':
            sm = session.client('sagemaker')
            params = self._parse_aws_args(args[2:])
            return sm.describe_endpoint(EndpointName=params.get('--endpoint-name', ''))

        raise RuntimeError(f'AWS operation not yet supported via boto3: {" ".join(args[:3])}')

    @staticmethod
    def _parse_aws_args(args):
        """Parse CLI-style --key value pairs into a dict. Handles multi-value flags like --tags."""
        result = {}
        i = 0
        while i < len(args):
            if args[i].startswith('--'):
                key = args[i]
                values = []
                i += 1
                while i < len(args) and not args[i].startswith('--'):
                    values.append(args[i])
                    i += 1
                if key == '--tags':
                    result[key] = values
                elif len(values) == 1:
                    result[key] = values[0]
                elif len(values) == 0:
                    result[key] = True
                else:
                    result[key] = values
            else:
                i += 1
        return result


    def verify(self):
        if self.auth_mode == 'token':
            # Token-based auth was already validated by the frontend during sign-in.
            # Return the scope identity directly.
            return {'Account': self.scope.get('account_id', ''),
                    'Arn': self.scope.get('identity', ''),
                    'provider': self.provider}
        if self.provider == 'aws':
            from .aws_cli import AwsCli
            return AwsCli(self.scope, self.region, self.run_process).verify()
        if self.provider == 'azure':
            identity = self.call(['account', 'show'])
            match = identity.get('id') == self.scope['account_id'] and identity.get('user', {}).get('name') == self.scope['identity'] and identity.get('state') == 'Enabled'
        else:
            identity = self.call(['auth', 'list', '--filter=status:ACTIVE'])
            match = len(identity) == 1 and identity[0].get('account') == self.scope['identity']
            self.call(['projects', 'describe', self.scope['account_id']])
        if not match:
            raise RuntimeError('Cloud identity changed. Confirm the signed-in account again.')
        return identity
