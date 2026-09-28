"""Exercise the local Hiera lifecycle on the project's minimum Python version."""

import json
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path


REPO_ROOT = Path(__file__).resolve().parents[1]


class LocalHieraLifecycleTest(unittest.TestCase):
    def test_admit_and_run_on_supported_python(self):
        with tempfile.TemporaryDirectory(prefix="autosci-hiera-test-") as temporary:
            project = Path(temporary)
            (project / "tools").mkdir()
            (project / "wiki" / "experiments").mkdir(parents=True)
            (project / "wiki" / "ideas").mkdir(parents=True)
            (project / "wiki" / "experiments" / "demo.md").write_text(
                "---\ntitle: Demo\nlinked_idea: demo-idea\n---\n",
                encoding="utf-8",
            )
            (project / "wiki" / "ideas" / "demo-idea.md").write_text(
                "---\ntitle: Demo idea\n---\n", encoding="utf-8"
            )
            overrides = {
                "candidate": {"entrypoint": "run.py", "editable_files": ["run.py"]},
                "evaluation": {
                    "evaluate_command": [sys.executable, "{entrypoint}", "{result_file}"],
                    "result_file": "results/result.json",
                    "score_path": "score",
                    "metric": "score",
                    "direction": "maximize",
                },
                "resources": {"environment": "local", "timeout_seconds": 10, "max_evaluations": 2},
            }
            contract_file = project / "overrides.json"
            contract_file.write_text(json.dumps(overrides), encoding="utf-8")
            spec_file = project / "candidate.json"
            spec_file.write_text(
                json.dumps(
                    {
                        "candidate_id": "candidate-a",
                        "semantic_point": {"dim-method": "hyp-baseline-method"},
                        "files": {
                            "run.py": "import json, sys\nfrom pathlib import Path\n"
                            "Path(sys.argv[1]).write_text(json.dumps({'score': 0.75}))\n"
                        },
                    }
                ),
                encoding="utf-8",
            )

            def invoke(command, *args):
                result = subprocess.run(
                    [
                        sys.executable,
                        "-m",
                        "tools.hiera.cli",
                        "--project",
                        str(project),
                        command,
                        "demo",
                        "--run-id",
                        "smoke",
                        *args,
                    ],
                    cwd=REPO_ROOT,
                    text=True,
                    capture_output=True,
                    check=False,
                )
                self.assertEqual(result.returncode, 0, result.stderr)
                return json.loads(result.stdout)

            self.assertTrue(invoke("init", "--contract", str(contract_file))["contract_ready"])
            self.assertEqual(invoke("admit", "--spec", str(spec_file))["status"], "admitted")
            self.assertTrue(invoke("approve")["approved"])
            self.assertEqual(invoke("preflight", "--candidate", "candidate-a")["status"], "passed")
            receipt = invoke("run", "--candidate", "candidate-a")
            self.assertEqual(receipt["status"], "success")
            self.assertEqual(receipt["score"], 0.75)


if __name__ == "__main__":
    unittest.main()
