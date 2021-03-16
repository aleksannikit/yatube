from django.test import Client, TestCase
from django.shortcuts import reverse
from .models import User, Post


class ProfileTest(TestCase):
    def setUp(self):
        self.client = Client()

    def test_profile_after_registration(self):
        registration_data = {"first_name": "Ivan",
                             "last_name": "Ivanov",
                             "username": "ivanov",
                             "email": "ivan@ivanov.com",
                             "password1": "!QAZ2wsx#EDC4rfv",
                             "password2": "!QAZ2wsx#EDC4rfv"}

        response = self.client.post(reverse("signup"), data=registration_data)
        self.assertIn(response.status_code, (301, 302))

        response = self.client.get(reverse("profile", kwargs={"username": registration_data.get("username")}))
        self.assertEqual(response.status_code, 200)

    def test_anon_try_publish_redirect(self):
        response = self.client.post(reverse("new_post"), data={"text": "Lorem ipsum"})
        self.assertIn(response.status_code, (301, 302))
        self.assertIn(reverse("login"), response.url)
        self.assertRedirects(response, '/auth/login/?next=/new/', status_code=302)


class PublishTest(TestCase):

    def setUp(self):
        self.client = Client()
        # create user
        self.new_user = User.objects.create_user(username="petr",
                                                 email="petr@petrov.com",
                                                 password="12345")
        # login
        self.client.force_login(self.new_user)

        # publish
        self.post_text = "Lorem ipsum"
        self.create_post_response = self.client.post(reverse("new_post"), data={"text": self.post_text, "group": ""})
        self.new_post = Post.objects.first()

    def test_logged_user_can_publish(self):
        self.assertIn(self.create_post_response.status_code, (301, 302))
        self.assertEqual(self.create_post_response.url, reverse("index"))
        self.assertEqual(self.new_post.text, self.post_text)

    def check_all_pages(self, post_text):
        response = self.client.get(reverse("index"))
        self.assertContains(response, post_text)

        response = self.client.get(reverse("profile", kwargs={"username": self.new_user.username}))
        self.assertContains(response, post_text)

        response = self.client.get(
            reverse("post", kwargs={"username": self.new_user.username, "post_id": self.new_post.id}))
        self.assertContains(response, post_text)

    def test_publish_all_pages(self):
        self.check_all_pages(self.post_text)

    def test_edit_post(self):
        edited_text = "Lorem ipsum edited"
        response = self.client.post(
            reverse("post_edit", kwargs={"username": self.new_user.username, "post_id": self.new_post.id}),
            data={"text": edited_text})
        self.assertRedirects(response,
                             reverse("post", kwargs={"username": self.new_user.username, "post_id": self.new_post.id}))

        self.check_all_pages(edited_text)
