import contextlib
import importlib.util
import io
from pathlib import Path
import tempfile
import unittest

spec = importlib.util.spec_from_file_location('installer', Path(__file__).resolve().parents[1] / 'scripts/init_toolkit.py')
installer = importlib.util.module_from_spec(spec)
spec.loader.exec_module(installer)


class InitTests(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.addCleanup(self.tmp.cleanup)
        self.vault = Path(self.tmp.name) / 'Vault with 空格'

    def run_install(self, **kwargs):
        with contextlib.redirect_stdout(io.StringIO()):
            return installer.install(self.vault, ['antigravity', 'codex'], **kwargs)

    def test_dry_run_leaves_no_directory(self):
        self.run_install(dry_run=True)
        self.assertFalse(self.vault.exists())

    def test_repeat_and_upgrade_preserve_personal_notes(self):
        self.run_install()
        self.assertEqual(len(list((self.vault / '.agents/skills').glob('*/SKILL.md'))), 5)
        note = next(self.vault.glob('个人资料/笔记/软考/系统架构设计师-高级/错题本/*.md'))
        note.write_text('PRIVATE ANSWER sentinel\n')
        skill = self.vault / '.agents/skills/soft-exam-prep/SKILL.md'
        skill.write_text('custom skill\n')
        self.run_install()
        self.assertEqual(skill.read_text(), 'custom skill\n')
        self.run_install(upgrade_skills=True)
        self.assertNotEqual(skill.read_text(), 'custom skill\n')
        self.assertEqual(note.read_text(), 'PRIVATE ANSWER sentinel\n')

    def test_symlink_blocks_all_writes(self):
        outside = Path(self.tmp.name) / 'outside'
        outside.mkdir()
        self.vault.mkdir()
        (self.vault / '.agents').symlink_to(outside, target_is_directory=True)
        with self.assertRaises(ValueError):
            self.run_install()
        self.assertFalse((self.vault / '个人资料').exists())
        self.assertEqual(list(outside.iterdir()), [])

    def test_all_platform_targets(self):
        with contextlib.redirect_stdout(io.StringIO()):
            installer.install(self.vault, list(installer.PLATFORMS))
        for folder in ['.agents', '.claude', '.trae']:
            self.assertEqual(len(list((self.vault / folder / 'skills').glob('*/SKILL.md'))), 5)


if __name__ == '__main__':
    unittest.main()
