import unittest

from x_listcopy import (
    extract_users_from_timeline,
    filter_new_members,
    is_list_response_decode_error,
    parse_list_reference,
)


class ParseListReferenceTest(unittest.TestCase):
    def test_numeric_id(self):
        ref = parse_list_reference("123456")
        self.assertEqual(ref.kind, "id")
        self.assertEqual(ref.list_id, "123456")

    def test_x_list_url(self):
        ref = parse_list_reference("https://x.com/i/lists/987654?s=20")
        self.assertEqual(ref.kind, "id")
        self.assertEqual(ref.list_id, "987654")

    def test_owner_slug_url(self):
        ref = parse_list_reference("https://twitter.com/example/lists/builders")
        self.assertEqual(ref.kind, "slug")
        self.assertEqual(ref.owner_screen_name, "example")
        self.assertEqual(ref.slug, "builders")

    def test_owner_slug_shorthand(self):
        ref = parse_list_reference("example/builders")
        self.assertEqual(ref.kind, "slug")
        self.assertEqual(ref.owner_screen_name, "example")
        self.assertEqual(ref.slug, "builders")


class TimelineExtractionTest(unittest.TestCase):
    def test_extracts_unique_users_and_bottom_cursor(self):
        timeline = {
            "instructions": [
                {
                    "type": "TimelineAddEntries",
                    "entries": [
                        {
                            "entryId": "user-1",
                            "content": {
                                "itemContent": {
                                    "user_results": {
                                        "result": {
                                            "rest_id": "1",
                                            "legacy": {"screen_name": "alice"},
                                        }
                                    }
                                }
                            },
                        },
                        {
                            "entryId": "user-1-duplicate",
                            "content": {
                                "itemContent": {
                                    "user_results": {
                                        "result": {
                                            "rest_id": "1",
                                            "legacy": {"screen_name": "alice"},
                                        }
                                    }
                                }
                            },
                        },
                        {
                            "entryId": "cursor-bottom-0",
                            "content": {
                                "cursorType": "Bottom",
                                "value": "cursor-next",
                            },
                        },
                    ],
                }
            ]
        }

        users, cursor = extract_users_from_timeline(timeline)

        self.assertEqual(users, [{"id": "1", "screen_name": "alice"}])
        self.assertEqual(cursor, "cursor-next")


class FilterNewMembersTest(unittest.TestCase):
    def test_skips_members_already_in_destination(self):
        source = [
            {"id": "1", "screen_name": "alice"},
            {"id": "2", "screen_name": "bob"},
        ]
        destination = [{"id": "1", "screen_name": "alice"}]

        self.assertEqual(
            filter_new_members(source, destination),
            [{"id": "2", "screen_name": "bob"}],
        )


class ListResponseDecodeErrorTest(unittest.TestCase):
    def test_matches_known_x_list_response_decode_error(self):
        error = (
            'X GraphQL error: [{"code": 214, "message": '
            '"BadRequest: com.twitter.strato.serialization.DecodeException", '
            '"path": ["list", "default_banner_media_results", "result"]}]'
        )

        self.assertTrue(is_list_response_decode_error(error))


if __name__ == "__main__":
    unittest.main()
