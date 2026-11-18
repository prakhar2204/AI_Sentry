"""Offline AWS authentication/deployment boundary tests. No real CLI or account."""
import json
from pathlib import Path
from types import SimpleNamespace
from unittest.mock import Mock

import pytest

from core.deploy.aws_cli import AwsCli, AwsCliError, isolated_aws_environment
from core.deploy.aws_engine import AwsDeployEngine
from core.deploy.aws_templates import build_template
from core.deploy.base import DeployStatus
from core.deploy.state_store import DeploymentStore


SCOPE = {'auth_mode': 'cli', 'profile': 'sentryphi-console', 'account_id': '123456789012',
         'identity': 'arn:aws:iam::123456789012:user/test', 'region': 'us-east-1'}
CONFIG = {'region': 'us-east-1', 'deployment_mode': 'bedrock', 'endpoint_scope': 'public',
          'model_id': 'test.model-v1', 'execution_role_arn': 'arn:aws:iam::123456789012:role/Inference'}


@pytest.fixture
def engine(tmp_path):
    cli = Mock()
    cli.call.return_value = {}
    instance = AwsDeployEngine(DeploymentStore(tmp_path), lambda scope, region: cli)
    instance.test_cli = cli
    return instance


def stack(plan, status='CREATE_COMPLETE', **changes):
    result = {'StackId': f'arn:aws:cloudformation:us-east-1:123456789012:stack/{plan.deployment_id}/uuid',
              'StackName': plan.deployment_id, 'StackStatus': status,
              'Tags': [{'Key': 'SentryPhi', 'Value': 'true'}, {'Key': 'DeploymentId', 'Value': plan.deployment_id}],
              'Outputs': [{'OutputKey': 'EndpointUrl', 'OutputValue': 'https://example.execute-api.us-east-1.amazonaws.com/invoke'}]}
    result.update(changes)
    return {'Stacks': [result]}


def test_bedrock_plan_is_real_gateway_with_enforced_guardrail(engine):
    plan = engine.generate_plan(CONFIG, SCOPE, {})
    template = build_template(CONFIG, plan.deployment_id, SCOPE['account_id'])
    resources = template['Resources']
    assert resources['Route']['Properties']['AuthorizationType'] == 'AWS_IAM'
    assert resources['Route']['Properties']['RouteKey'] == 'POST /invoke'
    assert resources['GuardrailVersion']['Type'] == 'AWS::Bedrock::GuardrailVersion'
    assert 'guardrailConfig=' in resources['Function']['Properties']['Code']['ZipFile']
    assert len(plan.resources) == len(resources)
    assert plan.estimated_cost['basis'] == 'not_estimated'
    assert engine.test_cli.mock_calls == []  # Local planning never signs in or calls AWS.


def test_sagemaker_and_lambda_require_actual_artifacts():
    config = {**CONFIG, 'deployment_mode': 'sagemaker', 'instance_type': 'ml.g4dn.xlarge',
              'container_image': '123456789012.dkr.ecr.us-east-1.amazonaws.com/inference:v1',
              'model_data_url': 's3://models-bucket/model.tar.gz'}
    resources = build_template(config, 'sp-test', SCOPE['account_id'])['Resources']
    assert resources['Model']['Properties']['PrimaryContainer']['ModelDataUrl'] == config['model_data_url']
    assert 'EndpointConfig' in resources and 'Endpoint' in resources
    config['deployment_mode'] = 'lambda'
    resources = build_template(config, 'sp-test', SCOPE['account_id'])['Resources']
    assert resources['Function']['Properties']['Code'] == {'ImageUri': config['container_image']}
    assert 'ZipFile' not in resources['Function']['Properties']['Code']
    del config['container_image']
    with pytest.raises(ValueError, match='ECR'):
        build_template(config, 'sp-test', SCOPE['account_id'])


@pytest.mark.parametrize('patch', [{'endpoint_scope': 'private'}, {'execution_role_arn': 'arn:aws:iam::999999999999:role/Other'}, {'model_id': ''}])
def test_invalid_or_unimplemented_plans_fail_before_cloud_calls(engine, patch):
    with pytest.raises(ValueError):
        engine.generate_plan({**CONFIG, **patch}, SCOPE, {})
    assert engine.test_cli.mock_calls == []


