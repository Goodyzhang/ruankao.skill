"""Release archives must keep optional materials separate from tool installation."""
import hashlib
import importlib.util
from pathlib import Path
import subprocess
import tempfile
import unittest
import zipfile


SPEC = importlib.util.spec_from_file_location(
    'build_release', Path(__file__).resolve().parents[1] / 'scripts/build_release.py')
release = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(release)


class ReleaseTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.root = (Path(self.temp.name) / 'repo').resolve()
        self.root.mkdir()
        self.original_root = release.ROOT
        release.ROOT = self.root
        self.addCleanup(setattr, release, 'ROOT', self.original_root)
        for name, text in {
            '.gitattributes': '/artifacts export-ignore\n/materials export-ignore\n',
            'NOTICE.md': 'Sources retain their own rights.\n',
            'skills/demo/SKILL.md': 'Tool fixture\n',
            'artifacts/chapter/index.html': '<h1>Large visual book</h1>',
            'materials/系统架构设计师/README.md': '# Study materials\n',
            **{f'materials/系统架构设计师/{category}/index.md': category
               for category in ('教材', '笔记', '题库', '案例分析', '论文')},
        }.items():
            path = self.root / name
            path.parent.mkdir(parents=True, exist_ok=True)
            path.write_text(text, encoding='utf-8')
        subprocess.run(['git', 'init', '-q', str(self.root)], check=True)
        release.git('add', '.')
        release.git('-c', 'user.name=Release Test', '-c', 'user.email=test@example.invalid',
                    '-c', 'commit.gpgsign=false', 'commit', '-qm', 'fixture')
        self.output = self.root.parent / 'out'

    def test_package_boundaries_and_checksums(self):
        release.build(self.output, '1.0.0')
        archives = list(self.output.rglob('*.zip'))
        self.assertEqual(len(archives), 6)
        with zipfile.ZipFile(self.output / 'toolkit/ruankao-toolkit-v1.0.0.zip') as archive:
            names = archive.namelist()
            self.assertTrue(any('/skills/' in name for name in names))
            self.assertFalse(any('/materials/' in name or '/artifacts/' in name for name in names))
        with zipfile.ZipFile(self.output / 'materials/ruankao-architect-questions-cases-v1.0.0.zip') as archive:
            names = archive.namelist()
            self.assertIn('系统架构设计师/题库/index.md', names)
            self.assertIn('系统架构设计师/案例分析/index.md', names)
            self.assertFalse(any('/教材/' in name or '/论文/' in name for name in names))
        with zipfile.ZipFile(self.output / 'materials/ruankao-architect-materials-v1.0.0.zip') as archive:
            self.assertEqual(len(archive.namelist()), 7)
        for sums in self.output.rglob('SHA256SUMS.txt'):
            for line in sums.read_text().splitlines():
                digest, name = line.split('  ')
                self.assertEqual(digest, hashlib.sha256((sums.parent / name).read_bytes()).hexdigest())

    def test_dirty_source_cannot_be_packaged(self):
        (self.root / 'NOTICE.md').write_text('Uncommitted change')
        with self.assertRaises(subprocess.CalledProcessError):
            release.build(self.output, '1.0.0')
        self.assertFalse(self.output.exists())

    def test_output_cannot_be_inside_repository(self):
        with self.assertRaises(ValueError):
            release.build(self.root / 'dist', '1.0.0')


if __name__ == '__main__':
    unittest.main()
