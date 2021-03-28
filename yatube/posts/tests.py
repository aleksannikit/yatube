from django.test import Client, TestCase
from django.shortcuts import reverse
from .models import User, Post, Follow
from django.core.cache import cache


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
        cache.clear()
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


class ImageTest(TestCase):
    def setUp(self):
        self.client = Client()
        # create user
        self.new_user = User.objects.create_user(username="petr",
                                                 email="petr@petrov.com",
                                                 password="12345")
        # login
        self.client.force_login(self.new_user)

    def test_current_post_image_contains(self):
        # publish
        with open('posts/image.jpg', 'rb') as img:
            self.create_post_response = self.client.post(reverse("new_post"),
                                                         data={"text": "Lorem ipsum", "group": "", "image": img})
        self.new_post = Post.objects.first()
        PublishTest.check_all_pages(self, post_text='<img')

    def test_not_image_forbidden(self):
        with open('posts/non_graphic.txt', 'rb') as txt:
            self.create_post_response = self.client.post(reverse("new_post"),
                                                         data={"text": "Lorem ipsum", "group": "", "image": txt})

        self.assertContains(self.create_post_response, '<div class="alert alert-danger" role="alert">')


class CacheTest(TestCase):
    def setUp(self):
        self.client = Client()
        # create user
        self.new_user = User.objects.create_user(username="petr",
                                                 email="petr@petrov.com",
                                                 password="12345")
        # login
        self.client.force_login(self.new_user)

    def test_cache(self):
        response = self.client.get(reverse('index'))

        # publish
        self.post_text = "Lorem ipsum"
        self.create_post_response = self.client.post(reverse("new_post"), data={"text": self.post_text, "group": ""})
        self.new_post = Post.objects.first()

        self.assertNotContains(response, self.post_text)

        cache.clear()
        response = self.client.get(reverse('index'))
        self.assertContains(response, self.post_text)


class CommentTest(TestCase):
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

    def test_only_auth_may_comment(self):
        self.commentator = Client()
        # create user
        self.new_commentator = User.objects.create_user(username="ivan",
                                                        email="ivan@ivanov.com",
                                                        password="12345")
        # login
        self.commentator.force_login(self.new_commentator)
        comment_text = "TestComment"
        self.commentator.post(
            reverse("add_comment", kwargs={'username': self.new_user.username, "post_id": self.new_post.id}),
            data={'text': comment_text})
        response = self.commentator.get(
            reverse("post", kwargs={'username': self.new_user.username, "post_id": self.new_post.id}))
        self.assertContains(response, comment_text)

        # anon
        self.anon = Client()
        response = self.anon.post(
            reverse("add_comment", kwargs={'username': self.new_user.username, "post_id": self.new_post.id}),
            data={'text': "anonComment"})
        self.assertIn(response.status_code, (301, 302))
        self.assertIn(reverse("login"), response.url)
        self.assertRedirects(response, '/auth/login/?next='
                             + reverse("add_comment", kwargs={'username': self.new_user.username,
                                                              "post_id": self.new_post.id}),
                             status_code=302)


class FollowTest(TestCase):
    def setUp(self):
        self.client = Client()
        # create user
        self.new_user = User.objects.create_user(username="petr",
                                                 email="petr@petrov.com",
                                                 password="12345")
        # login
        self.client.force_login(self.new_user)

        self.follower = Client()
        # create user
        self.new_follower = User.objects.create_user(username="ivan",
                                                     email="ivan@ivanov.com",
                                                     password="12345")
        # login
        self.follower.force_login(self.new_follower)
        self.follower.post(reverse("profile_follow", kwargs={"username": self.new_user.username}))

    def test_auth_can_follow(self):
        f = Follow.objects.filter(user=self.new_follower, author=self.new_user)
        self.assertNotEqual(len(f), 0)
        # unfollow
        self.follower.post(reverse("profile_unfollow", kwargs={"username": self.new_user.username}))
        f = Follow.objects.filter(user=self.new_follower, author=self.new_user)
        self.assertEqual(len(f), 0)

    def test_new_post_follow(self):
        # publish
        self.post_text = "Lorem ipsum"
        self.create_post_response = self.client.post(reverse("new_post"), data={"text": self.post_text, "group": ""})
        self.new_post = Post.objects.first()

        response = self.follower.get(reverse("follow_index"))
        self.assertContains(response, self.post_text)

        not_follower = Client()
        self.not_folower_user = User.objects.create_user(username="dm",
                                                         email="dm@petrov.com",
                                                         password="12345")
        not_follower.force_login(self.not_folower_user)
        response = not_follower.get(reverse("follow_index"))
        self.assertNotContains(response, self.post_text)


class NotFoundTest(TestCase):
    def test_404(self):
        c = Client()
        response = c.get("/notfound404error/")
        self.assertEqual(response.status_code, 404)
