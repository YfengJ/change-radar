from __future__ import annotations

import importlib.util
import json
from pathlib import Path
import subprocess
import tempfile
import unittest


ROOT = Path(__file__).resolve().parents[1]
SCRIPT = ROOT / "change-radar" / "scripts" / "change_radar.py"

spec = importlib.util.spec_from_file_location("change_radar", SCRIPT)
change_radar = importlib.util.module_from_spec(spec)
assert spec and spec.loader
spec.loader.exec_module(change_radar)


class ChangeRadarTests(unittest.TestCase):
    def test_risk_cues_find_high_value_paths(self) -> None:
        files = [
            "package.json",
            "src/auth/session.ts",
            ".github/workflows/ci.yml",
            "docs/usage.md",
        ]

        labels = [label for label, _ in change_radar.risk_cues(files)]

        self.assertIn("Dependencies changed", labels)
        self.assertIn("Auth, security, or money path changed", labels)
        self.assertIn("CI or deployment changed", labels)
        self.assertIn("Documentation changed", labels)

    def test_risk_cues_include_executable_source_changes(self) -> None:
        labels = [label for label, _ in change_radar.risk_cues(["tools/change_radar.py"])]

        self.assertIn("Executable source changed", labels)

    def test_executable_source_risk_excludes_test_files(self) -> None:
        cues = dict(change_radar.risk_cues(["tools/change_radar.py", "tests/test_change_radar.py"]))

        self.assertEqual(cues["Executable source changed"], ["tools/change_radar.py"])

    def test_package_json_commands_prefer_detected_manager(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            repo = Path(tmp)
            (repo / "package.json").write_text(
                '{"scripts":{"test":"vitest","lint":"eslint .","build":"vite build"}}',
                encoding="utf-8",
            )
            (repo / "pnpm-lock.yaml").write_text("lockfileVersion: 9\n", encoding="utf-8")

            commands = change_radar.package_json_commands(repo)

        self.assertEqual(commands, ["pnpm run lint", "pnpm run test", "pnpm run build"])

    def test_nearest_tests_match_common_names(self) -> None:
        changed = ["src/payments/checkout.ts", "src/lib/math.py"]
        universe = [
            "src/payments/checkout.test.ts",
            "tests/test_math.py",
            "README.md",
        ]

        tests = change_radar.nearest_tests(changed, universe)

        self.assertIn("src/payments/checkout.test.ts", tests)
        self.assertIn("tests/test_math.py", tests)

    def test_python_without_pytest_config_uses_unittest(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            repo = Path(tmp)
            (repo / "tests").mkdir()
            (repo / "tool.py").write_text("print('ok')\n", encoding="utf-8")

            commands = change_radar.suggest_commands(repo, ["tool.py"])

        self.assertIn("python3 -m unittest discover -s tests", commands)
        self.assertNotIn("python3 -m pytest", commands)

    def test_render_report_without_git_is_still_useful(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            repo = Path(tmp)
            (repo / "pyproject.toml").write_text("[project]\nname='x'\n", encoding="utf-8")

            report = change_radar.render_report(repo, "HEAD", True)

        self.assertIn("# Change Radar Report", report)
        self.assertIn("Git detected: no", report)
        self.assertIn("Python project", report)

    def test_report_data_scores_high_risk_auth_api_without_tests(self) -> None:
        files = [
            "src/auth/session.ts",
            "src/api/checkout.ts",
            "package.json",
        ]

        data = change_radar.build_report_data(Path.cwd(), "HEAD", True, files_override=files)

        self.assertEqual(data["overall_risk"], "P0")
        self.assertGreaterEqual(data["risk_score"], 90)
        self.assertIn("Auth, security, or money path changed", data["risk_labels"])
        self.assertIn("Public API or integration changed", data["risk_labels"])
        self.assertIn("No nearby tests found for changed production files.", data["blocking_gaps"])
        self.assertIn("Add or identify tests for changed production files.", data["recommended_actions"])

    def test_content_risk_cues_detect_secrets_and_focused_tests(self) -> None:
        cues = change_radar.content_risk_cues(
            [
                "+API_KEY = 'not_a_real_test_fixture_12345'",  # change-radar: ignore-risk
                "+test.only('charges card', () => {})",  # change-radar: ignore-risk
                "+it.skip('handles failure', () => {})",  # change-radar: ignore-risk
            ]
        )

        labels = [cue["label"] for cue in cues]
        self.assertIn("Possible secret added", labels)
        self.assertIn("Focused test left enabled", labels)
        self.assertIn("Skipped test added", labels)

    def test_secret_content_evidence_is_redacted(self) -> None:
        cues = change_radar.content_risk_cues(["+API_KEY = 'not_a_real_test_fixture_12345'"])  # change-radar: ignore-risk
        secret_cue = next(cue for cue in cues if cue["label"] == "Possible secret added")

        self.assertNotIn("not_a_real_test_fixture_12345", secret_cue["evidence"][0])  # change-radar: ignore-risk
        self.assertIn("[REDACTED]", secret_cue["evidence"][0])

    def test_content_risk_ignore_marker_allows_safe_fixtures(self) -> None:
        cues = change_radar.content_risk_cues(
            [
                "+API_KEY = 'not_a_real_test_fixture_12345'  # change-radar: ignore-risk",
                "+test.only('fixture only') // change-radar: ignore-risk",
            ]
        )

        self.assertEqual(cues, [])

    def test_content_risk_ignores_documentation_mentions(self) -> None:
        cues = change_radar.content_risk_cues(
            [
                {"path": "README.md", "line": "+Document that TODO markers and test.only are detected."},  # change-radar: ignore-risk
                {"path": "docs/security.md", "line": "+Example API_KEY = 'fake_secret_documentation_fixture'"},  # change-radar: ignore-risk
            ]
        )

        self.assertEqual(cues, [])

    def test_verification_plan_groups_commands_by_purpose(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            repo = Path(tmp)
            (repo / "package.json").write_text(
                '{"scripts":{"typecheck":"tsc --noEmit","lint":"eslint .","test":"vitest","build":"vite build"}}',
                encoding="utf-8",
            )
            (repo / "src").mkdir()
            (repo / "src" / "ui.tsx").write_text("export const Ui = () => null\n", encoding="utf-8")

            data = change_radar.build_report_data(repo, "HEAD", True, files_override=["src/ui.tsx"])

        plan = data["verification_plan"]
        self.assertEqual(plan["static"], ["npm run typecheck", "npm run lint"])
        self.assertEqual(plan["focused"], ["npm run test"])
        self.assertEqual(plan["broad"], ["npm run build"])
        self.assertIn("Check affected UI states manually or with browser automation.", plan["manual"])

    def test_json_output_is_machine_readable(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            repo = Path(tmp)
            subprocess.run(["git", "init"], cwd=repo, check=True, capture_output=True, text=True)
            (repo / "src").mkdir()
            (repo / "src" / "auth.py").write_text("TOKEN = 'x'\n", encoding="utf-8")

            output = subprocess.check_output(
                [
                    "python3",
                    str(SCRIPT),
                    "--repo",
                    str(repo),
                    "--format",
                    "json",
                ],
                text=True,
            )

        data = json.loads(output)
        self.assertEqual(data["git"]["detected"], True)
        self.assertIn("src/auth.py", data["changed_files"])
        self.assertIn("overall_risk", data)
        self.assertIn("verification_plan", data)

    def test_fail_on_risk_returns_gate_exit_code(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            repo = Path(tmp)
            subprocess.run(["git", "init"], cwd=repo, check=True, capture_output=True, text=True)
            (repo / "src").mkdir()
            (repo / "src" / "auth.py").write_text("TOKEN = 'x'\n", encoding="utf-8")

            result = subprocess.run(
                [
                    "python3",
                    str(SCRIPT),
                    "--repo",
                    str(repo),
                    "--fail-on-risk",
                    "P1",
                ],
                text=True,
                capture_output=True,
                check=False,
            )

        self.assertEqual(result.returncode, 3)
        self.assertIn("Risk gate failed", result.stderr)


if __name__ == "__main__":
    unittest.main()
