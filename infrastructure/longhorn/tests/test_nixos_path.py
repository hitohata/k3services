"""Offline admission checks; requires Kyverno CLI v1.20.0 and Python yq."""

import json
import os
from pathlib import Path
import subprocess
import tempfile
import unittest


POLICY = Path(__file__).resolve().parents[1] / "admission/nixos-path.yaml"
CLI = os.environ.get("KYVERNO_CLI", "kyverno")
HOST_PATH = "/run/current-system/sw/bin"
IMAGE_PATH = "/usr/local/sbin:/usr/local/bin:/usr/sbin:/usr/bin:/sbin:/bin"
MANAGER = "docker.io/longhornio/longhorn-manager:v1.13.0"
INSTANCE = "docker.io/longhornio/longhorn-instance-manager:v1.13.0"


def pod():
    return {
        "apiVersion": "v1",
        "kind": "Pod",
        "metadata": {"name": "offline-path-test", "namespace": "longhorn-system"},
        "spec": {
            "containers": [
                {"name": "manager", "image": MANAGER},
                {
                    "name": "instance",
                    "image": INSTANCE,
                    "env": [{"name": "POD_NAME", "valueFrom": {"fieldRef": {"fieldPath": "metadata.name"}}}],
                    "envFrom": [{"configMapRef": {"name": "existing-config"}}],
                },
            ],
            "initContainers": [
                {"name": "init", "image": MANAGER, "env": [{"name": "PATH", "value": "/custom/bin:/bin"}]}
            ],
        },
    }


def apply(resource):
    with tempfile.TemporaryDirectory(prefix="longhorn-path-test-") as directory:
        source = Path(directory) / "pod.json"
        output = Path(directory) / "result.yaml"
        source.write_text(json.dumps(resource))
        result = subprocess.run(
            [CLI, "apply", str(POLICY), "--resource", str(source), "--output-file", str(output)],
            capture_output=True, text=True, timeout=60,
        )
        resources = []
        if output.exists() and output.read_text().strip():
            parsed = subprocess.run(["yq", "-s", ".", str(output)], check=True, capture_output=True, text=True)
            resources = [r for r in json.loads(parsed.stdout) if r]
        return result, resources


class NixOSPathTests(unittest.TestCase):
    def test_dynamic_pods_and_init_containers_preserve_existing_configuration(self):
        source = pod()
        result, resources = apply(source)
        self.assertEqual(result.returncode, 0, result.stdout + result.stderr)
        self.assertEqual(len(resources), 1)
        actual = resources[0]
        self.assertEqual(actual["spec"]["containers"][0]["env"], [{"name": "PATH", "value": IMAGE_PATH + ":" + HOST_PATH}])
        instance = actual["spec"]["containers"][1]
        self.assertEqual(instance["env"][0], source["spec"]["containers"][1]["env"][0])
        self.assertEqual(instance["envFrom"], source["spec"]["containers"][1]["envFrom"])
        self.assertEqual(instance["env"][-1]["value"], IMAGE_PATH + ":" + HOST_PATH)
        self.assertEqual(actual["spec"]["initContainers"][0]["env"], [{"name": "PATH", "value": "/custom/bin:/bin:" + HOST_PATH}])
        again, repeated = apply(actual)
        self.assertEqual(again.returncode, 0, again.stdout + again.stderr)
        self.assertEqual(repeated[0]["spec"], actual["spec"])

    def test_no_init_containers(self):
        source = pod()
        del source["spec"]["initContainers"]
        result, resources = apply(source)
        self.assertEqual(result.returncode, 0, result.stdout + result.stderr)
        self.assertEqual(len(resources), 1)
        self.assertNotIn("initContainers", resources[0]["spec"])

    def test_other_namespaces_are_not_mutated(self):
        source = pod()
        source["metadata"]["namespace"] = "default"
        source["spec"]["containers"][0]["image"] = "unreviewed.invalid/image:1"
        result, resources = apply(source)
        self.assertEqual(result.returncode, 0, result.stdout + result.stderr)
        for resource in resources:
            self.assertEqual(resource["spec"], source["spec"])

    def test_unreviewed_image_fails_closed(self):
        source = pod()
        source["spec"]["containers"][0]["image"] = "unreviewed.invalid/image:1"
        result, _ = apply(source)
        self.assertNotEqual(result.returncode, 0)

    def test_indirect_path_is_not_silently_overwritten(self):
        source = pod()
        source["spec"]["containers"][0]["env"] = [{"name": "PATH", "valueFrom": {"configMapKeyRef": {"name": "profile", "key": "path"}}}]
        result, _ = apply(source)
        self.assertNotEqual(result.returncode, 0)


if __name__ == "__main__":
    unittest.main()
