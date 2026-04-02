import yaml
import sys

def parse_aiml(filepath):
    try:
        with open(filepath, 'r') as f:
            data = yaml.safe_load(f)

        print("AIML Orchestrator Initialized")

        if 'pipeline' in data:
            pipeline = data['pipeline']
            print(f"Loaded Pipeline: {pipeline.get('name')}")

            steps = pipeline.get('steps', [])
            print(f"Total Steps: {len(steps)}")

            for i, step in enumerate(steps):
                agent = step.get('agent', 'unknown')
                print(f"  Step {i+1}: Assigned to Agent '{agent}'")
                if 'requires' in step and step['requires'] == 'human_approval':
                    print(f"    [!] HILT Escalation Required: Human approval needed for step {i+1}")

    except Exception as e:
        print(f"Error parsing AIML file: {e}")
        sys.exit(1)

if __name__ == "__main__":
    parse_aiml("pipeline.yaml")
