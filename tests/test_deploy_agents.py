import importlib.util
import tempfile
import unittest
from pathlib import Path

SPEC = importlib.util.spec_from_file_location("deploy_agents", Path(__file__).resolve().parents[1] / "scripts/deploy_agents.py")
MODULE = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(MODULE)


class DeploymentTests(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.addCleanup(self.tmp.cleanup)
        self.root = Path(self.tmp.name)
        self.source = self.root / "agents"
        self.target = self.root / "deployed"
        self.source.mkdir()

    def role(self, name, group="design", text="First"):
        path = self.source / group / f"{name}.toml"
        path.parent.mkdir(exist_ok=True)
        path.write_text(f'name = "{name}"\ndescription = "{text}"\nmodel = "gpt-6.1-sol"\nmodel_reasoning_effort = "high"\ndeveloper_instructions = "Instructions"\n')
        return path

    def test_deploy_check_update_remove_preserves_unmanaged(self):
        a = self.role("atlas")
        self.role("probe", "verification")
        self.assertTrue(MODULE.deploy(self.source, self.target, check=True)[0])
        self.assertFalse(self.target.exists())
        MODULE.deploy(self.source, self.target)
        (self.target / "personal.toml").write_text("keep")
        self.assertFalse(MODULE.deploy(self.source, self.target, check=True)[0])
        a.unlink()
        self.role("probe", "verification", "Updated")
        MODULE.deploy(self.source, self.target)
        self.assertFalse((self.target / "atlas.toml").exists())
        self.assertIn("Updated", (self.target / "probe.toml").read_text())
        self.assertEqual((self.target / "personal.toml").read_text(), "keep")

    def test_modified_copy_blocks_whole_deployment(self):
        self.role("atlas")
        MODULE.deploy(self.source, self.target)
        (self.target / "atlas.toml").write_text("user edit")
        self.role("probe")
        with self.assertRaisesRegex(ValueError, "locally edited"):
            MODULE.deploy(self.source, self.target)
        self.assertFalse((self.target / "probe.toml").exists())
        self.assertEqual((self.target / "atlas.toml").read_text(), "user edit")

    def test_modified_stale_copy_is_not_deleted(self):
        a = self.role("atlas")
        self.role("probe")
        MODULE.deploy(self.source, self.target)
        a.unlink()
        (self.target / "atlas.toml").write_text("user edit")
        with self.assertRaises(ValueError):
            MODULE.deploy(self.source, self.target)
        self.assertTrue((self.target / "atlas.toml").exists())

    def test_unmanaged_collision_is_not_overwritten(self):
        self.role("atlas")
        self.target.mkdir()
        (self.target / "atlas.toml").write_text("unmanaged")
        with self.assertRaises(ValueError):
            MODULE.deploy(self.source, self.target)

    def test_matching_existing_copy_can_be_adopted(self):
        p = self.role("atlas")
        self.target.mkdir()
        (self.target / p.name).write_bytes(p.read_bytes())
        MODULE.deploy(self.source, self.target)
        self.assertFalse(MODULE.deploy(self.source, self.target, check=True)[0])

    def test_duplicate_and_invalid_sources_write_nothing(self):
        self.role("atlas")
        duplicate = self.role("atlas", "verification")
        with self.assertRaisesRegex(ValueError, "Duplicate"):
            MODULE.deploy(self.source, self.target)
        duplicate.write_text('name = "atlas"\n')
        with self.assertRaisesRegex(ValueError, "Missing"):
            MODULE.deploy(self.source, self.target)
        self.assertFalse(self.target.exists())

    def test_symlink_destination_is_not_followed(self):
        self.role("atlas")
        self.target.mkdir()
        outside = self.root / "outside"
        outside.write_text("preserve")
        (self.target / "atlas.toml").symlink_to(outside)
        with self.assertRaisesRegex(ValueError, "regular file"):
            MODULE.deploy(self.source, self.target)
        self.assertEqual(outside.read_text(), "preserve")


if __name__ == "__main__":
    unittest.main()
