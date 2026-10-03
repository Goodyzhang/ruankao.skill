"""Release validation rejects broken payloads, not just missing filenames."""
import importlib.util
from pathlib import Path
import shutil
import tempfile
import unittest

ROOT = Path(__file__).resolve().parents[1]
spec = importlib.util.spec_from_file_location('toolkit_validator', ROOT / 'scripts/validate_toolkit.py')
validator = importlib.util.module_from_spec(spec)
spec.loader.exec_module(validator)
reader_spec = importlib.util.spec_from_file_location('book_checker', ROOT / 'skills/soft-exam-review-book/scripts/check_book.py')
reader = importlib.util.module_from_spec(reader_spec)
reader_spec.loader.exec_module(reader)


class PackageValidationTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.tmp = tempfile.TemporaryDirectory()
        cls.addClassCleanup(cls.tmp.cleanup)
        cls.root = Path(cls.tmp.name) / 'published copy'
        shutil.copytree(ROOT, cls.root, ignore=shutil.ignore_patterns('.git', '__pycache__', 'dist'))

    def mutate(self, relative, content):
        path = self.root / relative
        before = path.read_bytes() if path.exists() else None
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(content, encoding='utf-8')
        def restore():
            if before is None:
                path.unlink()
            else:
                path.write_bytes(before)
        self.addCleanup(restore)
        return validator.validate(self.root)

    def test_six_correct_skill_names_are_required_not_just_count(self):
        source = self.root / 'skills/soft-exam-prep'
        renamed = self.root / 'skills/not-a-toolkit-skill'
        source.rename(renamed)
        self.addCleanup(renamed.rename, source)
        errors = validator.validate(self.root)
        self.assertTrue(any('Skill set mismatch' in e and 'soft-exam-prep' in e for e in errors))

    def test_broken_reference_and_readme_image_are_reported(self):
        errors = self.mutate('CHECK-LINKS.md', '[Missing guide](skills/soft-exam-review-book/references/missing.md)\n![Missing image](docs/images/missing.png)\n')
        self.assertTrue(any('missing Markdown link skills/' in e for e in errors))
        self.assertTrue(any('missing Markdown link docs/images/missing.png' in e for e in errors))

    def test_local_bindings_and_concrete_paths_cannot_enter_release(self):
        # Build synthetic private paths at runtime so the test source is publishable.
        private = '/' + '/'.join(('Users', 'fictionaluser', 'PrivateVault'))
        errors = self.mutate('.soft-exam.local.json', '{"vault_root": "' + private + '"}')
        self.assertTrue(any('machine-local binding' in e for e in errors))
        self.assertTrue(any('device path' in e for e in errors))

    def test_html_and_json_are_also_checked_for_credentials(self):
        for name in ('credential-fixture.html', 'credential-fixture.json'):
            errors = self.mutate(name, 'ghp_' + 'x' * 24)
            self.assertTrue(any(name + ': possible credential' in e for e in errors))

    def test_review_asset_contents_must_be_nonempty(self):
        errors = self.mutate('skills/soft-exam-review-book/assets/reader/reader.css', '')
        self.assertTrue(any('Missing or empty Skill resource: soft-exam-review-book/assets/reader/reader.css' in e for e in errors))


class OfflineDemoTests(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.addCleanup(self.tmp.cleanup)
        self.root = Path(self.tmp.name) / 'relocated demo'
        self.root.mkdir()
        self.page = self.root / 'index.html'
        (self.root / 'diagram.svg').write_text('<svg xmlns="http://www.w3.org/2000/svg"></svg>', encoding='utf-8')

    def check(self, html):
        self.page.write_text(html, encoding='utf-8')
        return validator.check_public_pages(reader, [self.page], self.root)

    def test_local_images_and_citation_links_work_after_relocation(self):
        errors = self.check('<h1 id="mail">Mail</h1><a href="#mail">Jump</a><img src="diagram.svg" alt="diagram"><a href="https://www.rfc-editor.org/rfc/rfc5321">Source</a>')
        self.assertEqual(errors, [])

    def test_missing_image_and_anchor_fail_with_actionable_errors(self):
        errors = self.check('<img src="absent.png" alt="missing"><a href="#missing">Jump</a>')
        self.assertTrue(any('missing local resource/link: absent.png' in e for e in errors))
        self.assertTrue(any('missing HTML anchor: #missing' in e for e in errors))

    def test_external_runtime_and_escaping_source_paths_are_rejected(self):
        errors = self.check('<script src="https://cdn.example.invalid/mermaid.js"></script><a href="../private.md">Notes</a>')
        self.assertTrue(any('external runtime resource' in e for e in errors))
        self.assertTrue(any('escapes the offline demo' in e for e in errors))

    def test_inline_css_dependency_is_checked(self):
        errors = self.check('<style>body { background: url("missing.png") }</style><h1>Mail</h1>')
        self.assertTrue(any('CSS resource is not available offline' in e for e in errors))


if __name__ == '__main__':
    unittest.main()
