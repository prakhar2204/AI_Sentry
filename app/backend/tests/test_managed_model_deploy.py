"""Offline tests: real local packaging; all provider mutations are mocked."""
import json
import struct
from types import SimpleNamespace
from unittest.mock import Mock

import pytest

from core.model_profile import inspect_model, capacity_check, artifact_digest, GIB
from core.deploy.model_recommender import recommendations
from core.deploy.model_package import package_model
from core.deploy.managed_cli import ManagedCli
from core.deploy.managed_engine import ManagedModelEngine
from core.deploy.state_store import DeploymentStore


@pytest.fixture
def model(tmp_path):
    path = tmp_path / 'tiny.gguf'
    path.write_bytes(b'GGUF' + struct.pack('<IQQ', 3, 1, 0) + b'weights')
    return path


def setup_engine(tmp_path, model, provider='aws'):
    cli = Mock()
    cli.scope = {'identity': 'user@example.test'}
    engine = ManagedModelEngine(provider, DeploymentStore(tmp_path / 'journal'), lambda *a: cli)
    offer = next(o for o in recommendations(str(model))['offers'] if o['provider'] == provider)
    scope = {'auth_mode': 'cli', 'account_id': '123456789012', 'identity': 'user@example.test',
             'profile': 'sentryphi-console', 'region': offer['config']['region']}
    report = {'model_profile': inspect_model(str(model))}
    report['model_profile']['content_sha256'] = artifact_digest(report['model_profile'])
    plan = engine.generate_plan(offer['config'], scope, report)
    return engine, cli, plan, scope


def test_inspection_quotes_editing_and_memory_gate(model):
    profile = inspect_model(str(model))
    assert profile['format'] == 'gguf'
    assert not capacity_check(profile, GIB, 0)['allowed']
    assert capacity_check(profile, 32 * GIB, 0)['allowed']
    original = recommendations(str(model))
    edited = recommendations(str(model), {'aws': {'replicas': 3, 'hours_per_month': 100}})
    assert edited['offers'][0]['estimate']['monthly_usd'] == round(.23 * 300, 2)
    assert edited['offers'][0]['estimate']['monthly_usd'] != original['offers'][0]['estimate']['monthly_usd']
    with pytest.raises(ValueError, match='reference regions'):
        recommendations(str(model), {'aws': {'region': 'us-west-2'}})
    with pytest.raises(ValueError):
        recommendations(str(model), {'private': {'power_watts': float('nan')}})


def test_packaging_uses_scanned_model_and_rejects_replacement(model, tmp_path):
    config = recommendations(str(model))['offers'][0]['config']
    output = package_model(config, tmp_path / 'build')
    assert (output / 'model/model.gguf').read_bytes() == model.read_bytes()
    assert 'llama.cpp:server' in (output / 'Dockerfile').read_text()
    model.write_bytes(model.read_bytes() + b'changed')
    with pytest.raises(ValueError, match='changed'):
        package_model(config, tmp_path / 'different')


def test_hf_package_never_includes_unrelated_json_or_credentials(tmp_path):
    root = tmp_path / 'hf'
    root.mkdir()
    for name, value in [('config.json', {'model_type': 'gpt2'}), ('tokenizer.json', {}),
                        ('credentials.json', {'test': 'SENTINEL'})]:
        (root / name).write_text(json.dumps(value))
    (root / 'model.safetensors').write_bytes(b'fake-test-weights')
    offer = recommendations(str(root))['offers'][0]
    package = package_model(offer['config'], tmp_path / 'build')
    assert not (package / 'model/credentials.json').exists()
    assert (package / 'model/config.json').exists()
    gpu = recommendations(str(root), {'aws': {'instance_type': 'ml.g4dn.xlarge'}})['offers'][0]
    assert not gpu['fits']


def test_review_confirmation_identity_and_plan_integrity(tmp_path, model):
    engine, cli, plan, scope = setup_engine(tmp_path, model)
    assert cli.mock_calls == []
    with pytest.raises(RuntimeError, match='confirmation'):
        engine.deploy(plan, scope)
    assert cli.mock_calls == []
    assert engine.dry_run(plan, scope).success
    cli.verify.assert_called_once()
    plan.raw_config['replicas'] = 4
    with pytest.raises(ValueError, match='changed'):
        engine.deploy(plan, scope, True)
    with pytest.raises(ValueError, match='different account'):
        engine.get_deployment_status(plan.deployment_id, {**scope, 'account_id': 'other'})


def test_failed_background_build_never_becomes_complete(tmp_path, model, monkeypatch):
    engine, cli, plan, scope = setup_engine(tmp_path, model)
    monkeypatch.setattr(engine, '_aws', Mock(side_effect=RuntimeError('Build failed')))
    result = engine.deploy(plan, scope, True)
    assert result.status.value == 'running'
    engine.jobs[plan.deployment_id].join(10)
    assert engine.get_deployment_status(plan.deployment_id, scope).status.value == 'failed'
    assert engine.deploy(plan, scope, True).status.value == 'failed'
    engine._aws.assert_called_once()
    assert cli.verify.call_count == 2  # Before job, again after packaging.


def test_restart_does_not_duplicate_provisioning(tmp_path, model):
    engine, cli, plan, scope = setup_engine(tmp_path, model)
    record = engine.store.load(plan.deployment_id)
    record['status'] = 'running'
    engine.store.save(record)
    status = engine.get_deployment_status(plan.deployment_id, scope)
    assert status.status.value == 'failed'
    assert 'interrupted' in status.errors[0]
    assert not cli.mock_calls


