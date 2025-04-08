from django.test.testcases import TestCase
from utils.functions import get_permission, parse_permission, strtobool


class TestFunctions(TestCase):
    def test_get_permission(self):
        """
        Test the `get_permission` function.
        """

        # Test project-level permissions
        permission = get_permission(
            app_label="app",
            action="add",
            code="project",
        )
        self.assertEqual(permission, "app.add_project")

        # Test object-level permissions
        permission = get_permission(
            app_label="app",
            action="add",
            code="project",
            object_type="object_type",
        )
        self.assertEqual(permission, "app.add_project_object_type")

        # Test field-level permissions
        permission = get_permission(
            app_label="app",
            action="add",
            code="project",
            object_type="object_type",
            field="field",
        )
        self.assertEqual(permission, "app.add_project_object_type__field")

        permission = get_permission(
            app_label="app",
            action="add",
            code="project",
            object_type="object_type",
            field="field_name__nested_field_name",
        )
        self.assertEqual(
            permission,
            "app.add_project_object_type__field_name__nested_field_name",
        )

        # Test missing app_label
        with self.assertRaises(ValueError):
            get_permission(
                app_label="",
                action="add",
                code="project",
            )

        # Test missing action
        with self.assertRaises(ValueError):
            get_permission(
                app_label="app",
                action="",
                code="project",
            )

        # Test missing code
        with self.assertRaises(ValueError):
            get_permission(
                app_label="app",
                action="add",
                code="",
            )

        # Test missing object_type when field is provided
        with self.assertRaises(ValueError):
            get_permission(
                app_label="app",
                action="add",
                code="project",
                field="field",
            )

    def test_parse_permission(self):
        """
        Test the `parse_permission` function.
        """

        # Test project-level permissions
        permission = "app.add_project"
        app_label, action, code, object_type, field = parse_permission(permission)
        self.assertEqual(app_label, "app")
        self.assertEqual(action, "add")
        self.assertEqual(code, "project")
        self.assertEqual(object_type, "")
        self.assertEqual(field, "")

        # Test object-level permissions
        permission = "app.add_project_object_type"
        app_label, action, code, object_type, field = parse_permission(permission)
        self.assertEqual(app_label, "app")
        self.assertEqual(action, "add")
        self.assertEqual(code, "project")
        self.assertEqual(object_type, "object_type")
        self.assertEqual(field, "")

        # Test field-level permissions
        permission = "app.add_project_object_type__field"
        app_label, action, code, object_type, field = parse_permission(permission)
        self.assertEqual(app_label, "app")
        self.assertEqual(action, "add")
        self.assertEqual(code, "project")
        self.assertEqual(object_type, "object_type")
        self.assertEqual(field, "field")

        permission = "app.add_project_object_type__field_name__nested_field_name"
        app_label, action, code, object_type, field = parse_permission(permission)
        self.assertEqual(app_label, "app")
        self.assertEqual(action, "add")
        self.assertEqual(code, "project")
        self.assertEqual(object_type, "object_type")
        self.assertEqual(
            field,
            "field_name__nested_field_name",
        )

        # Test invalid permission (no app_label)
        permission = ".add_project"
        with self.assertRaises(ValueError):
            parse_permission(permission)

        # Test invalid permission (no action or code)
        permissions = ["app.action", "app.action_", "app._project"]
        for permission in permissions:
            with self.assertRaises(ValueError):
                parse_permission(permission)

        # Test invalid permission (field without object_type)
        permissions = [
            "app.add_project__field",
            "app.add_project__field_name__nested_field_name",
        ]
        for permission in permissions:
            with self.assertRaises(ValueError):
                parse_permission(permission)

    def test_strtobool(self):
        """
        Test the `strtobool` function.
        """

        # Test valid inputs
        for val in [
            "y",
            "Y",
            "yes",
            "YES",
            "t",
            "T",
            "true",
            "TRUE",
            "on",
            "ON",
            "1",
        ]:
            self.assertTrue(strtobool(val))

        for val in [
            "n",
            "N",
            "no",
            "NO",
            "f",
            "F",
            "false",
            "FALSE",
            "off",
            "OFF",
            "0",
        ]:
            self.assertFalse(strtobool(val))

        # Test invalid inputs
        with self.assertRaises(ValueError):
            strtobool("invalid")
