import unittest
from datetime import datetime
from unittest.mock import AsyncMock, MagicMock, patch
from zoneinfo import ZoneInfo

from app.services.digest_service import DailyDigest, format_digest_text
from app.services.umami_stats_service import UmamiDayStats, fetch_umami_day_stats


class DigestFormatTest(unittest.TestCase):
    def test_format_includes_core_metrics(self) -> None:
        text = format_digest_text(
            DailyDigest(
                date="2026-09-17",
                timezone="Asia/Shanghai",
                total_users=12,
                users_created_today=2,
                pageviews=42,
                visitors=9,
                visits=10,
                umami_website_id="dcc92778-4c55-4181-b006-d2085fdb1d20",
                feishu_sent=False,
            )
        )
        self.assertIn("总用户：12", text)
        self.assertIn("今日新增用户：2", text)
        self.assertIn("今日 PV：42", text)
        self.assertIn("fAjwSKOBPqy37HAd", text)


class UmamiStatsServiceTest(unittest.IsolatedAsyncioTestCase):
    async def test_fetch_umami_day_stats(self) -> None:
        share_response = MagicMock()
        share_response.raise_for_status = MagicMock()
        share_response.json.return_value = {
            "token": "share-token",
            "websiteId": "dcc92778-4c55-4181-b006-d2085fdb1d20",
        }
        stats_response = MagicMock()
        stats_response.raise_for_status = MagicMock()
        stats_response.json.return_value = {
            "pageviews": 42,
            "visitors": 9,
            "visits": 10,
        }

        client = AsyncMock()
        client.get = AsyncMock(side_effect=[share_response, stats_response])

        start = datetime(2026, 9, 17, tzinfo=ZoneInfo("Asia/Shanghai"))
        end = datetime(2026, 9, 18, tzinfo=ZoneInfo("Asia/Shanghai"))
        with patch("app.services.umami_stats_service.settings") as settings:
            settings.umami_share_base_url = "https://cloud.umami.is/analytics/us"
            settings.umami_share_slug = "fAjwSKOBPqy37HAd"
            settings.digest_http_timeout_seconds = 5.0
            result = await fetch_umami_day_stats(start=start, end=end, client=client)

        self.assertEqual(
            result,
            UmamiDayStats(
                website_id="dcc92778-4c55-4181-b006-d2085fdb1d20",
                pageviews=42,
                visitors=9,
                visits=10,
            ),
        )
        self.assertEqual(client.get.await_count, 2)
        stats_call = client.get.await_args_list[1]
        self.assertEqual(
            stats_call.kwargs["headers"]["x-umami-share-token"],
            "share-token",
        )
        self.assertEqual(stats_call.kwargs["headers"]["x-umami-share-context"], "1")


if __name__ == "__main__":
    unittest.main()