def test_aws_upload_build_and_endpoint_health_protocol(tmp_path, model):
    engine, cli, plan, scope = setup_engine(tmp_path, model)
    def call(args, **kwargs):
        if args[:2] == ['cloudformation', 'create-stack']:
            return {'StackId': args[3]}
        if args[:2] == ['cloudformation', 'describe-stacks']:
            return {'Stacks': [{'StackStatus': 'CREATE_COMPLETE', 'Outputs': [
                {'OutputKey': key, 'OutputValue': value} for key, value in
                {'Bucket': 'test-private', 'Image': 'test-image', 'Role': 'test-role', 'BuildProject': 'test-build'}.items()]}]}
        if args[:2] == ['codebuild', 'start-build']:
            return {'build': {'id': 'build-123'}}
        if args[:2] == ['codebuild', 'batch-get-builds']:
            return {'builds': [{'buildStatus': 'SUCCEEDED'}]}
        if args[:2] == ['sagemaker', 'describe-endpoint']:
            return {'EndpointStatus': 'InService'}
        return {}
    cli.call.side_effect = call
    engine.deploy(plan, scope, True)
    engine.jobs[plan.deployment_id].join(10)
    result = engine.get_deployment_status(plan.deployment_id, scope)
    assert result.status.value == 'complete', result.errors
    assert result.endpoint_url.endswith('/invocations')
    calls = [c.args[0] for c in cli.call.call_args_list]
    assert any(c[:2] == ['s3', 'cp'] for c in calls)
    assert any(c[:2] == ['codebuild', 'start-build'] for c in calls)
    assert calls[-1][:2] == ['sagemaker', 'describe-endpoint']


@pytest.mark.parametrize('provider', ['azure', 'gcp'])
def test_provider_drivers_wait_for_real_readiness(tmp_path, model, provider):
    engine, cli, plan, scope = setup_engine(tmp_path, model, provider)
    def call(args, **kwargs):
        if args[:2] == ['acr', 'create']:
            return {'id': '/registry/test', 'loginServer': 'test.azurecr.io'}
        if args[:3] == ['ml', 'online-endpoint', 'create']:
            return {'identity': {'principal_id': 'principal'}}
        if args[:3] == ['ml', 'online-deployment', 'show']:
            return {'provisioning_state': 'Succeeded'}
        if args[:3] == ['ml', 'online-endpoint', 'show']:
            return {'scoring_uri': 'https://test.inference.ml.azure.com/score'}
        if args[:3] == ['ai', 'endpoints', 'describe']:
            return {'deployedModels': [{'id': '1'}], 'trafficSplit': {'1': 100}}
        if args[:2] == ['builds', 'submit']:
            return {'id': 'test-build'}
        if args[:2] == ['builds', 'describe']:
            return {'status': 'SUCCESS'}
        return {}
    cli.call.side_effect = call
    engine.deploy(plan, scope, True)
    engine.jobs[plan.deployment_id].join(10)
    result = engine.get_deployment_status(plan.deployment_id, scope)
    assert result.status.value == 'complete', result.errors
    calls = [c.args[0] for c in cli.call.call_args_list]
    assert not any('get-credentials' in c or 'print-access-token' in c for c in calls)
    if provider == 'azure':
        endpoint = json.loads((engine.store.directory / (plan.deployment_id + '-build') / 'endpoint.json').read_text())
        assert endpoint['auth_mode'] == 'aad_token'
    else:
        assert any(c[:2] == ['builds', 'submit'] for c in calls)


@pytest.mark.parametrize('provider', ['aws', 'azure', 'gcp'])
def test_removal_requires_provider_ownership_tags(tmp_path, model, provider):
    engine, cli, plan, scope = setup_engine(tmp_path, model, provider)
    record = engine.store.load(plan.deployment_id)
    record.update(status='failed', owned={ {'aws': '-build', 'azure': 'resource_group', 'gcp': 'repository'}[provider]: 'foreign'})
    engine.store.save(record)
    cli.call.return_value = {'Stacks': [{'Tags': []}]}
    result = engine.rollback(plan.deployment_id, scope)
    assert not result.success
    assert 'ownership' in result.errors[0]
    assert len(cli.call.call_args_list) == 1


def test_transport_hides_raw_provider_errors_and_isolates_env(monkeypatch, tmp_path):
    monkeypatch.setenv('SENTRYPHI_CLOUD_AUTH_ROOT', str(tmp_path))
    monkeypatch.setenv('AZURE_CLIENT_SECRET', 'SENTINEL')
    run = Mock(return_value=SimpleNamespace(returncode=1, stderr='failure SENTINEL', stdout=''))
    cli = ManagedCli('azure', {'auth_mode': 'cli', 'account_id': 'subscription'}, 'eastus', run)
    with pytest.raises(RuntimeError) as error:
        cli.call(['account', 'show'])
    assert 'SENTINEL' not in str(error.value)
    assert 'AZURE_CLIENT_SECRET' not in run.call_args.kwargs['env']
    assert run.call_args.kwargs['env']['AZURE_CONFIG_DIR'] == str(tmp_path / 'azure')
    assert run.call_args.kwargs['shell'] is False
