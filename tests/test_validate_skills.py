import tempfile
import unittest
from pathlib import Path

from tools.validate_skills import (
    find_skill_dirs,
    read_text_with_fallbacks,
    validate_all,
    validate_skill_dir,
)


class ValidateSkillsTests(unittest.TestCase):
    def temp_dir(self):
        root = Path(__file__).resolve().parent / "_tmp"
        root.mkdir(exist_ok=True)
        return tempfile.TemporaryDirectory(dir=root)

    def write_skill(self, root: Path, name: str, description: str = "desc") -> Path:
        skill_dir = root / name
        (skill_dir / "agents").mkdir(parents=True)
        (skill_dir / "SKILL.md").write_text(
            f"---\nname: {name}\ndescription: {description}\n---\n\n# Skill\n",
            encoding="utf-8",
        )
        (skill_dir / "agents" / "openai.yaml").write_text("interface:\n  display_name: \"x\"\n", encoding="utf-8")
        return skill_dir

    def test_find_skill_dirs(self) -> None:
        with self.temp_dir() as tmp:
            root = Path(tmp)
            self.write_skill(root, "good-skill")
            (root / "scripts").mkdir()
            found = find_skill_dirs(root)
            self.assertEqual([path.name for path in found], ["good-skill"])

    def test_validate_skill_dir(self) -> None:
        with self.temp_dir() as tmp:
            root = Path(tmp)
            skill_dir = self.write_skill(root, "good-skill")
            self.assertEqual(validate_skill_dir(skill_dir), [])

    def test_validate_all_reports_errors(self) -> None:
        with self.temp_dir() as tmp:
            root = Path(tmp)
            bad = root / "BadSkill"
            bad.mkdir()
            (bad / "SKILL.md").write_text("---\nname: BadSkill\ndescription: desc\n---\n", encoding="utf-8")
            errors = validate_all(root)
            self.assertIn("BadSkill", errors)
            self.assertTrue(any("name must be lowercase hyphen-case" in item for item in errors["BadSkill"]))

    def test_read_text_with_fallbacks_supports_cp936(self) -> None:
        with self.temp_dir() as tmp:
            path = Path(tmp) / "skill.md"
            content = "---\nname: test-skill\ndescription: 中文说明\n---\n"
            path.write_text(content, encoding="cp936")
            self.assertEqual(read_text_with_fallbacks(path), content)


if __name__ == "__main__":
    unittest.main()
