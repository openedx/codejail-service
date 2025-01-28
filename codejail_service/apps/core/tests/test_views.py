"""Test core.views."""

from django.test import TestCase
from django.urls import reverse


class HealthTests(TestCase):
    """Tests of the health endpoint."""

    def test_healthcheck(self):
        """Test that the endpoint reports when all services are healthy."""
        response = self.client.get(reverse('health'))
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response['content-type'], 'application/json')

        expected_data = {
            'status': 'OK'
        }

        self.assertJSONEqual(response.content, expected_data)
