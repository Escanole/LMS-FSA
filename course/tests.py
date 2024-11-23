from django.test import TestCase
from django.urls import reverse
from django.contrib.messages import get_messages
from .models import Topic, Tag
from course.forms import TopicForm


class TopicTagListViewTest(TestCase):

    def setUp(self):
        # Tạo các đối tượng giả để kiểm tra
        self.topic1 = Topic.objects.create(name="Topic 1")
        self.topic2 = Topic.objects.create(name="Topic 2")
        self.tag1 = Tag.objects.create(name="Tag 1", topic=self.topic1)
        self.tag2 = Tag.objects.create(name="Tag 2", topic=self.topic2)

    def test_topic_tag_list_view_status_code(self):
        # Kiểm tra response trả về có thành công (200 OK)
        response = self.client.get(reverse('course:topic_tag_list'))
        self.assertEqual(response.status_code, 200)

    def test_topic_tag_list_context_data(self):
        # Kiểm tra context chứa đủ dữ liệu
        response = self.client.get(reverse('course:topic_tag_list'))
        self.assertIn('topics', response.context)
        self.assertIn('tags', response.context)

        # Kiểm tra dữ liệu trong context
        self.assertQuerysetEqual(
        response.context['topics'].order_by('id'),  # Sắp xếp theo 'id'
        Topic.objects.all().order_by('id'),        # Sắp xếp theo 'id'
        transform=lambda x: x,  # Không biến đổi giá trị
        )
        self.assertQuerysetEqual(
            response.context['tags'].order_by('id'),
            Tag.objects.all().order_by('id'),
            transform=lambda x: x,
        )

    def test_topic_tag_list_template_used(self):
        # Kiểm tra template được sử dụng
        response = self.client.get(reverse('course:topic_tag_list'))
        self.assertTemplateUsed(response, 'topic-tag/topic_tag_list.html')

    def test_topic_tag_list_rendered_content(self):
        # Kiểm tra nội dung được render
        response = self.client.get(reverse('course:topic_tag_list'))
        self.assertContains(response, "Manage Topics and Tags")  # Tiêu đề trên giao diện
        self.assertContains(response, self.topic1.name)          # Tên topic
        self.assertContains(response, self.tag1.name)            # Tên tag

class TopicAddViewTest(TestCase):
    def test_topic_add_get_request(self):
        """
        Test GET request to topic_add view renders the correct template and includes the form.
        """
        response = self.client.get(reverse('course:topic_add'))
        self.assertEqual(response.status_code, 200)
        self.assertTemplateUsed(response, 'topic-tag/topic_form.html')
        self.assertIn('topic_form', response.context)

    def test_topic_add_post_request_success(self):
        """
        Test POST request with valid topic names creates new topics and redirects to topic_tag_list.
        """
        topic_names = ['Topic A', 'Topic B', 'Topic C']
        response = self.client.post(reverse('course:topic_add'), {
            'topics[]': topic_names,
        })

        # Check redirection
        self.assertRedirects(response, reverse('course:topic_tag_list'))

        # Check success message
        messages = list(get_messages(response.wsgi_request))
        self.assertTrue(any('Topics added successfully.' in str(m) for m in messages))

        # Check topics created
        self.assertEqual(Topic.objects.count(), len(topic_names))
        for name in topic_names:
            self.assertTrue(Topic.objects.filter(name=name).exists())

    def test_topic_add_post_request_empty(self):
        """
        Test POST request with empty topic names displays an error message.
        """
        response = self.client.post(reverse('course:topic_add'), {
            'topics[]': []  # Empty input
        })

        # Check status code
        self.assertEqual(response.status_code,302 )

        # Kiểm tra nếu nó chuyển hướng tới đúng URL (topic_tag_list)
        self.assertRedirects(response, reverse('course:topic_tag_list'))

        # Check error message
        messages = list(get_messages(response.wsgi_request))
        self.assertEqual(str(messages[0]), 'Please enter at least one topic name.')

        # Check no topics created
        self.assertEqual(Topic.objects.count(), 0)

    def test_topic_add_post_request_strip_whitespace(self):
        """
        Test POST request with topic names containing leading/trailing whitespace.
        """
        topic_names = ['   Topic D  ', 'Topic E   ', '   Topic F']
        expected_names = [name.strip() for name in topic_names]

        response = self.client.post(reverse('course:topic_add'), {
            'topics[]': topic_names,
        })

        # Check redirection
        self.assertRedirects(response, reverse('course:topic_tag_list'))

        # Check topics created with stripped names
        self.assertEqual(Topic.objects.count(), len(expected_names))
        for name in expected_names:
            self.assertTrue(Topic.objects.filter(name=name).exists())

