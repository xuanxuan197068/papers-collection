import unittest
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
AGENTS_SKILL = ROOT / ".agents" / "skills" / "radar-digest" / "SKILL.md"
CLAUDE_SKILL = ROOT / ".claude" / "skills" / "radar-digest" / "SKILL.md"


class RadarSkillSyncTest(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.agents_bytes = AGENTS_SKILL.read_bytes()
        cls.claude_bytes = CLAUDE_SKILL.read_bytes()
        cls.text = cls.agents_bytes.decode("utf-8")

    def test_skill_files_are_byte_identical(self):
        self.assertEqual(
            self.agents_bytes,
            self.claude_bytes,
            "Claude and Codex radar-digest Skills must remain byte-identical",
        )

    def test_skill_is_platform_neutral(self):
        forbidden = (
            "subagent_type",
            "haiku",
            "sonnet",
            "webfetch",
            "agent",
            ".agents/skills",
            ".claude/skills",
            "每批 ≤5",
        )
        lower_text = self.text.lower()
        for token in forbidden:
            with self.subTest(token=token):
                self.assertNotIn(token.lower(), lower_text)

    def test_skill_contains_v2_contract_and_workflow(self):
        required = (
            "radar/schema/technique-v2.schema.json",
            '"name"',
            '"type"',
            '"target"',
            '"action"',
            '"effect"',
            '"grounding"',
            '"limitation"',
            "0-4",
            "grounding=explicit",
            "grounding=partial",
            "使用简洁中文",
            "参与者数量",
            "所有 `type=other` 的 atom 必须逐项人工审计",
            "不得因摘要不足而自动读取论文页或 PDF",
            "--mode full",
            "--mode technique",
            "--force",
            "--check-only",
            "type + name + target/action",
            "不同论文数",
            "有序 technique atom 链",
        )
        for marker in required:
            with self.subTest(marker=marker):
                self.assertIn(marker, self.text)


if __name__ == "__main__":
    unittest.main()
