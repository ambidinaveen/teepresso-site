from django.test import RequestFactory, TestCase

from cms.models import FAQ

from .ai import chatbot_reply


class ChatbotTests(TestCase):
    def test_intent_delivery(self):
        self.assertIn("PAN-India", chatbot_reply("how long for delivery?"))

    def test_intent_bulk(self):
        self.assertIn("quotation", chatbot_reply("I need a bulk corporate order").lower())

    def test_faq_fallback(self):
        FAQ.objects.create(question="Where is my warranty card", answer="It's in the box.")
        self.assertEqual(chatbot_reply("warranty please"), "It's in the box.")

    def test_unknown_question(self):
        self.assertIn("contact", chatbot_reply("zzzz qqqq").lower())


class RbacTests(TestCase):
    def test_dashboard_requires_staff(self):
        from django.contrib.auth import get_user_model
        User = get_user_model()
        User.objects.create_user(username="c@x.com", email="c@x.com", password="pass12345",
                                 role=User.Role.CUSTOMER)
        self.client.login(username="c@x.com", password="pass12345")
        r = self.client.get("/dashboard/")
        self.assertEqual(r.status_code, 403)