def test_confirmation_identity_and_template_validation(engine):
    plan = engine.generate_plan(CONFIG, SCOPE, {})
    with pytest.raises(RuntimeError, match='confirmation'):
        engine.deploy(plan, SCOPE)
    assert engine.test_cli.mock_calls == []
    assert engine.dry_run(plan, SCOPE).success
    assert engine.test_cli.mock_calls[0][0] == 'verify'
    assert engine.test_cli.call.call_args.args[:2] == ('cloudformation', 'validate-template')
    engine.test_cli.reset_mock()
    result = engine.deploy(plan, SCOPE, confirmed=True)
    assert result.status == DeployStatus.RUNNING
    assert engine.test_cli.mock_calls[0][0] == 'verify'
    assert engine.store.load(plan.deployment_id)['status'] == 'running'
    engine.test_cli.call.return_value = stack(plan)
    assert engine.deploy(plan, SCOPE, confirmed=True).status == DeployStatus.COMPLETE
    assert sum(c.args[:2] == ('cloudformation', 'create-stack') for c in engine.test_cli.call.call_args_list) == 1


@pytest.mark.parametrize('aws_status,expected', [('CREATE_IN_PROGRESS', 'running'), ('CREATE_COMPLETE', 'complete'),
    ('ROLLBACK_COMPLETE', 'failed'), ('CREATE_FAILED', 'failed'), ('DELETE_IN_PROGRESS', 'running'), ('DELETE_COMPLETE', 'rolled_back')])
def test_actual_stack_readiness_not_tag_presence(engine, aws_status, expected):
    plan = engine.generate_plan(CONFIG, SCOPE, {})
    engine.deploy(plan, SCOPE, True)
    engine.test_cli.call.return_value = stack(plan, aws_status)
    result = engine.get_deployment_status(plan.deployment_id, SCOPE)
    assert result.status.value == expected
    assert bool(result.endpoint_url) == (expected == 'complete')


def test_missing_output_cannot_report_success(engine):
    plan = engine.generate_plan(CONFIG, SCOPE, {})
    engine.deploy(plan, SCOPE, True)
    engine.test_cli.call.return_value = stack(plan, Outputs=[])
    assert engine.get_deployment_status(plan.deployment_id, SCOPE).status == DeployStatus.FAILED


def test_timeout_preserves_intent_and_reconciles_without_duplicate_creation(engine):
    plan = engine.generate_plan(CONFIG, SCOPE, {})
    engine.test_cli.call.side_effect = AwsCliError('TIMEOUT', 'Timed out')
    assert engine.deploy(plan, SCOPE, True).status == DeployStatus.UNKNOWN
    assert engine.store.load(plan.deployment_id)['status'] == 'pending'
    engine.test_cli.call.side_effect = None
    engine.test_cli.call.return_value = stack(plan, 'CREATE_IN_PROGRESS')
    assert engine.deploy(plan, SCOPE, True).status == DeployStatus.RUNNING
    assert sum(c.args[:2] == ('cloudformation', 'create-stack') for c in engine.test_cli.call.call_args_list) == 1


@pytest.mark.parametrize('changes', [{'Tags': []}, {'StackName': 'unrelated'},
    {'StackId': 'arn:aws:cloudformation:us-west-2:999999999999:stack/unrelated/uuid'}])
def test_rollback_rejects_resources_outside_owned_stack(engine, changes):
    plan = engine.generate_plan(CONFIG, SCOPE, {})
    engine.deploy(plan, SCOPE, True)
    engine.test_cli.reset_mock()
    engine.test_cli.call.return_value = stack(plan, **changes)
    with pytest.raises(ValueError, match='ownership'):
        engine.rollback(plan.deployment_id, SCOPE)
    assert not any(c.args[1] == 'delete-stack' for c in engine.test_cli.call.call_args_list)


def test_rollback_uses_exact_arn_and_does_not_claim_deletion_complete(engine):
    plan = engine.generate_plan(CONFIG, SCOPE, {})
    engine.deploy(plan, SCOPE, True)
    engine.test_cli.call.return_value = stack(plan)
    result = engine.rollback(plan.deployment_id, SCOPE)
    assert result.success and result.deleted == []
    assert engine.test_cli.call.call_args.args[2]['StackName'] == stack(plan)['Stacks'][0]['StackId']
    assert engine.store.load(plan.deployment_id)['status'] == 'deleting'
    with pytest.raises(ValueError, match='different AWS account'):
        engine.get_deployment_status(plan.deployment_id, {**SCOPE, 'account_id': '999999999999'})
    engine.test_cli.call.return_value = stack(plan, 'DELETE_IN_PROGRESS')
    assert engine.get_deployment_status(plan.deployment_id, SCOPE).status == DeployStatus.RUNNING
    engine.test_cli.call.side_effect = AwsCliError('NOT_FOUND', 'Stack gone')
    assert engine.get_deployment_status(plan.deployment_id, SCOPE).status == DeployStatus.ROLLED_BACK
    assert engine.get_deployment_status(plan.deployment_id, SCOPE).status == DeployStatus.ROLLED_BACK


