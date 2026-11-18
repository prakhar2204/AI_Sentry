"""Generate example AWS templates for offline cfn-lint validation. Never deploys."""
import json
from pathlib import Path
import sys

from core.deploy.aws_templates import build_template


def main():
    directory = Path(sys.argv[1]) if len(sys.argv) > 1 else Path('../../.tools/cloud-templates')
    directory.mkdir(parents=True, exist_ok=True)
    for mode in ('bedrock', 'sagemaker', 'lambda'):
        config = {'region': 'us-east-1', 'deployment_mode': mode, 'endpoint_scope': 'public',
                  'execution_role_arn': 'arn:aws:iam::123456789012:role/ExampleInferenceRole',
                  'model_id': 'example.model-v1', 'instance_type': 'ml.g4dn.xlarge',
                  'container_image': '123456789012.dkr.ecr.us-east-1.amazonaws.com/example:v1',
                  'model_data_url': 's3://example-artifacts/model.tar.gz'}
        target = directory / f'{mode}.json'
        target.write_text(json.dumps(build_template(config, f'sp-example-{mode}', '123456789012'), indent=2), encoding='utf-8')
        print(target)


if __name__ == '__main__':
    main()
