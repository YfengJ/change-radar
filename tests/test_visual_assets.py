from __future__ import annotations

from pathlib import Path
import re
import unittest
import xml.etree.ElementTree as ET


ROOT = Path(__file__).resolve().parents[1]
README = ROOT / "README.md"


class VisualAssetTests(unittest.TestCase):
    def test_readme_references_valid_svg_diagrams(self) -> None:
        readme = README.read_text(encoding="utf-8")
        svg_paths = re.findall(r'<img src="([^"]+\.svg)"', readme)

        self.assertGreaterEqual(len(svg_paths), 3)
        for svg_path in svg_paths:
            path = ROOT / svg_path
            self.assertTrue(path.exists(), f"Missing SVG asset: {svg_path}")
            root = ET.parse(path).getroot()
            self.assertTrue(root.tag.endswith("svg"), f"Not an SVG file: {svg_path}")

    def test_mermaid_sources_exist_for_svg_diagrams(self) -> None:
        expected = [
            ROOT / "docs/diagrams/change-radar-workflow.mmd",
            ROOT / "docs/diagrams/risk-ladder.mmd",
            ROOT / "docs/diagrams/ci-gate.mmd",
        ]

        for path in expected:
            self.assertTrue(path.exists(), f"Missing Mermaid source: {path}")
            text = path.read_text(encoding="utf-8")
            self.assertIn("flowchart", text)

    def test_skill_icon_assets_exist(self) -> None:
        metadata = (ROOT / "change-radar/agents/openai.yaml").read_text(encoding="utf-8")
        icon_paths = re.findall(r'icon_(?:small|large): "([^"]+)"', metadata)

        self.assertEqual(len(icon_paths), 2)
        for icon_path in icon_paths:
            path = ROOT / "change-radar" / icon_path
            self.assertTrue(path.exists(), f"Missing icon asset: {icon_path}")
            root = ET.parse(path).getroot()
            self.assertTrue(root.tag.endswith("svg"), f"Not an SVG file: {icon_path}")


if __name__ == "__main__":
    unittest.main()
