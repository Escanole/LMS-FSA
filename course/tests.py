from django.test import TestCase
from django.contrib.auth import get_user_model
from datetime import timedelta
from django.db import IntegrityError
from django.urls import reverse
from django.utils import timezone
from django.contrib.messages import get_messages
from django.http import HttpRequest
from django.urls import reverse
from django.utils import timezone
from django.contrib import messages
from .models import Course, Enrollment, Completion, SessionCompletion, UserCourseProgress, Transaction, Session, Tag, Topic, ReadingMaterial, CourseMaterial
from django.contrib import messages
from django.core.files.uploadedfile import SimpleUploadedFile
from django.core.files.storage import default_storage

class CourseDeleteTestCase(TestCase):

    def setUp(self):
        # Create a user for authentication
        User = get_user_model()
        self.user = User.objects.create_user(username='testuser', password='password123')
        
        # Create a course and associated sessions
        self.course = Course.objects.create(
            course_name='Test Course',
            course_code='TC101',
            price=100,
            discount=10,
        )
        
        # Create associated sessions for this course
        self.session1 = Session.objects.create(course=self.course, name="Session 1", order=1)
        self.session2 = Session.objects.create(course=self.course, name="Session 2", order=2)

        # URL for course deletion (with the course primary key)
        self.url = reverse('course:course_delete', args=[self.course.pk])

        # Log in the user
        self.client.login(username='testuser', password='password123')

    def test_course_delete(self):
        # Ensure the course and its sessions exist before deletion
        self.assertTrue(Course.objects.filter(pk=self.course.pk).exists())
        self.assertTrue(Session.objects.filter(course=self.course).count(), 2)

        # Send a POST request to delete the course
        response = self.client.post(self.url)

        # Ensure the course is deleted from the database
        self.assertFalse(Course.objects.filter(pk=self.course.pk).exists())

        # Ensure the sessions associated with the course are also deleted
        self.assertFalse(Session.objects.filter(course=self.course).exists())

        # Ensure the response redirects to the course list
        self.assertRedirects(response, reverse('course:course_list'))

class CourseAddTestCase(TestCase):

    def setUp(self):
        # Create a user for authentication
        User = get_user_model()
        self.user = User.objects.create_user(username='testuser', password='password123')
        
        # URL for course creation
        self.url = reverse('course:course_add')
        
        # Log in the user
        self.client.login(username='testuser', password='password123')

    def test_course_add_no_prerequisite(self):
        # Prepare form data to add a course
        data = {
            'course_name': 'Test Course',
            'course_code': 'TC101',
            'price': 100,
            'discount': 10,
        }
        
        # Send a POST request with the form data
        response = self.client.post(self.url, data)

        # Check if the course was created and saved
        course = Course.objects.filter(course_code='TC101').first()
        self.assertIsNotNone(course)
        self.assertEqual(course.course_name, 'Test Course')
        self.assertEqual(course.course_code, 'TC101')
        self.assertEqual(course.price, 100)
        self.assertEqual(course.discount, 10)

        # Check the success message
        storage = get_messages(response.wsgi_request)
        messages = [message.message for message in storage]
        self.assertIn('Course and sessions created successfully.', messages)

        # Ensure the redirect after successful creation
        self.assertRedirects(response, reverse('course:course_list'))

    def test_course_add_with_prerequisite(self):
        # Create prerequisite courses
        prerequisite1 = Course.objects.create(course_name='Prerequisite 1', course_code='PRQ101', price=50, discount=5)
        prerequisite2 = Course.objects.create(course_name='Prerequisite 2', course_code='PRQ102', price=60, discount=10)

        # Prepare form data to add a course with prerequisites
        data = {
            'course_name': 'Test Course with Prerequisites',
            'course_code': 'TC102',
            'price': 100,
            'discount': 10,
            'prerequisite_courses[]': [prerequisite1.id, prerequisite2.id],  # Add the prerequisite courses
        }
        
        # Send a POST request with the form data
        response = self.client.post(self.url, data)

        # Check if the course was created and saved
        course = Course.objects.filter(course_code='TC102').first()
        self.assertIsNotNone(course)
        self.assertEqual(course.course_name, 'Test Course with Prerequisites')
        self.assertEqual(course.course_code, 'TC102')
        self.assertEqual(course.price, 100)
        self.assertEqual(course.discount, 10)

        # Verify that the prerequisites are correctly associated with the course
        self.assertEqual(course.prerequisites.count(), 2)
        self.assertIn(prerequisite1, course.prerequisites.all())
        self.assertIn(prerequisite2, course.prerequisites.all())

        # Check the success message
        storage = get_messages(response.wsgi_request)
        messages = [message.message for message in storage]
        self.assertIn('Course and sessions created successfully.', messages)

        # Ensure the redirect after successful creation
        self.assertRedirects(response, reverse('course:course_list'))


    def test_course_add_duplicate_course_code(self):

        # Trying to create another course with the same code
        data2 = {
            'course_name': 'Test Course',
            'course_code': 'TC101',
            'price': 100,
            'discount': 10,
        }
               
        response2 = self.client.post(self.url, data2)

        # Check if the course was not created due to duplicate code
        course_count = Course.objects.filter(course_code='TC101').count()
        self.assertEqual(course_count, 1)  # Only one course should exist with that code

