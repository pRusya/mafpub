from django.test import TestCase


"""
Test

-create game bot, create superuser
-create game
-register bots
-create departure
-assign roles
-new day
-generate possible votes
-create votes
-end day
-save results for analysis

"""


class IndexViewTestCase(TestCase):
    def test_index(self):
        resp = self.client.get('/')
        self.assertEqual(resp.status_code, 200)
        print('\nContext\n', resp.context)
        print('\nTemplates\n', resp.templates)
