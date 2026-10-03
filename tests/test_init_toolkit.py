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
        self.assertEqual(len(list((self.vault / '.agents/skills').glob('*/SKILL.md'))), 6)
        note = next(self.vault.glob('个人资料/笔记/软考/系统架构设计师-高级/错题本/*.md'))
        note.write_text('PRIVATE ANSWER sentinel\n', encoding='utf-8')
        skill = self.vault / '.agents/skills/soft-exam-prep/SKILL.md'
        skill.write_text('custom skill\n', encoding='utf-8')
        self.run_install()
        self.assertEqual(skill.read_text(encoding='utf-8'), 'custom skill\n')
        binding = self.vault / '.soft-exam.local.json'
        binding.write_text('{"source_root": "用户资料", "grok": "skip"}', encoding='utf-8')
        original_binding = binding.read_bytes()
        self.run_install(upgrade_skills=True)
        self.assertEqual(binding.read_bytes(), original_binding)
        self.assertNotEqual(skill.read_text(encoding='utf-8'), 'custom skill\n')
        self.assertEqual(note.read_text(encoding='utf-8'), 'PRIVATE ANSWER sentinel\n')

    def test_all_six_skills_resources_are_copied_byte_for_byte(self):
        self.run_install()
        source = installer.ROOT / 'skills'
        installed = self.vault / '.agents/skills'
        for path in source.rglob('*'):
            if not path.is_file() or '__pycache__' in path.parts:
                continue
            with self.subTest(resource=path.relative_to(source)):
                self.assertEqual((installed / path.relative_to(source)).read_bytes(), path.read_bytes())
        installed = installed / 'soft-exam-review-book'
        self.assertTrue((installed / 'assets/reader/quiz-state.js').is_file())
        self.assertTrue((installed / 'assets/characters/whale-reference.png').is_file())
        self.assertTrue((installed / 'references/environment.md').is_file())

    def test_upgrade_from_five_skills_adds_review_book_without_replacing_work(self):
        self.run_install()
        import shutil
        shutil.rmtree(self.vault / '.agents/skills/soft-exam-review-book')
        book = self.vault / '个人资料/笔记/软考/系统架构设计师-高级/速查复习册/05-软件工程基础知识'
        book.mkdir(parents=True)
        relay = book / '制作记录.md'
        relay.write_text('CURRENT STAGE: diagrams; adopted assets stay here', encoding='utf-8')
        generated = book / 'index.html'
        generated.write_text('<h1>User-created review book</h1>', encoding='utf-8')
        before = {p: p.read_bytes() for p in (relay, generated)}
        self.run_install(upgrade_skills=True)
        self.assertEqual(len(list((self.vault / '.agents/skills').glob('*/SKILL.md'))), 6)
        for path, content in before.items():
            self.assertEqual(path.read_bytes(), content)

    def test_symlink_blocks_all_writes(self):
        outside = Path(self.tmp.name) / 'outside'
        outside.mkdir()
        self.vault.mkdir()
        try:
            (self.vault / '.agents').symlink_to(outside, target_is_directory=True)
        except OSError:
            self.skipTest('当前 Windows 账户不允许创建测试用符号链接')
        with self.assertRaises(ValueError):
            self.run_install()
        self.assertFalse((self.vault / '个人资料').exists())
        self.assertEqual(list(outside.iterdir()), [])

    def test_all_platform_targets(self):
        with contextlib.redirect_stdout(io.StringIO()):
            installer.install(self.vault, list(installer.PLATFORMS))
        for folder in ['.agents', '.claude', '.trae']:
            self.assertEqual(len(list((self.vault / folder / 'skills').glob('*/SKILL.md'))), 6)


if __name__ == '__main__':
    unittest.main()