class CourseEditDetailTestCase(TestCase):

    def setUp(self):
        # Create a user to associate with the course
        User = get_user_model()
        self.user = User.objects.create_user(username='testuser', password='password')

        # Create prerequisite course
        self.prerequisite_course = Course.objects.create(
            course_name='Prerequisite Course',
            course_code='CS100',
            description='A prerequisite course',
            creator=self.user,
            instructor=self.user,
            price=50.0
        )

        # Create the main course with the prerequisite
        self.course = Course.objects.create(
            course_name='Original Course Name',
            course_code='CS101',
            description='Original description',
            creator=self.user,
            instructor=self.user,
            price=100.0
        )

        # Add prerequisite to the course
        self.course.prerequisites.add(self.prerequisite_course)

        # URL for editing the course (assuming the name of the view is 'course_edit_detail')
        self.url = reverse('course:course_edit_detail', kwargs={'pk': self.course.pk})

    def test_edit_course_and_prerequisites(self):
        # Log in the user
        self.client.login(username='testuser', password='password')

        new_prerequisite_course = Course.objects.create(
            course_name='New Prerequisite Course',
            course_code='CS103',
            description='Another prerequisite course',
            creator=self.user,
            instructor=self.user,
            price=60.0
        )

        updated_data = {
            'course_name': 'Updated Course Name',
            'course_code': 'CS102',
            'description': 'Updated description',
            'price': 150.0,
            'prerequisite_courses': [str(new_prerequisite_course.id)],  # Add new prerequisite
            'deleted_prerequisite_ids': [str(self.prerequisite_course.id)],  # Remove old prerequisite
            'discount': 10,
        }

        # Send POST request to update the course
        response = self.client.post(self.url, updated_data)

        # Refresh the course from the database
        self.course.refresh_from_db()

        # Check if the course details were updated
        self.assertEqual(self.course.course_name, 'Updated Course Name')
        self.assertEqual(self.course.course_code, 'CS102')
        self.assertEqual(self.course.description, 'Updated description')
        self.assertEqual(self.course.price, 150.0)

        # Check if the prerequisite has been removed
        self.assertNotIn(self.prerequisite_course, self.course.prerequisites.all())

        # Check if the new prerequisite has been added
        self.assertIn(new_prerequisite_course, self.course.prerequisites.all())

        # Check if the response redirects (this means the update was successful)
        self.assertRedirects(response, self.url)  # Should redirect to the same course edit page
        
    def test_upload_and_replace_image(self):
        self.client.login(username='testuser', password='password')
        
        # Simulate uploading an initial image
        initial_image = SimpleUploadedFile('initial_image.jpg', b'file_content', content_type='image/jpeg')
        self.course.image = initial_image
        self.course.save()
        # Check if the initial image exists
        self.assertTrue(default_storage.exists(self.course.image.path))
        # Now upload a new image to replace the old one
        new_image = SimpleUploadedFile('new_image.jpg', b'new_file_content', content_type='image/jpeg')
        # Prepare the form data, including the new image
        updated_data = {
            'course_name': 'Updated Course Name',
            'course_code': 'CS102',
            'description': 'Updated description',
            'prerequisite_courses': [],  # Add new prerequisite
            'deleted_prerequisite_ids': [],  # Remove old prerequisite
            'price': 150.0,
            'image': new_image, 
            'discount': 0 # New image to upload
        }
        # Send POST request to update the course with the new image
        response = self.client.post(self.url, updated_data)
        # Refresh the course from the database
        self.course.refresh_from_db()
        # Check if the course details were updated
        self.assertEqual(self.course.course_name, 'Updated Course Name')
        self.assertEqual(self.course.course_code, 'CS102')
        self.assertEqual(self.course.description, 'Updated description')
        self.assertEqual(self.course.price, 150.0)
        # Check if the new image is saved correctly
        self.assertTrue(self.course.image.name.endswith('new_image.jpg'))
        # Check if the old image has been deleted from the file system
        self.assertFalse(default_storage.exists(self.course.image.path))  # Old image should be replaced
        # Check if the response redirects (this means the update was successful)
        self.assertRedirects(response, self.url)  # Should redirect to the same course edit page


