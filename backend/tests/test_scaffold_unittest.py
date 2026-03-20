import unittest
from pathlib import Path


ROOT = Path(__file__).resolve().parents[2]


class BootstrapSmokeTests(unittest.TestCase):
    def test_root_files_exist(self) -> None:
        for relative_path in [
            "README.md",
            ".gitignore",
            ".editorconfig",
            ".env.example",
            "Makefile",
            "docker-compose.yml",
            "docker-compose.override.yml",
        ]:
            self.assertTrue((ROOT / relative_path).exists(), relative_path)

    def test_backend_health_route_source_exists(self) -> None:
        source = (ROOT / "backend/app/api/routes/health.py").read_text(encoding="utf-8")
        self.assertIn('"/health"', source)
        self.assertIn('"status": "ok"', source)

    def test_frontend_login_page_exists(self) -> None:
        self.assertTrue((ROOT / "frontend/src/app/login/page.tsx").exists())


if __name__ == "__main__":
    unittest.main()
