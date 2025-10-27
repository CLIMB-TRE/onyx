import json
import sys
from collections import OrderedDict
import yaml


def normalize_actions(a):
    if a is None:
        return []
    if isinstance(a, str):
        return [a]
    return list(a)


def refactor_project(data):
    # data['contents'] expected
    for content in data.get("contents", []):
        for group in content.get("groups", []):
            # build ordered map field -> set(actions)
            field_actions = OrderedDict()
            # keep insertion order by iterating original permissions
            for perm in group.get("permissions", []):
                actions = set(
                    normalize_actions(perm.get("action") or perm.get("actions"))
                )
                fields = perm.get("fields", [])
                for f in fields:
                    if f not in field_actions:
                        field_actions[f] = set()
                    field_actions[f].update(actions)
            # produce consolidated permissions: one entry per field with sorted actions
            consolidated = []
            for f, acts in field_actions.items():
                if not acts:
                    continue
                consolidated.append(
                    {
                        "field": f,
                        "actions": ",".join(sorted(acts)),
                    }
                )
            group["permissions"] = consolidated
    return data


def main(src_path):
    with open(src_path, "r") as fh:
        data = json.load(fh)
    out = refactor_project(data)
    # dump YAML for readability
    print(yaml.safe_dump(out, sort_keys=False, default_flow_style=False))


if __name__ == "__main__":
    if len(sys.argv) < 2:
        print(
            "Usage: python refactor_permissions.py path/to/project.json",
            file=sys.stderr,
        )
        sys.exit(2)
    main(sys.argv[1])