class CourseEditSessionTestCase(TestCase):

    def setUp(self):
        # Create a user to associate with the course
        User = get_user_model()
        self.user = User.objects.create_user(username='testuser', password='password')

        # Create a course that we can edit
        self.course = Course.objects.create(
            course_name='Test Course',
            course_code='CS101',
            description='Test description',
            creator=self.user,
            instructor=self.user,
            price=100.0
        )

        # Create initial sessions for the course
        self.session_1 = Session.objects.create(course=self.course, name='Session 1', order=1)
        self.session_2 = Session.objects.create(course=self.course, name='Session 2', order=2)
        self.session_3 = Session.objects.create(course=self.course, name='Session 3', order=3)  # Corrected the session name here

        # URL for editing the course sessions
        self.url = reverse('course:course_edit_session', kwargs={'pk': self.course.pk})

    def test_edit_sessions(self):
        # Log in the user
        self.client.login(username='testuser', password='password')

        # Prepare data to update sessions, add new ones, delete some, and reorder them
        updated_data = {
            'session_ids': [str(self.session_1.id), str(self.session_2.id)],
            'session_names': ['Updated Session 1', 'Updated Session 2'],
            'new_session_names': ['New Session 4'],  # New session to be added
            'delete_session_ids': f'{self.session_3.id}',  # Delete session 3
            'session_order': f'{self.session_2.id},{self.session_1.id}',  # Reorder sessions (session 3 should be deleted)
        }

        # Send POST request to update the course sessions
        response = self.client.post(self.url, updated_data)

        # Refresh the course's sessions from the database
        self.session_1.refresh_from_db()
        self.session_2.refresh_from_db()

        # Verify that the session names were updated
        self.assertEqual(self.session_1.name, 'Updated Session 1')
        self.assertEqual(self.session_2.name, 'Updated Session 2')

        # Verify that a new session was added
        new_session = Session.objects.get(course=self.course, name='New Session 4')
        self.assertEqual(new_session.name, 'New Session 4')

        # Verify that session 3 was deleted
        with self.assertRaises(Session.DoesNotExist):
            self.session_3.refresh_from_db()

        # Verify the session order after reordering
        self.assertEqual(self.session_2.order, 0)  # After reorder, it should be first
        self.assertEqual(self.session_1.order, 1)  # Session 2 should still be second

        # Check if the response redirects (this means the update was successful)
        self.assertRedirects(response, self.url)  # Should redirect back to the course session edit page
        
