import json
import re
import tempfile
import unittest
from pathlib import Path


ROOT = Path(__file__).resolve().parent.parent
SKILLS = ROOT / "skills"


class TestWorkflowContract(unittest.TestCase):
    def test_consolidated_skill_inventory(self):
        aliases = {"oracle-learn-from", "oracle-apprentice", "oracle-cover-analyze"}
        names = sorted(
            p.name for p in SKILLS.iterdir()
            if p.is_dir() and p.name.startswith("oracle-") and p.name not in aliases
        )
        self.assertEqual(len(names), 26)
        self.assertIn("oracle-study", names)
        self.assertIn("oracle-cover", names)
        self.assertNotIn("oracle-edit-plan", names)
        for alias in aliases:
            self.assertTrue((SKILLS / alias / "SKILL.md").is_file())

    def test_legacy_aliases_are_thin_routes(self):
        expected = {
            "oracle-learn-from": "oracle-study --mode benchmark",
            "oracle-apprentice": "oracle-study --mode practice",
            "oracle-cover-analyze": "oracle-cover --mode analyze",
        }
        for alias, target in expected.items():
            text = (SKILLS / alias / "SKILL.md").read_text(encoding="utf-8")
            self.assertIn(target, text)
            self.assertIn("不包含独立", text)

    def test_cover_is_two_mode_entry(self):
        text = (SKILLS / "oracle-cover" / "SKILL.md").read_text(encoding="utf-8")
        self.assertIn("generate", text)
        self.assertIn("analyze", text)
        self.assertIn("cover-generation-protocol.md", text)
        self.assertIn("cover-analysis-protocol.md", text)
        self.assertTrue((ROOT / "references" / "cover-generation-protocol.md").exists())
        self.assertTrue((ROOT / "references" / "cover-analysis-protocol.md").exists())

    def test_deleted_production_boundary_has_no_runtime_skill(self):
        self.assertFalse((SKILLS / "oracle-edit-plan").exists())
        self.assertFalse((ROOT / "tools" / "context.py").read_text(encoding="utf-8").count('"edit-plan"'))

    def test_root_routes_legacy_names_to_new_boundaries(self):
        text = (ROOT / "SKILL.md").read_text(encoding="utf-8")
        self.assertIn("/oracle-study", text)
        self.assertIn("oracle-cover --mode analyze", text)
        self.assertIn("video-production-workflow", text)
        self.assertNotRegex(text, r"调用\s+`?/oracle-(learn-from|apprentice|cover-analyze|edit-plan)")

    def test_context_readlist_uses_new_tasks(self):
        text = (ROOT / "tools" / "context.py").read_text(encoding="utf-8")
        self.assertIn('"study"', text)
        self.assertIn('"cover"', text)
        self.assertIn("cover-generation-protocol.md", text)
        self.assertIn("cover-analysis-protocol.md", text)
        self.assertNotIn('"learn-from"', text)
        self.assertNotIn('"apprentice"', text)
        self.assertNotIn('"edit-plan"', text)

    def test_install_manifest_uses_current_runtime_names(self):
        text = (ROOT / "install.sh").read_text(encoding="utf-8")
        self.assertIn("oracle-study", text)
        self.assertIn('MAIN_DST="$TARGET_DIR/oracle-bone"', text)
        for alias in ("oracle-learn-from", "oracle-apprentice", "oracle-cover-analyze"):
            self.assertIn(f"  {alias}\n", text)
        self.assertNotIn("  oracle-edit-plan\n", text)

    def test_windows_installer_reads_skills_subdirectory(self):
        text = (ROOT / "install.ps1").read_text(encoding="utf-8")
        self.assertIn('$SkillRoot = Join-Path $RepoRoot "skills"', text)
        self.assertIn('$mainSource = $RepoRoot', text)

    def test_copy_install_carries_shared_runtime_resources(self):
        sh = (ROOT / "install.sh").read_text(encoding="utf-8-sig")
        ps = (ROOT / "install.ps1").read_text(encoding="utf-8-sig")
        for resource in ("references", "shared-references", "templates", "tools"):
            self.assertIn(resource, sh)
            self.assertIn(resource, ps)
        # Direct copies live at <target>/oracle-*, while repository links use
        # ../../resources; installers must therefore keep a parent-level copy
        # and a package-local copy for the root entry.
        self.assertIn('RESOURCE_ROOT="$(cd -- "$(dirname "$TARGET_DIR")"', sh)
        self.assertIn('$resourceRoot = Split-Path -Parent $Target', ps)
        self.assertIn('PACKAGE_ROOT="$TARGET_DIR/oracle-bone"', sh)
        self.assertIn('PACKAGE_ROOT_OWNED=0', sh)
        self.assertIn('if [[ "$PACKAGE_ROOT_OWNED" -eq 1 ]]', sh)
        self.assertIn('$packageRoot = Join-Path $Target $SkillName', ps)
        self.assertIn('if ($packageRootOwned)', ps)
        self.assertIn('.oracle-bone-resource', sh)
        self.assertIn('.oracle-bone-resource', ps)
        self.assertIn('RESOURCE_CONFLICT=0', sh)
        self.assertIn('$resourceConflicts = @()', ps)

    def test_copy_install_layout_resolves_repository_relative_links(self):
        # Model the direct-copy layout without executing a platform-specific
        # installer. ../../references from a copied sub-skill must land in the
        # parent of the target skills directory, while root routes use the
        # package-local copy.
        with tempfile.TemporaryDirectory() as tmp:
            target = Path(tmp) / "skills"
            direct_skill = target / "oracle-cover"
            package_root = target / "oracle-bone"
            self.assertEqual(
                (direct_skill / "../../references").resolve(),
                target.parent / "references",
            )
            self.assertEqual(
                (package_root / "references").resolve(),
                target / "oracle-bone" / "references",
            )

    def test_installers_retire_old_edit_plan_without_deleting_foreign_dirs(self):
        sh = (ROOT / "install.sh").read_text(encoding="utf-8-sig")
        ps = (ROOT / "install.ps1").read_text(encoding="utf-8-sig")
        self.assertIn("RETIRED=(oracle-edit-plan)", sh)
        self.assertIn("retired = Join-Path $Target \"oracle-edit-plan\"", ps)
        self.assertIn("manual review", ps)

    def test_uninstaller_owns_root_router_and_checks_link_source(self):
        text = (ROOT / "uninstall.sh").read_text(encoding="utf-8-sig")
        self.assertIn('ROOT_TARGET="$HOME/.claude/skills/oracle-bone"', text)
        self.assertIn('"$LINK_TARGET" == "$SOURCE_ROOT/skills/$s"', text)
        self.assertIn('"$ROOT_LINK_TARGET" == "$SOURCE_ROOT"', text)


if __name__ == "__main__":
    unittest.main(verbosity=2)