class TopicDeleteViewTest(TestCase):

    def setUp(self):
        # Tạo một topic để test
        self.topic = Topic.objects.create(name="Test Topic")
        self.delete_url = reverse('course:topic_delete', args=[self.topic.pk])

    def test_topic_delete_post_request(self):
        """
        Test case: Submit a POST request to delete a topic.
        """
        # Gửi yêu cầu POST để xóa topic
        response = self.client.post(self.delete_url)
        
        # Kiểm tra nếu topic đã bị xóa khỏi cơ sở dữ liệu
        self.assertFalse(Topic.objects.filter(pk=self.topic.pk).exists())
        
        # Kiểm tra nếu thông báo thành công được tạo ra
        messages = list(get_messages(response.wsgi_request))
        self.assertEqual(len(messages), 1)
        self.assertEqual(str(messages[0]), "Topic deleted successfully.")
        
        # Kiểm tra nếu người dùng được chuyển hướng về topic_tag_list
        self.assertRedirects(response, reverse('course:topic_tag_list'))

    def test_topic_delete_get_request(self):
        """
        Test case: Submit a GET request to display the delete confirmation page.
        """
        # Gửi yêu cầu GET để hiển thị trang xác nhận xóa
        response = self.client.get(self.delete_url)

        # Kiểm tra mã trạng thái trả về là 200
        self.assertEqual(response.status_code, 200)
        
        # Kiểm tra nội dung trang có chứa thông tin về topic
        self.assertContains(response, "Delete Topic")
        self.assertContains(response, "Test Topic")

class TopicEditViewTest(TestCase):

    def setUp(self):
        # Tạo một topic để test
        self.topic = Topic.objects.create(name="Initial Topic Name")
        self.edit_url = reverse('course:topic_edit', args=[self.topic.pk])

    def test_topic_edit_get_request(self):
        """
        Test case: Submit a GET request to display the edit form.
        """
        response = self.client.get(self.edit_url)
        
        # Kiểm tra mã trạng thái trả về là 200
        self.assertEqual(response.status_code, 200)
        
        # Kiểm tra form được hiển thị với dữ liệu topic hiện tại
        self.assertContains(response, "Edit Topic")
        self.assertContains(response, self.topic.name)

    def test_topic_edit_post_request_success(self):
        """
        Test case: Submit a valid POST request to edit a topic successfully.
        """
        new_data = {'name': "Updated Topic Name"}
        response = self.client.post(self.edit_url, new_data)

        # Cập nhật dữ liệu trong database
        self.topic.refresh_from_db()
        self.assertEqual(self.topic.name, new_data['name'])
        
        # Kiểm tra thông báo thành công
        messages = list(get_messages(response.wsgi_request))
        self.assertEqual(len(messages), 1)
        self.assertEqual(str(messages[0]), "Topic updated successfully.")
        
        # Kiểm tra việc chuyển hướng về topic_tag_list
        self.assertRedirects(response, reverse('course:topic_tag_list'))

    def test_topic_edit_post_request_failure(self):
        """
        Test case: Submit an invalid POST request to edit a topic (e.g., empty name).
        """
        invalid_data = {'name': ""}
        response = self.client.post(self.edit_url, invalid_data)

        # Kiểm tra topic không bị thay đổi trong database
        self.topic.refresh_from_db()
        self.assertNotEqual(self.topic.name, invalid_data['name'])
        self.assertEqual(self.topic.name, "Initial Topic Name")
        
        # Kiểm tra thông báo lỗi
        messages = list(get_messages(response.wsgi_request))
        self.assertEqual(len(messages), 1)
        self.assertEqual(str(messages[0]), "There was an error updating the topic.")
        
        # Kiểm tra mã trạng thái trả về là 200 để hiển thị lại form
        self.assertEqual(response.status_code, 200)

        # Kiểm tra nếu form hiển thị lại với lỗi
        self.assertContains(response, "Edit Topic")