class CourseEditTopicTagsTestCase(TestCase):
    
    def setUp(self):
        # Create a user
        User = get_user_model()
        self.user = User.objects.create_user(username='testuser', password='password')

        # Create a course
        self.course = Course.objects.create(
            course_name='Test Course',
            course_code='CS101',
            description='Test description',
            creator=self.user,
            instructor=self.user,
            price=100.0
        )

        # Create some topics
        self.topic_1 = Topic.objects.create(name='Topic 1')
        self.topic_2 = Topic.objects.create(name='Topic 2')

        # Create some tags with topics
        self.tag_1 = Tag.objects.create(name='Tag 1', topic=self.topic_1)
        self.tag_2 = Tag.objects.create(name='Tag 2', topic=self.topic_2)

        # Add tags to the course
        self.course.tags.add(self.tag_1, self.tag_2)

        # URL for editing course tags
        self.url = reverse('course:course_edit_topic_tags', kwargs={'pk': self.course.pk})

    def test_edit_tags(self):
        # Log in the user
        self.client.login(username='testuser', password='password')

        # Create a new topic and tag to add
        new_topic = Topic.objects.create(name='Topic 3')
        new_tag = Tag.objects.create(name='Tag 3', topic=new_topic)

        # Prepare data for the actions: add, delete, and reorder
        updated_data = {
            'tags': [ str(new_tag.id)],  # Add the new tag
            'delete_tag_{}'.format(self.tag_1.id): 'on',  # Mark to delete tag_1
        }

        # Send POST request to update the tags
        response = self.client.post(self.url, updated_data)

        # Refresh the course from the database
        self.course.refresh_from_db()

        # Verify that the new tag has been added to the course
        self.assertIn(new_tag, self.course.tags.all())

        # Verify that tag_1 has been deleted from the course
        self.assertNotIn(self.tag_1, self.course.tags.all())

        # Verify that tag_2 remains in the course tags
        self.assertIn(self.tag_2, self.course.tags.all())

        # Ensure the number of tags has increased by one
        self.assertEqual(self.course.tags.count(), 2)  # The tags should only be tag_2 and new_tag now


