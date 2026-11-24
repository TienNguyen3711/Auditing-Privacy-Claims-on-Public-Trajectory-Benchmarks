"""Smoke test: every planned package imports and the model config lists the four chosen models."""
import importlib
import unittest
from pathlib import Path

import yaml

ROOT = Path(__file__).resolve().parents[1]
PACKAGES = ["data_io", "serialize", "controls", "llm", "contamination", "mechanisms", "attacks", "audit", "analysis"]


class Layout(unittest.TestCase):
    def test_packages_import(self):
        for name in PACKAGES:
            self.assertTrue(importlib.import_module(name).__doc__, name)

    def test_model_config(self):
        cfg = yaml.safe_load((ROOT / "configs/models.yaml").read_text())
        self.assertEqual(set(cfg["models"]), {"olmo2_13b", "llama31_8b", "gemma3_12b", "qwen3_14b"})
        for key, m in cfg["models"].items():
            self.assertTrue(m["base"] and m["instruct"], key)


if __name__ == "__main__":
    unittest.main()