class TagAddViewTest(TestCase):
    @classmethod
    def setUpTestData(cls):
        cls.topic1 = Topic.objects.create(name="Topic 1")
        cls.topic2 = Topic.objects.create(name="Topic 2")
        cls.tag_add_url = reverse('course:tag_add')

    def test_tag_add_get_request(self):
        """
        Test case: Access the tag_add view with a GET request.
        """
        response = self.client.get(self.tag_add_url)
        self.assertEqual(response.status_code, 200)
        self.assertTemplateUsed(response, 'topic-tag/tag_form.html')
        self.assertContains(response, "Add Tags")
        topics_in_context = list(response.context['topics'])
        topics_in_db = list(Topic.objects.all())
        self.assertEqual(topics_in_context, topics_in_db)

    def test_tag_add_post_request_success(self):
        """
        Test case: Submit a valid POST request to add tags.
        """
        data = {
            'tags[]': ['Tag 1', 'Tag 2'],
            'topics[]': [self.topic1.id, self.topic2.id],
        }
        response = self.client.post(self.tag_add_url, data)

        # Kiểm tra redirect
        self.assertEqual(response.status_code, 302)
        self.assertRedirects(response, reverse('course:topic_tag_list'))

        # Kiểm tra thông báo thành công
        messages = list(get_messages(response.wsgi_request))
        self.assertEqual(len(messages), 1)
        self.assertIn('Tags added successfully.', str(messages[0]))

        # Kiểm tra dữ liệu trong database
        self.assertEqual(Tag.objects.count(), 2)
        self.assertTrue(Tag.objects.filter(name='Tag 1', topic=self.topic1).exists())
        self.assertTrue(Tag.objects.filter(name='Tag 2', topic=self.topic2).exists())

    def test_tag_add_post_request_missing_data(self):
        response = self.client.post(reverse('course:tag_add'), data={
            'tags[]': [''],  # Dữ liệu thiếu (empty tag)
            'topics[]': ['']  # Dữ liệu thiếu (empty topic)
        })

        
        # Kiểm tra thông báo được tạo ra
        messages = list(get_messages(response.wsgi_request))
        self.assertTrue(any("Tags added successfully." in str(message) for message in messages))
    def test_tag_add_post_request_no_data(self):
        response = self.client.post(reverse('course:tag_add'), data={})  # POST request không có dữ liệu

        # Kiểm tra status code
        self.assertEqual(response.status_code, 200)  # Không redirect khi dữ liệu không hợp lệ
        
        # Kiểm tra rằng template đã render đúng
        self.assertTemplateUsed(response, 'topic-tag/tag_form.html')

        # Kiểm tra thông báo lỗi
        messages = list(get_messages(response.wsgi_request))
        self.assertTrue(
            any("Please enter at least one tag name and select a topic for each tag." in str(message) for message in messages),
            "Expected error message not found in response."
        )