class CoureContentEditTestCase(TestCase):
    def setUp(self):
        """
        This method is run before each test.
        Create a test user, a reading material, and associated course material.
        """
        User = get_user_model()
        # Create a test user (if necessary for authentication)
        self.user = User.objects.create_user(username='testuser', password='testpassword')
        
        # Simulate user login (if required for the delete operation)
        self.client.login(username='testuser', password='testpassword')
        
        # Create a test course and session
        self.course = Course.objects.create(course_name='Test Course', course_code='TC101')
        self.session = Session.objects.create(course=self.course, name='Session 1', order=1)
        
        # Create a reading material object
        self.reading_material = ReadingMaterial.objects.create(
            title='Test Material',
            content='testing :))'  # Example HTML content
        )
        
        # Create a corresponding course material object
        self.course_material = CourseMaterial.objects.create(
            session=self.session,
            material_id=self.reading_material.id,
            material_type='lectures',
            title=self.reading_material.title,
            order=1
        )
        self.reading_material.material = self.course_material
        # URL to the course content edit view (adjusted with course and session IDs)
        self.edit_url = reverse('course:course_content_edit', args=[self.course.id, self.session.id])

    def test_delete_reading_material(self):
        """
        Test that a reading material is deleted and no longer exists in the database.
        """
        # Ensure that the material exists before deletion
        self.assertTrue(ReadingMaterial.objects.filter(id=self.reading_material.id).exists())

        # Ensure the related course material exists
        self.assertTrue(CourseMaterial.objects.filter(id=self.course_material.id).exists())

        # Send the delete request
        # Simulate the deletion by passing the material_id and material_type in the 'marked_for_deletion' POST parameter
        post_data = {
            'marked_for_deletion': f'{self.reading_material.id}:lectures'
        }
        
        # Send POST request to delete the material
        response = self.client.post(self.edit_url, post_data)

        # Check if the reading material no longer exists in the database
        self.assertFalse(ReadingMaterial.objects.filter(id=self.reading_material.id).exists())

        # Check that the related course material has also been deleted
        self.assertFalse(CourseMaterial.objects.filter(id=self.course_material.id).exists())
        
        # Optionally, check for any redirect (if your delete view redirects after success)
        # self.assertRedirects(response, expected_redirect_url)

    def test_course_content_add(self):
        self.url = reverse('course:course_content_edit', args=[self.course.pk, self.session.pk])

        # Prepare form data including files and other form fields
        file = SimpleUploadedFile('testfile.pdf', b'file_content', content_type='application/pdf')

        post_data = {
            'session_id': self.session.id,
            'uploaded_material_type[]': ['references'],
            'reading_material_title[]': ['Reading Material 123'],
            'reading_material_content[]': ['This is content for the material'],
            'uploaded_material_file[]': [file],
            'reading_material_type[]': ['labs'],
            'marked_for_deletion' : '',
            'assessment_id[]' : []

        }

        # File data (to be included in request.FILES)
        # files = {
        #     'uploaded_material_file[]': [file]
        # }

        # Send the POST request with form data and files data
        print(f"Posting to URL: {self.url}")
        response = self.client.post(self.url, post_data)
        course_material=CourseMaterial.objects.get(material_type='labs')
        reading_material=ReadingMaterial.objects.get(material=course_material)

        up_course_material=CourseMaterial.objects.get(material_type='references')
        up_reading_material=ReadingMaterial.objects.get(material=up_course_material)

        self.assertEqual(reading_material.content, 'This is content for the material')
        self.assertEqual(reading_material.title, 'Reading Material 123')
        self.assertEqual(course_material.material_type, 'labs')
        
        self.assertEqual(up_reading_material.title, 'testfile.pdf')
        self.assertEqual(up_course_material.material_type, 'references')

        # self.assertTrue(new_material.file.name.endswith('.pdf'))


# class CourseContentTestCase(TestCase):
#     def setUp(self):
#         # Create a course and session
#         self.course = Course.objects.create(course_name='Test Course')
#         self.session = Session.objects.create(course=self.course, name='Session 1', order=1)
#     def test_course_content_edit_post(self):
#         self.url = reverse('course:course_content_edit', args=[self.course.pk, self.session.pk])

#         # Prepare form data including files and other form fields
#         file = SimpleUploadedFile('testfile.pdf', b'file_content', content_type='application/pdf')

#         post_data = {
#             'session_id': self.session.id,
#             'uploaded_material_type[]': ['lectures'],
#             'reading_material_title[]': ['Reading Material'],
#             'reading_material_content[]': ['This is content for the material'],
#             'uploaded_material_file[]': [file],
#             'reading_material_type[]': ['labs'],
#             'marked_for_deletion' : '',
#             'assessment_id[]' : []

#         }

#         # File data (to be included in request.FILES)
#         # files = {
#         #     'uploaded_material_file[]': [file]
#         # }

#         # Send the POST request with form data and files data
#         print(f"Posting to URL: {self.url}")
#         response = self.client.post(self.url, post_data)
#         course_material=CourseMaterial.objects.get(session=self.session)

#         # Check that the reading material was added
#         new_material = ReadingMaterial.objects.get(title='Reading Material')
#         self.assertEqual(new_material.content, 'This is content for the material')
#         self.assertEqual(new_material.material_type, 'lectures')

#         # Check if the uploaded file is saved (depending on your model setup)
#         self.assertTrue(new_material.file.name.endswith('.pdf'))

  