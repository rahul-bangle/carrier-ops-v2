import unittest

from cli.resolve_targets import (
    extract_api_urls,
    normalize_api_url,
    parse_jobs,
    provider_for_url,
)


class ResolveTargetsTests(unittest.TestCase):
    def test_extracts_greenhouse_api_from_next_chunk(self):
        text = (
            'fetch("https://boards-api.greenhouse.io/v1/boards/'
            'razorpaysoftwareprivatelimited/jobs?content=true")'
        )

        self.assertEqual(
            extract_api_urls(text),
            [
                "https://boards-api.greenhouse.io/v1/boards/"
                "razorpaysoftwareprivatelimited/jobs?content=true"
            ],
        )

    def test_normalizes_greenhouse_board_url_to_jobs_endpoint(self):
        self.assertEqual(
            normalize_api_url(
                "https://boards-api.greenhouse.io/v1/boards/"
                "razorpaysoftwareprivatelimited"
            ),
            "https://boards-api.greenhouse.io/v1/boards/"
            "razorpaysoftwareprivatelimited/jobs?content=true",
        )

    def test_parses_greenhouse_jobs(self):
        payload = {
            "jobs": [
                {
                    "title": "Product Manager II",
                    "absolute_url": "https://job-boards.greenhouse.io/x/jobs/1",
                    "location": {"name": "Bengaluru"},
                }
            ]
        }

        jobs = parse_jobs("greenhouse", payload, "Razorpay")

        self.assertEqual(len(jobs), 1)
        self.assertEqual(jobs[0]["title"], "Product Manager II")
        self.assertEqual(jobs[0]["location"], "Bengaluru")

    def test_detects_provider(self):
        self.assertEqual(
            provider_for_url("https://api.ashbyhq.com/posting-api/job-board/foo"),
            "ashby",
        )
        self.assertEqual(
            provider_for_url("https://api.lever.co/v0/postings/foo"), "lever"
        )
        self.assertEqual(
            provider_for_url("https://boards-api.greenhouse.io/v1/boards/foo/jobs"),
            "greenhouse",
        )


if __name__ == "__main__":
    unittest.main()
