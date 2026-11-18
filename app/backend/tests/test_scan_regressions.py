"""Regressions for the desktop scan and backend command repair."""
import unittest
import json
import tempfile
from pathlib import Path
from unittest.mock import patch
from core.engine_runner import _select_engine
from core.adapters.garak_adapter import GarakAdapter
from ipc_server import run_scan_pipeline
from core.manifest import create_manifest
from types import SimpleNamespace


class ScanRegressions(unittest.TestCase):
    def test_gcp_rollback_does_not_touch_another_deployment(self):
        from core.deploy.gcp_engine import GcpDeployEngine
        assets = [{'name': name, 'resource': {'data': {'labels': {
            'sentryphi': 'true', 'deployment-id': deployment}}}} for name, deployment in
            [('owned-resource', 'sp-current'), ('unrelated-resource', 'sp-other')]]
        with patch('core.deploy.gcp_engine._gcp_request', side_effect=[{'assets': assets}, {}]) as request:
            result = GcpDeployEngine().rollback('sp-current', {'gcp_project_id': 'test', 'gcp_access_token': 'test'})
        self.assertEqual(result.deleted, ['owned-resource'])
        self.assertEqual(request.call_count, 2)

    def test_local_file_target_starts_model_even_without_separate_path(self):
        from core.engine_interface import ScanResult
        with patch('ipc_server._emit') as emit, patch('core.local_model_server.detect_gpu', return_value={'available': False}), patch(
            'core.local_model_server.start_local_model', return_value='http://127.0.0.1:11500/v1/chat/completions'
        ) as start, patch('core.local_model_server.get_or_create_server') as server, patch(
            'core.engine_runner.run_engine', return_value=ScanResult(findings=[], engine_name='garak', manifest_id='test', total_probes=1)
        ) as run:
            run_scan_pipeline({'target': 'F:\\models\\dolphin-phi.gguf', 'mode': 'local', 'categories': ['prompt_injection']})
            self.assertTrue(start.call_args.kwargs['model_path'].endswith('dolphin-phi.gguf'))
            self.assertEqual(run.call_args.args[0].target, 'http://127.0.0.1:11500/v1/chat/completions')
            server.return_value.stop.assert_called_once()
            self.assertEqual(sum(c.args[0]['type'] == 'complete' for c in emit.call_args_list), 1)

    def test_direct_garak_file_target_is_rejected(self):
        from core.garak_engine import GarakEngine
        with self.assertRaisesRegex(ValueError, 'HTTP inference endpoint'):
            GarakEngine('F:\\models\\dolphin-phi.gguf', Path('.'))

    def test_garak_config_quotes_model_and_key_safely(self):
        from core.garak_engine import GarakEngine
        with tempfile.TemporaryDirectory() as directory:
            engine = GarakEngine('http://localhost:8000/v1/chat/completions', Path(directory),
                                 api_key='test: #value', model_name='org/model: #revision')
            config = json.loads(engine._write_rest_config('test').read_text())
            generator = config['plugins']['generators']['rest']['RestGenerator']
            self.assertEqual(generator['headers']['Authorization'], 'Bearer $KEY')
            self.assertNotIn('test: #value', json.dumps(config))
            self.assertEqual(generator['req_template_json_object']['model'], 'org/model: #revision')

    def test_deploy_plan_preserves_settings(self):
        from core.deploy.base import DeployPlan
        from ipc_server import _dict_to_plan
        plan = DeployPlan(provider='private', raw_config={'stack': 'kubernetes', 'domain': 'test.local'})
        self.assertEqual(_dict_to_plan(plan.to_dict()).raw_config, plan.raw_config)

    def test_recommendations_read_real_report_summary_and_category_names(self):
        from core.deploy.recommendation_engine import generate_deployment_recommendation
        rec = generate_deployment_recommendation({'summary': {'risk_score': 90},
            'findings': [{'category': 'data_leak', 'severity': 'high'}]})
        self.assertEqual(rec.risk_score, 90)
        self.assertEqual(rec.risk_level, 'high')
        self.assertTrue(any('PII' in control for control in rec.required_controls))

    def test_real_adapter_maps_categories_and_does_not_report_passing_probes(self):
        manifest = create_manifest(target='http://localhost:11500', mode='local',
                                   scan_depth='quick', categories=['data_leak', 'harmful_output'])
        passing = SimpleNamespace(category='data_leakage', severity=1, confidence=0.5,
                                  pass_rate=1.0, total=2, failed=0, probe='test', detector='test')
        with patch.object(GarakAdapter, 'is_available', return_value=True), patch(
            'core.garak_engine.GarakEngine'
        ) as engine:
            engine.return_value.run.return_value = SimpleNamespace(
                findings=[passing], probe_results=[object(), object()], errors=[])
            result = GarakAdapter().run_scan(manifest)
            self.assertIsNone(result.error)
            self.assertEqual(result.findings, [])
            self.assertEqual(result.total_probes, 2)
            self.assertEqual(engine.return_value.run.call_args.kwargs['categories'],
                             ['data_leakage', 'toxicity'])

    def test_auto_without_engines_fails_instead_of_simulating(self):
        with patch.object(GarakAdapter, 'is_available', return_value=False), patch(
            'core.adapters.pyrit_adapter.PyRITAdapter.is_available', return_value=False
        ):
            with self.assertRaisesRegex(RuntimeError, 'No real scan engine'):
                _select_engine('auto')

    def test_missing_model_never_produces_report(self):
        with patch('ipc_server._emit') as emit:
            with self.assertRaises(RuntimeError):
                run_scan_pipeline({'target': 'http://localhost:11500', 'mode': 'local',
                                   'local_model_path': 'missing-regression-model.gguf', 'engine': 'auto'})
            self.assertFalse(any(call.args[0]['type'] == 'complete' for call in emit.call_args_list))


if __name__ == '__main__':
    unittest.main()
