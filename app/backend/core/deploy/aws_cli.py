"""AWS CLI transport. The official CLI alone owns and reads its credentials."""
from __future__ import annotations

import json
import os
from pathlib import Path
import re
import subprocess
import tempfile


class AwsCliError(RuntimeError):
    def __init__(self, code, message):
        super().__init__(message)
        self.code = code


def isolated_aws_environment(profile: str) -> dict[str, str]:
    if profile not in ('sentryphi-console', 'sentryphi-sso'):
        raise ValueError('Select an app-managed AWS profile')
    root = os.environ.get('SENTRYPHI_CLOUD_AUTH_ROOT')
    if not root:
        raise ValueError('Cloud configuration directory is missing; use the desktop sign-in flow')
    env = dict(os.environ)
    for key in list(env):
        if re.match(r'^AWS_(ACCESS_KEY|SECRET|SESSION_TOKEN|SECURITY_TOKEN|ROLE_ARN|WEB_IDENTITY|CONTAINER_CREDENTIALS|ENDPOINT_URL|PROFILE|DEFAULT_PROFILE|CONFIG_FILE|SHARED_CREDENTIALS_FILE|LOGIN_CACHE)', key, re.I):
            del env[key]
    directory = Path(root) / 'aws'
    env.update(HOME=str(directory / 'home'), USERPROFILE=str(directory / 'home'),
               AWS_CONFIG_FILE=str(directory / 'config'),
               AWS_SHARED_CREDENTIALS_FILE=str(directory / 'credentials'),
               AWS_LOGIN_CACHE_DIRECTORY=str(directory / 'login-cache'),
               AWS_PROFILE=profile, AWS_DEFAULT_PROFILE=profile, AWS_PAGER='',
               AWS_CLI_AUTO_PROMPT='off', AWS_EC2_METADATA_DISABLED='true')
    return env


class AwsCli:
    ALLOWED = {('sts', 'get-caller-identity'), ('cloudformation', 'validate-template'),
               ('cloudformation', 'create-stack'), ('cloudformation', 'describe-stacks'),
               ('cloudformation', 'list-stack-resources'), ('cloudformation', 'delete-stack')}

    def __init__(self, scope: dict[str, str], region: str, run=None):
        if scope.get('auth_mode') != 'cli':
            raise ValueError('Sign in using the official AWS CLI first')
        if not re.fullmatch(r'[a-z]{2}(?:-[a-z]+)+-\d+', region or ''):
            raise ValueError('Invalid AWS region')
        self.scope, self.region = scope, region
        self.env = isolated_aws_environment(scope.get('profile', ''))
        self.run = run or subprocess.run

    def _invoke(self, args):
        try:
            result = self.run(['aws', *args], env=self.env, capture_output=True, text=True,
                              encoding='utf-8', timeout=60, shell=False,
                              creationflags=subprocess.CREATE_NO_WINDOW if os.name == 'nt' else 0)
        except FileNotFoundError:
            raise AwsCliError('CLI_MISSING', 'Install AWS CLI 2.32.0 or later and restart the app') from None
        except subprocess.TimeoutExpired:
            raise AwsCliError('TIMEOUT', 'AWS CLI timed out. Refresh deployment status before retrying.') from None
        if result.returncode:
            error = result.stderr or ''
            if re.search(r'ExpiredToken|expired|InvalidClientTokenId', error, re.I):
                raise AwsCliError('EXPIRED_SESSION', 'AWS session expired; sign in again')
            if 'does not exist' in error and 'Stack' in error:
                raise AwsCliError('NOT_FOUND', 'Deployment stack not found')
            if 'AlreadyExistsException' in error:
                raise AwsCliError('ALREADY_EXISTS', 'A stack with this name already exists; refresh status')
            raise AwsCliError('AWS_FAILED', 'AWS rejected the request. Check permissions, resource inputs and regional quotas in the AWS console.')
        return result.stdout

    def verify(self):
        version = re.search(r'aws-cli/(\d+)\.(\d+)\.(\d+)', self._invoke(['--version']))
        if not version or tuple(map(int, version.groups())) < (2, 32, 0):
            raise AwsCliError('CLI_OLD', 'Upgrade to AWS CLI 2.32.0 or later')
        identity = self.call('sts', 'get-caller-identity')
        if identity.get('Account') != self.scope.get('account_id') or identity.get('Arn') != self.scope.get('identity'):
            raise AwsCliError('IDENTITY_CHANGED', 'AWS identity changed; confirm the signed-in account again')
        if not re.fullmatch(r'\d{12}', identity.get('Account', '')):
            raise AwsCliError('INVALID_IDENTITY', 'AWS did not return a valid account')
        return identity

    def call(self, service, operation, payload=None):
        if (service, operation) not in self.ALLOWED:
            raise ValueError('Unsupported AWS operation')
        args = [service, operation, '--profile', self.scope['profile'], '--region', self.region,
                '--output', 'json', '--no-cli-pager']
        filename = None
        try:
            if payload:
                # These are resource specifications, never credential files.
                fd, filename = tempfile.mkstemp(prefix='sentryphi-request-', suffix='.json')
                with os.fdopen(fd, 'w', encoding='utf-8') as stream:
                    json.dump(payload, stream)
                args += ['--cli-input-json', 'file://' + filename]
            output = self._invoke(args)
            try:
                return json.loads(output) if output.strip() else {}
            except ValueError:
                raise AwsCliError('INVALID_RESPONSE', 'AWS CLI returned an invalid response') from None
        finally:
            if filename:
                Path(filename).unlink(missing_ok=True)
