from __future__ import annotations

import importlib.util
from pathlib import Path
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


if __name__ == "__main__":
    unittest.main()