def test_cli_subprocess_uses_same_isolated_environment_and_no_shell(tmp_path, monkeypatch):
    monkeypatch.setenv('SENTRYPHI_CLOUD_AUTH_ROOT', str(tmp_path))
    monkeypatch.setenv('AWS_ACCESS_KEY_ID', 'TOKEN_SENTINEL')
    calls = []
    def run(args, **kwargs):
        calls.append((args, kwargs))
        assert kwargs['shell'] is False
        assert kwargs['env'].get('AWS_ACCESS_KEY_ID') is None
        if '--version' in args:
            return SimpleNamespace(returncode=0, stdout='aws-cli/2.32.0', stderr='')
        if 'get-caller-identity' in args:
            return SimpleNamespace(returncode=0, stdout=json.dumps({'Account': SCOPE['account_id'], 'Arn': SCOPE['identity']}), stderr='')
        file = Path(args[-1].removeprefix('file://'))
        assert json.loads(file.read_text()) == {'StackName': 'sp-test'}
        return SimpleNamespace(returncode=0, stdout='{}', stderr='')
    cli = AwsCli(SCOPE, 'us-east-1', run)
    cli.verify()
    cli.call('cloudformation', 'describe-stacks', {'StackName': 'sp-test'})
    assert not Path(calls[-1][0][-1].removeprefix('file://')).exists()
    assert cli.env['AWS_PROFILE'] == 'sentryphi-console'
    assert cli.env['AWS_CONFIG_FILE'] == str(tmp_path / 'aws' / 'config')
    with pytest.raises(ValueError):
        isolated_aws_environment('default')


def test_cli_errors_never_expose_stderr_tokens(tmp_path, monkeypatch):
    monkeypatch.setenv('SENTRYPHI_CLOUD_AUTH_ROOT', str(tmp_path))
    run = Mock(return_value=SimpleNamespace(returncode=1, stdout='', stderr='ExpiredToken TOKEN_SENTINEL'))
    with pytest.raises(AwsCliError) as exc:
        AwsCli(SCOPE, 'us-east-1', run).verify()
    assert exc.value.code == 'EXPIRED_SESSION'
    assert 'TOKEN_SENTINEL' not in str(exc.value)


def test_journal_rejects_credentials_and_path_traversal(tmp_path):
    store = DeploymentStore(tmp_path)
    with pytest.raises(ValueError):
        store.save({'deployment_id': 'sp-test', 'nested': {'access_token': 'TOKEN_SENTINEL'}})
    with pytest.raises(ValueError):
        store.load('../outside')
    assert list(tmp_path.iterdir()) == []


def test_gateway_enforces_server_guardrail_and_rejects_selective_bypass(monkeypatch):
    import sys
    from core.deploy.aws_templates import BEDROCK_HANDLER
    client = Mock()
    client.converse.return_value = {'output': {'message': {'content': [{'text': 'ok'}]}}, 'stopReason': 'end_turn'}
    monkeypatch.setitem(sys.modules, 'boto3', SimpleNamespace(client=lambda service: client))
    for key, value in {'MODEL_ID': 'configured-model', 'GUARDRAIL_ID': 'guardrail', 'GUARDRAIL_VERSION': '1'}.items():
        monkeypatch.setenv(key, value)
    namespace = {}
    exec(compile(BEDROCK_HANDLER, '<generated-lambda-handler>', 'exec'), namespace)
    body = {'messages': [{'role': 'user', 'content': [{'text': 'hello'}]}], 'modelId': 'untrusted-model'}
    assert namespace['handler']({'body': json.dumps(body)}, None)['statusCode'] == 200
    assert client.converse.call_args.kwargs['modelId'] == 'configured-model'
    assert client.converse.call_args.kwargs['guardrailConfig'] == {'guardrailIdentifier': 'guardrail', 'guardrailVersion': '1'}
    client.reset_mock()
    body['messages'][0]['content'].append({'guardContent': {'text': {'text': 'selectively scanned'}}})
    assert namespace['handler']({'body': json.dumps(body)}, None)['statusCode'] == 400
    client.converse.assert_not_called()


def test_legacy_custom_oauth_entrypoints_are_disabled():
    from core.deploy.azure_engine import AzureDeployEngine
    from core.deploy.gcp_engine import GcpDeployEngine
    for engine in (AwsDeployEngine(), AzureDeployEngine(), GcpDeployEngine()):
        with pytest.raises(RuntimeError, match='CLI'):
            engine.get_auth_url()
        with pytest.raises(RuntimeError, match='CLI'):
            engine.exchange_auth_code('never-process-this', 'state')
