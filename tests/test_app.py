from pathlib import Path
import unittest

from streamlit.testing.v1 import AppTest


class AppSmokeTests(unittest.TestCase):
    def test_app_runs_and_reruns_without_exceptions(self):
        app = AppTest.from_file(Path(__file__).resolve().parents[1] / "app.py")
        for _ in range(2):
            app.run(timeout=20)
            self.assertEqual(len(app.exception), 0)
            self.assertEqual(app.title[0].value, "Transportation System")


if __name__ == "__main__":
    unittest.main()
