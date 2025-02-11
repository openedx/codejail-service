"""Test core.views."""

from unittest.mock import patch

import ddt
from django.test import TestCase
from django.urls import reverse


@ddt.ddt
class HealthTests(TestCase):
    """Tests of the health endpoint."""

    @ddt.data(False, None, "garbage")
    def test_unhealthy(self, safety_state):
        """Test that the endpoint reports error when safety checks failed or haven't run."""
        with patch('codejail_service.startup_check.STARTUP_SAFETY_CHECK_OK', safety_state):
            response = self.client.get(reverse('health'))

        self.assertEqual(response.status_code, 503)
        self.assertEqual(response['content-type'], 'application/json')

        expected_data = {
            'status': 'UNAVAILABLE'
        }

        self.assertJSONEqual(response.content, expected_data)

    def test_healthy(self):
        """Test that the endpoint reports OK when all services are healthy."""
        with patch('codejail_service.startup_check.STARTUP_SAFETY_CHECK_OK', True):
            response = self.client.get(reverse('health'))

        self.assertEqual(response.status_code, 200)
        self.assertEqual(response['content-type'], 'application/json')

        expected_data = {
            'status': 'OK'
        }

        self.assertJSONEqual(response.content, expected_data)
