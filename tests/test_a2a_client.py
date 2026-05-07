import base64
import os
import unittest

from modules.a2a_client import build_message_send_payload, parse_response


def _task_with_parts(parts):
    return {
        "result": {
            "id": "task-1",
            "status": {"state": "completed"},
            "artifacts": [{"parts": parts}],
        }
    }


class ParseResponseTests(unittest.TestCase):
    def test_message_payload_includes_task_id_only_when_provided(self):
        payload = build_message_send_payload("continue", context_id="ctx-1", task_id="task-1")

        message = payload["params"]["message"]
        self.assertEqual(message["contextId"], "ctx-1")
        self.assertEqual(message["taskId"], "task-1")

        payload_without_task = build_message_send_payload("new turn", context_id="ctx-1")
        self.assertNotIn("taskId", payload_without_task["params"]["message"])

    def test_file_part_bytes_are_routed_to_files_and_images(self):
        raw = b"\x89PNG\r\n\x1a\n"
        response = _task_with_parts(
            [
                {
                    "kind": "file",
                    "file": {
                        "name": "chart.png",
                        "mimeType": "image/png",
                        "bytes": base64.b64encode(raw).decode("ascii"),
                    },
                }
            ]
        )

        parsed = parse_response(response)

        self.assertEqual(parsed["images"], [raw])
        self.assertEqual(parsed["files"][0]["name"], "chart.png")
        self.assertEqual(parsed["files"][0]["mime_type"], "image/png")
        self.assertEqual(parsed["files"][0]["data"], raw)

    def test_markdown_image_text_is_removed_when_file_artifact_exists(self):
        raw = b"\x89PNG\r\n\x1a\n"
        response = _task_with_parts(
            [
                {"text": "Sample plot created.\n\n![Sample Plot](sample.png)"},
                {
                    "kind": "file",
                    "file": {
                        "name": "sample.png",
                        "mimeType": "image/png",
                        "bytes": base64.b64encode(raw).decode("ascii"),
                    },
                },
            ]
        )

        parsed = parse_response(response)

        self.assertEqual(parsed["text"], "Sample plot created.")
        self.assertEqual(parsed["files"][0]["data"], raw)

    def test_status_message_root_wrapped_inline_data_is_parsed(self):
        html = b"<html><body>plot</body></html>"
        response = {
            "result": {
                "id": "task-2",
                "status": {
                    "state": "completed",
                    "message": {
                        "parts": [
                            {
                                "root": {
                                    "kind": "file",
                                    "inline_data": {
                                        "display_name": "plot.html",
                                        "mime_type": "text/html",
                                        "data": base64.b64encode(html).decode("ascii"),
                                    },
                                }
                            }
                        ]
                    },
                },
            }
        }

        parsed = parse_response(response)

        self.assertEqual(parsed["html"], [html.decode("utf-8")])
        self.assertEqual(parsed["files"][0]["name"], "plot.html")

    def test_data_part_file_path_reference_is_loaded_from_allowed_artifact_dir(self):
        os.makedirs("/tmp/plots", exist_ok=True)
        file_path = "/tmp/plots/a2a_client_test_chart.csv"
        raw = b"hour,units\n6,115\n"
        with open(file_path, "wb") as f:
            f.write(raw)
        self.addCleanup(lambda: os.path.exists(file_path) and os.remove(file_path))

        response = _task_with_parts(
            [
                {
                    "kind": "data",
                    "data": {
                        "name": "generate_chart",
                        "response": {
                            "status": "success",
                            "file_path": file_path,
                            "filename": "sales_chart.csv",
                        },
                    },
                }
            ]
        )

        parsed = parse_response(response)

        self.assertEqual(parsed["tables"], [raw.decode("utf-8")])
        self.assertEqual(parsed["files"][0]["name"], "sales_chart.csv")
        self.assertEqual(parsed["files"][0]["data"], raw)

    def test_data_part_data_base64_is_used_for_remote_file_path(self):
        raw = b"<html><body>remote chart</body></html>"
        response = _task_with_parts(
            [
                {
                    "kind": "data",
                    "data": {
                        "name": "generate_chart",
                        "response": {
                            "status": "success",
                            "file_path": "/root/projects/ori/amazon_manager/tmp/plots/chart.html",
                            "filename": "chart.html",
                            "mime_type": "text/html",
                            "data_base64": base64.b64encode(raw).decode("ascii"),
                        },
                    },
                }
            ]
        )

        parsed = parse_response(response)

        self.assertEqual(parsed["html"], [raw.decode("utf-8")])
        self.assertEqual(parsed["files"][0]["name"], "chart.html")
        self.assertEqual(parsed["files"][0]["data"], raw)

    def test_data_part_file_path_reference_rejects_unexpected_local_paths(self):
        response = _task_with_parts(
            [
                {
                    "kind": "data",
                    "data": {
                        "response": {
                            "file_path": "/etc/passwd",
                            "filename": "passwd.txt",
                        }
                    },
                }
            ]
        )

        parsed = parse_response(response)

        self.assertEqual(parsed["files"], [])


if __name__ == "__main__":
    unittest.main()