class TagEditViewTest(TestCase):
    def setUp(self):
        # Tạo dữ liệu test
        self.topic = Topic.objects.create(name="Sample Topic")
        self.tag = Tag.objects.create(name="Sample Tag", topic=self.topic)
        self.url = reverse('course:tag_edit', kwargs={'pk': self.tag.pk})

    def test_tag_edit_get_request(self):
        """Test case: Access the tag_edit view with a GET request."""
        response = self.client.get(self.url)

        # Kiểm tra status code
        self.assertEqual(response.status_code, 200)

        # Kiểm tra rằng đúng template được render
        self.assertTemplateUsed(response, 'topic-tag/tag_edit.html')

        # Kiểm tra dữ liệu trong context
        self.assertIn('form', response.context)
        self.assertIn('topics', response.context)
        self.assertEqual(len(response.context['topics']), 1)
        self.assertEqual(response.context['topics'][0], self.topic)

    def test_tag_edit_post_request_success(self):
        """Test case: Submit a valid POST request to edit a tag."""
        new_data = {
            'name': 'Updated Tag Name',
            'topic': self.topic.pk  # Sử dụng topic hiện tại
        }
        response = self.client.post(self.url, data=new_data)

        # Kiểm tra redirect
        self.assertRedirects(response, reverse('course:topic_tag_list'))

        # Kiểm tra tag đã được cập nhật
        self.tag.refresh_from_db()
        self.assertEqual(self.tag.name, 'Updated Tag Name')

        # Kiểm tra thông báo thành công
        messages = list(get_messages(response.wsgi_request))
        self.assertTrue(
            any("Tag updated successfully." in str(message) for message in messages),
            "Expected success message not found in response."
        )

    def test_tag_edit_post_request_failure(self):
        """Test case: Submit an invalid POST request to edit a tag (e.g., empty name)."""
        new_data = {
            'name': '',  # Invalid data (empty name)
            'topic': self.topic.pk
        }
        response = self.client.post(self.url, data=new_data)

        # Kiểm tra status code (không redirect)
        self.assertEqual(response.status_code, 200)

        # Kiểm tra rằng template đã được render lại
        self.assertTemplateUsed(response, 'topic-tag/tag_edit.html')

        # Kiểm tra rằng tag không được cập nhật
        self.tag.refresh_from_db()
        self.assertNotEqual(self.tag.name, '')  # Name không thay đổi

        # Kiểm tra lỗi trong form
        self.assertIn('This field is required.', str(response.context['form'].errors))

class TagDeleteViewTest(TestCase):
    def setUp(self):
        # Tạo một Topic và một Tag để thử nghiệm
        self.topic = Topic.objects.create(name="Sample Topic")
        self.tag = Tag.objects.create(name="Sample Tag", topic=self.topic)
        self.url = reverse('course:tag_delete', kwargs={'pk': self.tag.pk})

    def test_tag_delete_get_request(self):
        """Test case: Access the tag_delete view with a GET request."""
        response = self.client.get(self.url)
        
        # Kiểm tra status code
        self.assertEqual(response.status_code, 200)

        # Kiểm tra template được sử dụng
        self.assertTemplateUsed(response, 'topic-tag/tag_confirm_delete.html')

        # Kiểm tra context
        self.assertEqual(response.context['object'], self.tag)
        self.assertEqual(response.context['title'], 'Delete Tag')

    def test_tag_delete_post_request_success(self):
        """Test case: Submit a POST request to delete a tag."""
        response = self.client.post(self.url)
        
        # Kiểm tra redirect sau khi xóa thành công
        self.assertRedirects(response, reverse('course:topic_tag_list'))

        # Kiểm tra thông báo thành công
        messages = list(get_messages(response.wsgi_request))
        self.assertTrue(
            any("Tag deleted successfully." in str(message) for message in messages),
            "Expected success message not found in response."
        )

        # Kiểm tra tag đã bị xóa
        with self.assertRaises(Tag.DoesNotExist):
            Tag.objects.get(pk=self.tag.pk)

    def test_tag_delete_post_request_nonexistent_tag(self):
        """Test case: Attempt to delete a non-existent tag."""
        invalid_url = reverse('course:tag_delete', kwargs={'pk': 999})  # ID không tồn tại
        response = self.client.post(invalid_url)
        
        # Kiểm tra rằng không tìm thấy tag sẽ trả về 404
        self.assertEqual(response.status_code, 404)
