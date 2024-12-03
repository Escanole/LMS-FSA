from django.test import TestCase, Client
from django.urls import reverse
from django.contrib.auth import get_user_model
from .models import Course, Enrollment, ReadingMaterial, Completion, Session, SessionCompletion, Topic, Tag, CourseMaterial, UserCourseProgress, Transaction
from course.views import duplicate_course
from department.models import Department
from feedback.models import CourseFeedback
from django.contrib.messages import get_messages
from django.utils.timezone import now
from django.utils import timezone
from django.core.files.uploadedfile import SimpleUploadedFile
from django.core.files.storage import default_storage
from certification.models import Certification  # Assuming this is where your Certification model is defined
from io import BytesIO


class CourseDetailViewTests(TestCase):
    def setUp(self):
        # Create users
        super().setUp()
        self.client = Client()
        User = get_user_model()

        self.superuser = User.objects.create_superuser(username='admin', password='password')
        self.instructor = User.objects.create_user(username="instructor", password="password",
                                                   email="instr@example.com", is_staff=True)
        self.student = User.objects.create_user(username="student", password="password", email="student@example.com")

        self.department = Department.objects.create(name="Test Department")
        self.department.users.add(self.student)

        # Setup course, departments, and enrollments
        self.course = Course.objects.create(
            course_name="Django Basics",
            course_code="DJ101",
            creator=self.instructor,
            instructor=self.instructor,
            description="abc",
            published=True,
            price=100,
            discount=10
        )

        self.department.courses.add(self.course)

        # Add prerequisites, tags, and sessions to the course
        self.prerequisite_course = Course.objects.create(
            course_name="Python Basics",
            course_code="PY101",
            creator=self.instructor,
            instructor=self.instructor,
            description="Learn Python basics.",
            published=True,
            price=100,
            discount=20
        )
        self.course.prerequisites.add(self.prerequisite_course)

        Enrollment.objects.create(student=self.student, course=self.prerequisite_course, is_active=True,
                                  date_enrolled=timezone.now())
        Enrollment.objects.create(student=self.student, course=self.course, is_active=True,
                                  date_enrolled=timezone.now())

        self.transaction = Transaction.objects.create(
            user=self.student,
            course=self.course,
            is_successful=True
        )

        # Create sessions
        self.session = Session.objects.create(course=self.course, name="Session 1", order=1)
        self.material = CourseMaterial.objects.create(
            session=self.session,
            material_id=1,
            material_type='lectures',
            order=1,
            title='Lecture 1'
        )

        # ReadingMaterial
        self.reading_material = ReadingMaterial.objects.create(
            material=self.material,
            title='Reading for Lecture 1',
            content='<p>This is content for Lecture 1</p>',
        )

        # Create tags
        self.topic = Topic.objects.create(name="Web Development")
        self.tag1 = Tag.objects.create(name="Django", topic=self.topic)
        self.tag2 = Tag.objects.create(name="Web Framework", topic=self.topic)
        self.course.tags.add(self.tag1, self.tag2)

        # Create a completion
        self.completion = Completion.objects.create(
            session=self.session,
            user=self.student,
            material=self.material,
            completed=True
        )

        SessionCompletion.objects.get_or_create(
            course=self.course,
            session=self.session,
            user=self.student,
            defaults={'completed': True}
        )

        # Add feedback
        self.feedback = CourseFeedback.objects.create(
            course=self.course,
            student=self.student,
            course_material=4,
            clarity_of_explanation=4,
            course_structure=2,
            practical_applications=5,
            support_materials=5,
            comments="ok",
        )

    # TEST DEF COURSE_DETAIL
    def test_superuser_can_access(self):
        """Superusers should always have access and be able to enroll."""
        self.client.login(username='admin', password='password')
        url = reverse('course:course_detail', kwargs={'pk': self.course.pk})
        response = self.client.get(url)

        self.assertEqual(response.status_code, 200)
        self.assertContains(response, "Django Basics")
        self.assertContains(response, "abc")
        self.assertContains(response, "ok")

    def test_instructor_access(self):
        """Instructors should have access to their own courses but cannot enroll."""
        self.client.login(username='instructor', password='password')
        url = reverse('course:course_detail', kwargs={'pk': self.course.pk})
        response = self.client.get(url)

        self.assertEqual(response.status_code, 200)
        self.assertContains(response, "Django Basics")
        self.assertContains(response, "abc")

    def test_student_in_department_can_access(self):
        """Students in the course's department should have access."""
        self.client.login(username='student', password='password')
        url = reverse('course:course_detail', kwargs={'pk': self.course.pk})
        response = self.client.get(url)

        self.assertEqual(response.status_code, 200)
        self.assertContains(response, "Django Basics")
        self.assertTrue(response.context['can_enroll'])
        self.assertTrue(response.context['is_enrolled'])

    def test_student_not_in_department_cannot_access(self):
        """Students not in the course's department should not have access."""
        # Create new student not in department
        User = get_user_model()
        other_student = User.objects.create_user(
            username="other_student",
            password="password"
        )
        self.client.login(username='other_student', password='password')

        url = reverse('course:course_detail', kwargs={'pk': self.course.pk})
        response = self.client.get(url)

        self.assertEqual(response.status_code, 200)
        self.assertFalse(response.context['can_enroll'])

    def test_course_without_department_accessible_to_all(self):
        """Courses without department should be accessible to all users."""
        # Create course without department
        course_no_dept = Course.objects.create(
            course_name="Open Course",
            course_code="OC101",
            creator=self.instructor,
            instructor=self.instructor,
            published=True
        )

        # Test with a new student
        User = get_user_model()
        new_student = User.objects.create_user(
            username="new_student",
            password="password"
        )
        self.client.login(username='new_student', password='password')

        url = reverse('course:course_detail', kwargs={'pk': course_no_dept.pk})
        response = self.client.get(url)

        self.assertEqual(response.status_code, 200)
        self.assertTrue(response.context['can_enroll'])

    def test_course_details_context(self):
        """Test that all required context data is present."""
        self.client.login(username='student', password='password')
        url = reverse('course:course_detail', kwargs={'pk': self.course.pk})
        response = self.client.get(url)

        self.assertEqual(response.status_code, 200)
        context = response.context

        # Check all required context variables
        self.assertIn('course', context)
        self.assertIn('prerequisites', context)
        self.assertIn('is_enrolled', context)
        self.assertIn('users_enrolled_count', context)
        self.assertIn('course_average_rating', context)
        self.assertIn('course_average_rating_star', context)
        self.assertIn('feedbacks', context)
        self.assertIn('sessions', context)
        self.assertIn('session_count', context)
        self.assertIn('latest_feedbacks', context)
        self.assertIn('tags', context)
        self.assertIn('instructor', context)
        self.assertIn('user_type', context)
        self.assertIn('user_progress', context)
        self.assertIn('random_tags', context)
        self.assertIn('can_enroll', context)

    def test_course_statistics(self):
        """Test that course statistics are calculated correctly."""
        self.client.login(username='student', password='password')
        url = reverse('course:course_detail', kwargs={'pk': self.course.pk})
        response = self.client.get(url)

        self.assertEqual(response.status_code, 200)
        context = response.context

        # Test enrollment count
        self.assertEqual(context['users_enrolled_count'], 1)

        # Test average rating calculation
        self.assertIsNotNone(context['course_average_rating'])
        expected_rating = 4  # (4+4+2+5+5)/5 = 4
        self.assertEqual(context['course_average_rating'], expected_rating)

        # Test rating star percentage
        expected_star_percentage = (expected_rating * 100) / 5
        self.assertEqual(context['course_average_rating_star'], expected_star_percentage)

    def test_user_type_identification(self):
        """Test that user types are correctly identified."""
        # Test for instructor
        self.client.login(username='instructor', password='password')
        url = reverse('course:course_detail', kwargs={'pk': self.course.pk})
        response = self.client.get(url)
        self.assertEqual(response.context['user_type'], 'instructor')

        # Test for student
        self.client.login(username='student', password='password')
        response = self.client.get(url)
        self.assertEqual(response.context['user_type'], 'student')

    def test_random_tags_displayed_correctly(self):
        self.client.login(username="student", password="password")
        url=reverse('course:course_detail', kwargs={'pk': self.course.pk})
        response=self.client.get(url)
        random_tags=response.context['random_tags']
        self.assertLessEqual(len(random_tags), 4)
        self.assertTrue(all(tag in self.course.tags.all() for tag in random_tags))

    def test_session_count(self):
        self.client.login(username="student", password="password")
        url=reverse('course:course_detail', kwargs={'pk': self.course.pk})
        response=self.client.get(url)
        self.assertEqual(response.context['session_count'],1)

    def test_latest_feedbacks(self):
        self.client.login(username="student", password="password")
        url=reverse('course:course_detail', kwargs={'pk': self.course.pk})
        response=self.client.get(url)
        self.assertEqual(response.status_code, 200)
        # Access the latest feedbacks from the context
        latest_feedbacks = response.context['latest_feedbacks']
        # Check that the feedbacks are ordered by `created_at` in descending order
        feedback_dates = [feedback.created_at for feedback in latest_feedbacks]
        self.assertEqual(feedback_dates, sorted(feedback_dates, reverse=True))

        # Check that the number of feedbacks is at most 5
        self.assertLessEqual(len(latest_feedbacks), 5)

    def test_user_progress(self):
        self.client.login(username="student", password="password")
        url=reverse('course:course_detail', kwargs={'pk': self.course.pk})
        response=self.client.get(url)
        user_progress=response.context['user_progress']
        self.assertEqual(len(user_progress),1)
        self.assertEqual(user_progress[0]['user'], self.student)
        self.assertEqual(user_progress[0]['progress'], 100)

    # TEST DEF COURSE_ENROLL
    def test_successfull_enrollment_without_payment(self):
        self.course.price = 0
        self.course.save()
        self.client.login(username="student", password="password")
        url=reverse('course:course_enroll', kwargs={'pk': self.course.pk})
        response = self.client.get(url)
        enrollment=Enrollment.objects.filter(student=self.student, course=self.course, is_active=True).exists()
        self.assertTrue(enrollment)
        messages = list(get_messages(response.wsgi_request))
        self.assertIn('You have been enrolled in Django Basics.', str(messages[0]))

        # Check redirect to course detail
        self.assertRedirects(response, reverse('course:course_detail', kwargs={'pk': self.course.pk}))

    def test_successfull_enrollment_with_payment(self):
        """Test enrollment process when course requires payment"""
        # Delete any existing enrollments/transactions
        Enrollment.objects.filter(student=self.student, course=self.course).delete()
        Transaction.objects.filter(user=self.student, course=self.course).delete()

        self.course.price = 100
        self.course.save()

        self.client.login(username="student", password="password")
        url = reverse('course:course_enroll', kwargs={'pk': self.course.pk})
        response = self.client.post(url)  # Changed to POST request since form submission is required

        # Check if transaction was created with is_successful=False
        transaction = Transaction.objects.filter(
            user=self.student,
            course=self.course,
            is_successful=False
        ).exists()
        self.assertTrue(transaction)

        # Verify the message
        messages = list(get_messages(response.wsgi_request))
        self.assertIn('Transaction required. Please complete the payment to activate enrollment.', str(messages[0]))

        # Check no enrollment created
        enrollment = Enrollment.objects.filter(student=self.student, course=self.course, is_active=True).exists()
        self.assertFalse(enrollment)

        # Verify redirect
        self.assertRedirects(response, reverse('course:course_detail', kwargs={'pk': self.course.pk}))

    def test_unsuccessfull_enrollment_due_to_missing_prerequisites(self):
        """Test enrollment fails when prerequisites are not met"""
        # Delete any existing enrollments
        Enrollment.objects.filter(student=self.student, course=self.course).delete()
        Enrollment.objects.filter(student=self.student, course=self.prerequisite_course).delete()
        Transaction.objects.filter(user=self.student, course=self.course).delete()

        self.client.login(username="student", password="password")
        url = reverse('course:course_enroll', kwargs={'pk': self.course.pk})
        response = self.client.post(url)  # Changed to POST request

        # Verify no enrollment was created
        enrollment = Enrollment.objects.filter(student=self.student, course=self.course).exists()
        self.assertFalse(enrollment)

        # Check error message
        messages = list(get_messages(response.wsgi_request))
        self.assertIn('You do not meet the prerequisites for this course.', str(messages[0]))

        # Verify redirect
        self.assertRedirects(response, reverse('course:course_detail', kwargs={'pk': self.course.pk}))

    def test_reactive_existing_enrollment(self):
        """Test reactivating an inactive enrollment"""
        # First delete any existing enrollments
        Enrollment.objects.filter(student=self.student, course=self.course).delete()
        Transaction.objects.filter(user=self.student, course=self.course).delete()

        # Create an inactive enrollment
        enrollment = Enrollment.objects.create(
            student=self.student,
            course=self.course,
            is_active=False,
            date_enrolled=now()
        )

        # Create a successful transaction (since course has no price)
        self.course.price = 0
        self.course.save()

        self.client.login(username="student", password="password")
        url = reverse('course:course_enroll', kwargs={'pk': self.course.pk})
        response = self.client.post(url)
        # Refresh enrollment from database
        enrollment.refresh_from_db()

        # Check enrollment was reactivated
        self.assertTrue(enrollment.is_active)
        self.assertEqual(enrollment.date_enrolled.date(), now().date())

        # Verify success message
        messages = list(get_messages(response.wsgi_request))
        self.assertIn(f'You have been enrolled in {self.course.course_name}', str(messages[0]))

        # Verify redirect
        self.assertRedirects(response, reverse('course:course_detail', kwargs={'pk': self.course.pk}))

    # TEST DEF COURSE_UNENROLL
    def test_course_unenroll(self):
        """Test the course unenrollment process"""
        self.client.login(username="student", password="password")
        url = reverse('course:course_unenroll', kwargs={'pk': self.course.pk})

        # First test GET request (confirmation page)
        get_response = self.client.get(url)
        self.assertEqual(get_response.status_code, 200)
        self.assertTemplateUsed(get_response, 'course/course_unenroll.html')

        # Test POST request (actual unenrollment)
        post_response = self.client.post(url)

        # Refresh enrollment from database
        enrollment = Enrollment.objects.get(student=self.student, course=self.course)
        transaction = Transaction.objects.get(user=self.student, course=self.course)

        # Check if enrollment is marked as inactive
        self.assertFalse(enrollment.is_active)
        self.assertIsNotNone(enrollment.date_unenrolled)

        # Check if transaction is marked as unsuccessful
        self.assertFalse(transaction.is_successful)

        # Check if completions are deleted
        self.assertFalse(
            Completion.objects.filter(
                user=self.student,
                session__course=self.course
            ).exists()
        )

        # Check if session completions are deleted
        self.assertFalse(
            SessionCompletion.objects.filter(
                user=self.student,
                course=self.course
            ).exists()
        )

        # Check if course progress is deleted
        self.assertFalse(
            UserCourseProgress.objects.filter(
                user=self.student,
                course=self.course
            ).exists()
        )

        # Verify success message
        messages = list(get_messages(post_response.wsgi_request))
        self.assertIn(f'You have been unenrolled from {self.course.course_name}', str(messages[0]))

        # Verify redirect to course list
        self.assertRedirects(post_response, reverse('course:course_list'))

    # TEST DEF DUPLICATE_COURSE
    def test_duplicate_course(self):
        """Test the course duplication process"""
        # Create a PDF file in the course materials
        pdf_content = '<iframe src="/media/course_pdf/DJ101/test.pdf#toolbar=0" style="border: none; width: 100%; height: 590px;"></iframe>'
        reading_material = ReadingMaterial.objects.create(
            material=self.material,
            title='PDF Material',
            content=pdf_content
        )

        # Call the duplicate_course function
        duplicated_course = duplicate_course(self.course)

        # Test basic course information
        self.assertEqual(duplicated_course.course_name, f"{self.course.course_name} - Copy")
        self.assertEqual(duplicated_course.description, self.course.description)
        self.assertEqual(duplicated_course.instructor, self.course.instructor)
        self.assertFalse(duplicated_course.published)

        # Test unique course code
        self.assertTrue(duplicated_course.course_code.startswith(self.course.course_code))
        self.assertNotEqual(duplicated_course.course_code, self.course.course_code)

        # Test sessions were duplicated
        original_sessions = self.course.sessions.count()
        duplicated_sessions = duplicated_course.sessions.count()
        self.assertEqual(original_sessions, duplicated_sessions)

        # Test materials were duplicated (except assessments)
        for original_session, duplicated_session in zip(
            self.course.sessions.all(),
            duplicated_course.sessions.all()
        ):
            # Check session name and order
            self.assertEqual(original_session.name, duplicated_session.name)
            self.assertEqual(original_session.order, duplicated_session.order)

            # Check materials (excluding assessments)
            original_materials = original_session.materials.exclude(material_type='assessments')
            duplicated_materials = duplicated_session.materials.exclude(material_type='assessments')

            self.assertEqual(original_materials.count(), duplicated_materials.count())

            for original_material, duplicated_material in zip(
                original_materials.order_by('order'),
                duplicated_materials.order_by('order')
            ):
                self.assertEqual(original_material.material_type, duplicated_material.material_type)
                self.assertEqual(original_material.order, duplicated_material.order)
                self.assertEqual(original_material.title, duplicated_material.title)

                # Check associated reading materials
                if original_material.material_type != 'assessments':
                    original_reading = ReadingMaterial.objects.get(id=original_material.material_id)
                    duplicated_reading = ReadingMaterial.objects.get(id=duplicated_material.material_id)

                    self.assertEqual(original_reading.title, duplicated_reading.title)

                    # Check if PDF content was properly duplicated with new course code
                    if 'course_pdf' in original_reading.content:
                        self.assertIn(duplicated_course.course_code, duplicated_reading.content)
                        self.assertNotIn(self.course.course_code, duplicated_reading.content)

        # Test prerequisites and tags were copied
        self.assertEqual(
            set(self.course.prerequisites.all()),
            set(duplicated_course.prerequisites.all())
        )
        self.assertEqual(
            set(self.course.tags.all()),
            set(duplicated_course.tags.all())
        )

    def test_duplicate_course_name_uniqueness(self):
        """Test that duplicate courses get unique names"""
        # Create first duplicate
        first_duplicate = duplicate_course(self.course)
        self.assertEqual(first_duplicate.course_name, f"{self.course.course_name} - Copy")

        # Create second duplicate
        second_duplicate = duplicate_course(self.course)
        self.assertEqual(second_duplicate.course_name, f"{self.course.course_name} - Copy (2)")

        # Create third duplicate
        third_duplicate = duplicate_course(self.course)
        self.assertEqual(third_duplicate.course_name, f"{self.course.course_name} - Copy (3)")

    # TEST DEF TOGGLE_COMPLETION
    def test_toggle_completion_authenticated(self):
        """Test completion toggle for authenticated user"""
        self.client.login(username="student", password="password")

        # Make sure completion doesn't exist yet
        Completion.objects.filter(
            session=self.session,
            material=self.material,
            user=self.student
        ).delete()

        url = reverse('course:toggle_completion', kwargs={'pk': self.course.pk})
        response = self.client.post(url, {'file_id': self.material.id})

        self.assertEqual(response.status_code, 200)

        # Check if completion was created and marked as completed
        completion = Completion.objects.get(
            session=self.session,
            material=self.material,
            user=self.student
        )
        self.assertTrue(completion.completed)

        # Verify JSON response
        data = response.json()
        self.assertIn('completed', data)
        self.assertIn('next_item_type', data)
        self.assertIn('next_item_id', data)
        self.assertIn('next_session_id', data)

    def test_toggle_completion_unauthenticated(self):
        """Test completion toggle for unauthenticated user"""
        # Instead of using logout which triggers activity logging,
        # just create a new client without logging in
        unauthenticated_client = Client()

        # Delete any existing completions
        Completion.objects.filter(
            session=self.session,
            material=self.material,
            user=self.student
        ).delete()

        url = reverse('course:toggle_completion', kwargs={'pk': self.course.pk})
        response = unauthenticated_client.post(url, {'file_id': self.material.id})

        # Should redirect to login page
        self.assertEqual(response.status_code, 302)
        self.assertIn('login', response.url)

        # Verify no completion was created
        self.assertFalse(
            Completion.objects.filter(
                session=self.session,
                material=self.material,
                user=self.student
            ).exists()
        )

    def test_toggle_completion_completion_toggled(self):
        """Test toggling an existing completion"""
        self.client.login(username="student", password="password")

        # Delete any existing completions first
        Completion.objects.filter(
            session=self.session,
            material=self.material,
            user=self.student
        ).delete()

        # Create initial completion
        completion = Completion.objects.create(
            session=self.session,
            material=self.material,
            user=self.student,
            completed=True
        )

        # Toggle the completion
        url = reverse('course:toggle_completion', kwargs={'pk': self.course.pk})
        response = self.client.post(url, {'file_id': self.material.id})

        # Refresh from database
        completion.refresh_from_db()

        # Verify completion was toggled to False
        self.assertFalse(completion.completed)

    def test_session_completion_status(self):
        """Test session completion status when all materials are completed"""
        self.client.login(username="student", password="password")

        # Delete any existing completions and session completions
        Completion.objects.filter(
            session=self.session,
            material=self.material,
            user=self.student
        ).delete()
        SessionCompletion.objects.filter(
            course=self.course,
            session=self.session,
            user=self.student
        ).delete()

        # Toggle completion for the material
        url = reverse('course:toggle_completion', kwargs={'pk': self.course.pk})
        response = self.client.post(url, {'file_id': self.material.id})

        # Since this is the only material in the session, completing it should complete the session
        session_completion = SessionCompletion.objects.get(
            course=self.course,
            session=self.session,
            user=self.student
        )

        # Verify session is marked as completed
        self.assertTrue(session_completion.completed)

    # TEST DEF TOGGLE_PUBLISH
    def test_toggle_publish_as_instructor(self):
        """Test that instructor can toggle course publish status"""
        self.client.login(username="instructor", password="password")

        # Set initial state
        self.course.published = False
        self.course.save()

        url = reverse('course:toggle_publish', kwargs={'pk': self.course.pk})
        response = self.client.post(url)  # Changed to POST request

        # Refresh course from database
        self.course.refresh_from_db()

        # Verify redirect and publish state
        self.assertEqual(response.status_code, 302)  # Redirect
        self.assertTrue(self.course.published)

        # Test toggling back to unpublished
        response = self.client.post(url)
        self.course.refresh_from_db()
        self.assertFalse(self.course.published)

    def test_toggle_publish_as_superuser(self):
        """Test that superuser can toggle course publish status"""
        self.client.login(username="admin", password="password")

        # Set initial state
        self.course.published = False
        self.course.save()

        url = reverse('course:toggle_publish', kwargs={'pk': self.course.pk})
        response = self.client.post(url)  # Changed to POST request

        # Refresh course from database
        self.course.refresh_from_db()

        # Verify redirect and publish state
        self.assertEqual(response.status_code, 302)  # Redirect
        self.assertTrue(self.course.published)

        # Test toggling back to unpublished
        response = self.client.post(url)
        self.course.refresh_from_db()
        self.assertFalse(self.course.published)

    def test_toggle_publish_as_student(self):
        """Test that student cannot toggle course publish status"""
        self.client.login(username="student", password="password")

        # Set initial state
        initial_state = self.course.published

        url = reverse('course:toggle_publish', kwargs={'pk': self.course.pk})
        response = self.client.post(url)  # Changed to POST request

        # Refresh course from database
        self.course.refresh_from_db()

        # Verify redirect to course detail and unchanged publish state
        self.assertEqual(response.status_code, 302)  # Redirect to course detail
        self.assertEqual(self.course.published, initial_state)  # State should not change
        self.assertRedirects(response, reverse('course:course_detail', kwargs={'pk': self.course.pk}))

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
            Topic.objects.all().order_by('id'),  # Sắp xếp theo 'id'
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
        self.assertContains(response, self.topic1.name)  # Tên topic
        self.assertContains(response, self.tag1.name)  # Tên tag


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
        self.assertEqual(response.status_code, 302)

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
            any("Please enter at least one tag name and select a topic for each tag." in str(message) for message in
                messages),
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
            'discount': 0  # New image to upload
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
        self.session_3 = Session.objects.create(course=self.course, name='Session 3',
                                                order=3)  # Corrected the session name here

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
            'session_order': f'{self.session_2.id},{self.session_1.id}',
            # Reorder sessions (session 3 should be deleted)
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
            'tags': [str(new_tag.id)],  # Add the new tag
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
            'marked_for_deletion': '',
            'assessment_id[]': []

        }

        print(f"Posting to URL: {self.url}")
        response = self.client.post(self.url, post_data)
        course_material = CourseMaterial.objects.get(material_type='labs')
        reading_material = ReadingMaterial.objects.get(material=course_material)

        up_course_material = CourseMaterial.objects.get(material_type='references')
        up_reading_material = ReadingMaterial.objects.get(material=up_course_material)

        self.assertEqual(reading_material.content, 'This is content for the material')
        self.assertEqual(reading_material.title, 'Reading Material 123')
        self.assertEqual(course_material.material_type, 'labs')

        self.assertEqual(up_reading_material.title, 'testfile.pdf')
        self.assertEqual(up_course_material.material_type, 'references')


class ReadingMaterialDetailTestCase(TestCase):
    def setUp(self):
        # Tạo một tài liệu để kiểm tra
        self.reading_material = ReadingMaterial.objects.create(
            title="Test Reading Material",
            content="<p>Test Content</p>"
        )
        self.client = Client()

        # Sử dụng đầy đủ tên view với namespace "course"
        self.detail_url = reverse("course:reading_material_detail", kwargs={"id": self.reading_material.id})

    def test_normal_request(self):
        # Gửi một yêu cầu GET thông thường
        response = self.client.get(self.detail_url)

        # Kiểm tra trạng thái HTTP trả về
        self.assertEqual(response.status_code, 200)

        # Kiểm tra context của template
        self.assertTemplateUsed(response, "material/reading_material_detail.html")
        self.assertContains(response, "Test Reading Material")
        self.assertContains(response, "Test Content")

    def test_ajax_request(self):
        # Gửi một yêu cầu AJAX
        response = self.client.get(
            self.detail_url,
            HTTP_X_REQUESTED_WITH="XMLHttpRequest"  # Giả lập AJAX request
        )

        # Kiểm tra trạng thái HTTP trả về
        self.assertEqual(response.status_code, 200)

        # Kiểm tra kiểu dữ liệu trả về là JSON
        self.assertEqual(response["Content-Type"], "application/json")

        # Kiểm tra nội dung JSON trả về
        json_data = response.json()
        self.assertEqual(json_data["title"], "Test Reading Material")
        self.assertEqual(json_data["content"], "<p>Test Content</p>")


class AddPDFInContentEditTestCase(TestCase):
    def setUp(self):
        User = get_user_model()
        self.user = User.objects.create_user(username="testuser", password="password")
        self.client = Client()
        self.client.login(username="testuser", password="password")

        self.course = Course.objects.create(course_name="Test Course", course_code="TC101")
        self.session = Session.objects.create(course=self.course, name="Test Session", order=1)

        self.edit_url = reverse("course:course_content_edit",
                                kwargs={"pk": self.course.pk, "session_id": self.session.pk})

    def test_add_pdf(self):
        pdf_content = BytesIO(b"Test PDF Content")
        uploaded_pdf = SimpleUploadedFile("test.pdf", pdf_content.getvalue(), content_type="application/pdf")
        data = {
            "uploaded_material_file[]": [uploaded_pdf],
            "uploaded_material_type[]": ["lectures"],
        }
        response = self.client.post(self.edit_url, data)
        self.assertEqual(response.status_code, 302)

        new_material = CourseMaterial.objects.filter(session=self.session, material_type="lectures").first()
        self.assertIsNotNone(new_material)
        self.assertEqual(new_material.title, "test.pdf")


class ReorderSessionTestCase(TestCase):
    def setUp(self):
        User = get_user_model()
        self.user = User.objects.create_user(username="testuser", password="password")
        self.client = Client()
        self.client.login(username="testuser", password="password")

        # Tạo khóa học và các session
        self.course = Course.objects.create(course_name="Test Course", course_code="TC101")
        self.session1 = Session.objects.create(course=self.course, name="Session 1", order=0)
        self.session2 = Session.objects.create(course=self.course, name="Session 2", order=1)
        self.session3 = Session.objects.create(course=self.course, name="Session 3", order=2)

        # URL của chức năng chỉnh sửa session
        self.edit_session_url = reverse("course:course_edit_session", kwargs={"pk": self.course.pk})

    def test_reorder_sessions(self):
        # Gửi dữ liệu POST với thứ tự mới
        data = {
            "session_order": f"{self.session3.id},{self.session1.id},{self.session2.id}",  # session3 lên đầu
        }
        response = self.client.post(self.edit_session_url, data)

        # Đảm bảo trả về đúng trạng thái
        self.assertEqual(response.status_code, 302)

        # Kiểm tra thứ tự sau khi sắp xếp
        self.session1.refresh_from_db()
        self.session2.refresh_from_db()
        self.session3.refresh_from_db()
        self.assertEqual(self.session3.order, 0)  # Session 3 ở vị trí đầu tiên
        self.assertEqual(self.session1.order, 1)  # Session 1 ở vị trí thứ hai
        self.assertEqual(self.session2.order, 2)  # Session 2 ở vị trí cuối


class EditReadingMaterialTestCase(TestCase):
    def setUp(self):
        # Sử dụng model người dùng tùy chỉnh
        User = get_user_model()
        # Tạo user test
        self.user = User.objects.create_user(username="testuser", password="password")
        self.client = Client()
        self.client.login(username="testuser", password="password")

        # Tạo course test
        self.course = Course.objects.create(course_name="Test Course", course_code="TC101")
        self.session = Session.objects.create(course=self.course, name="Test Session", order=1)
        self.reading_material = ReadingMaterial.objects.create(
            title="Old Title",
            content="<p>Old Content</p>",
        )
        self.course_material = CourseMaterial.objects.create(
            session=self.session,
            material_id=self.reading_material.id,
            material_type="lectures",
            order=1,
            title="Old Title",
        )
        self.reading_material.material = self.course_material
        self.reading_material.save()

        self.edit_url = reverse(
            "course:edit_reading_material",
            kwargs={
                "pk": self.course.pk,
                "session_id": self.session.pk,
                "reading_material_id": self.reading_material.pk
            }
        )

    def test_edit_reading_material(self):
        updated_data = {
            "title": "New Title",
            "content": "<p>New Content</p>",
            "material_type": "lectures",
        }
        response = self.client.post(self.edit_url, updated_data)
        self.assertEqual(response.status_code, 302)
        self.reading_material.refresh_from_db()
        self.course_material.refresh_from_db()
        self.assertEqual(self.reading_material.title, "New Title")
        self.assertEqual(self.reading_material.content, "<p>New Content</p>")
        self.assertEqual(self.course_material.title, "New Title")
        self.assertEqual(self.course_material.material_type, "lectures")


class DeleteMaterialInContentEditTestCase(TestCase):
    def setUp(self):
        User = get_user_model()
        self.user = User.objects.create_user(username="testuser", password="password")
        self.client = Client()
        self.client.login(username="testuser", password="password")

        self.course = Course.objects.create(course_name="Test Course", course_code="TC101")
        self.session = Session.objects.create(course=self.course, name="Test Session", order=1)

        self.reading_material = ReadingMaterial.objects.create(
            title="Material to Delete",
            content="<p>Delete Me</p>",
        )
        self.course_material = CourseMaterial.objects.create(
            session=self.session,
            material_id=self.reading_material.id,
            material_type="lectures",
            order=1,
            title="Material to Delete",
        )
        self.reading_material.material = self.course_material
        self.reading_material.save()

        self.edit_url = reverse("course:course_content_edit",
                                kwargs={"pk": self.course.pk, "session_id": self.session.pk})

    def test_delete_material(self):
        data = {
            "marked_for_deletion": f"{self.reading_material.id}:lectures"
        }
        response = self.client.post(self.edit_url, data)
        self.assertEqual(response.status_code, 302)
        with self.assertRaises(ReadingMaterial.DoesNotExist):
            ReadingMaterial.objects.get(pk=self.reading_material.pk)
        with self.assertRaises(CourseMaterial.DoesNotExist):
            CourseMaterial.objects.get(pk=self.course_material.pk)


class CourseSearchTests(TestCase):
    def setUp(self):
        # Create some sample courses for testing
        Course.objects.create(course_name="Python Basics", description="Learn Python from scratch", course_code="PY101")
        Course.objects.create(course_name="Advanced Python", description="Deep dive into Python", course_code="PY201")
        Course.objects.create(course_name="Introduction ", description="Basic programming concepts",
                              course_code="CS101")

    def test_course_search(self):
        # Test searching for a course by full name
        response = self.client.get(reverse('course:course_search'), {'query': 'Python'})
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, "Python Basics")
        self.assertContains(response, "Advanced Python")

        # Test searching for a course that does not exist
        response = self.client.get(reverse('course:course_search'), {'query': 'Nonexistent Course'})
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, "No courses found")  # Adjust this based on your template's behavior

        # Test searching with partial match
        response = self.client.get(reverse('course:course_search'), {'query': 'Python Basics'})
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, "Python Basics")

        # Test searching with case insensitivity
        response = self.client.get(reverse('course:course_search'), {'query': 'python basics'})
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, "Python Basics")

        # Test searching with a substring that matches multiple courses
        response = self.client.get(reverse('course:course_search'), {'query': 'Python'})
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, "Python Basics")
        self.assertContains(response, "Advanced Python")

        # Test searching for a course by course code
        response = self.client.get(reverse('course:course_search'), {'query': 'PY101'})
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, "Python Basics")

        # Test searching for a course with a different case in course code
        response = self.client.get(reverse('course:course_search'), {'query': 'py101'})
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, "Python Basics")

        # Test searching for a course with a description keyword
        response = self.client.get(reverse('course:course_search'), {'query': 'programming'})
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, "Introduction ")

        # Test searching for a course with a missing word in description
        response = self.client.get(reverse('course:course_search'), {'query': 'gramming'})
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, "Introduction ")

        # Test searching for a course with a missing word in name
        response = self.client.get(reverse('course:course_search'), {'query': 'troduc'})
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, "Introduction ")

        # Test searching for a course with a missing word in code
        response = self.client.get(reverse('course:course_search'), {'query': 'cs'})
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, "Introduction ")

        # Test searching with a course without whitespace but have CL : Lỗi không đáng kể
        response = self.client.get(reverse('course:course_search'), {'query': 'PythonBasics'})
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, "Python Basics")

        # Test searching with a course without whitespace but not have CL : Lỗi không đáng kể
        response = self.client.get(reverse('course:course_search'), {'query': 'pythonbasics'})
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, "Python Basics")

        # Test searching with leading and trailing whitespace : Lỗi
        response = self.client.get(reverse('course:course_search'), {'query': '  Python  '})
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, "Python Basics")


class CourseCertificationTests(TestCase):
    def setUp(self):
        # Create a user for testing
        self.user = get_user_model().objects.create_user(
            username='testuser',
            password='testpassword'
        )
        # Create a sample course
        self.course = Course.objects.create(
            course_name="Python Basics",
            description="Learn Python from scratch",
            course_code="PY101"
        )
        # Create sessions for the course
        self.session1 = Session.objects.create(course=self.course, name="Session 1", order=1)
        self.session2 = Session.objects.create(course=self.course, name="Session 2", order=2)

    def test_certification_generation(self):
        # Simulate user completing all sessions
        SessionCompletion.objects.create(course=self.course, user=self.user, session=self.session1, completed=True)
        SessionCompletion.objects.create(course=self.course, user=self.user, session=self.session2, completed=True)

        # Check if certification is generated
        self.course.check_and_generate_certification(self.user)
        certification = Certification.objects.filter(course=self.course, user=self.user).first()
        self.assertIsNotNone(certification)
        self.assertEqual(certification.course, self.course)
        self.assertEqual(certification.user, self.user)

    def test_no_duplicate_certification(self):
        # Simulate user completing all sessions
        SessionCompletion.objects.create(course=self.course, user=self.user, session=self.session1, completed=True)
        SessionCompletion.objects.create(course=self.course, user=self.user, session=self.session2, completed=True)

        # Generate certification for the first time
        self.course.check_and_generate_certification(self.user)
        certification = Certification.objects.filter(course=self.course, user=self.user).count()
        self.assertEqual(certification, 1)  # Ensure only one certification is created

        # Attempt to generate certification again
        self.course.check_and_generate_certification(self.user)
        certification = Certification.objects.filter(course=self.course, user=self.user).count()
        self.assertEqual(certification, 1)  # Still only one certification

    def test_no_certification_if_sessions_not_completed(self):
        # Simulate user not completing all sessions
        SessionCompletion.objects.create(course=self.course, user=self.user, session=self.session1, completed=True)
        # session2 is not completed

        # Check if certification is generated
        self.course.check_and_generate_certification(self.user)
        certification = Certification.objects.filter(course=self.course, user=self.user).first()
        self.assertIsNone(certification)  # No certification should be generated

    def test_no_certification_when_no_sessions(self):
        # Create a new course with no sessions
        empty_course = Course.objects.create(course_name="Empty Course", description="No sessions",
                                             course_code="EMPTY101")

        # Check if certification is generated for a user with no sessions
        empty_course.check_and_generate_certification(self.user)
        certification = Certification.objects.filter(course=empty_course, user=self.user).first()
        self.assertIsNone(certification)  # No certification should be generated

    def test_certification_generation_multiple_users(self):
        # Create another user
        another_user = get_user_model().objects.create_user(
            username='anotheruser',
            password='anotherpassword'
        )

        # Simulate both users completing all sessions
        SessionCompletion.objects.create(course=self.course, user=self.user, session=self.session1, completed=True)
        SessionCompletion.objects.create(course=self.course, user=self.user, session=self.session2, completed=True)

        SessionCompletion.objects.create(course=self.course, user=another_user, session=self.session1, completed=True)
        SessionCompletion.objects.create(course=self.course, user=another_user, session=self.session2, completed=True)

        # Check if certification is generated for both users
        self.course.check_and_generate_certification(self.user)
        self.course.check_and_generate_certification(another_user)

        certification_user = Certification.objects.filter(course=self.course, user=self.user).first()
        certification_another_user = Certification.objects.filter(course=self.course, user=another_user).first()

        self.assertIsNotNone(certification_user)
        self.assertIsNotNone(certification_another_user)
        self.assertNotEqual(certification_user.id,
                            certification_another_user.id)  # Ensure they are different certifications

    def test_certification_content(self):
        # Simulate user completing all sessions
        SessionCompletion.objects.create(course=self.course, user=self.user, session=self.session1, completed=True)
        SessionCompletion.objects.create(course=self.course, user=self.user, session=self.session2, completed=True)

        # Generate certification
        self.course.check_and_generate_certification(self.user)

        # Retrieve the generated certification
        certification = Certification.objects.filter(course=self.course, user=self.user).first()

        # Check that the certification is not None
        self.assertIsNotNone(certification)

        # Verify the contents of the certification
        self.assertEqual(certification.course, self.course)
        self.assertEqual(certification.user, self.user)
        self.assertIn(self.user.username, certification.generated_html_content)  # Check recipient name
        self.assertIn(self.course.course_name, certification.generated_html_content)  # Check course name
        self.assertIn("Successfully completed the course.", certification.generated_html_content)  # Check description
        self.assertIn(timezone.now().strftime('%Y-%m-%d'), certification.generated_html_content)  # Check awarded date
        self.assertIn(str(timezone.now().year), certification.generated_html_content)  # Check awarded year


class CourseListTests(TestCase):
    def setUp(self):
        User = get_user_model()
        # Create users
        self.superuser = User.objects.create_superuser(
            username='superuser',
            password='superpassword'
        )
        self.instructor = User.objects.create_user(
            username='instructor',
            password='instructorpassword'
        )
        self.student = User.objects.create_user(
            username='student',
            password='studentpassword'
        )

        # Create courses
        self.published_course = Course.objects.create(
            course_name="Published Course",
            description="This course is published.",
            course_code="PUB101",
            published=True
        )
        self.unpublished_course = Course.objects.create(
            course_name="Unpublished Course",
            description="This course is not published.",
            course_code="UNPUB101",
            published=False
        )
        self.instructor_course = Course.objects.create(
            course_name="Instructor Course",
            description="Course taught by instructor.",
            course_code="INST101",
            published=True,
            instructor=self.instructor
        )

        # Create a session and material for the published course
        self.session = Session.objects.create(course=self.published_course, name="Session 1", order=1)
        self.reading_material = ReadingMaterial.objects.create(
            title="Reading Material for Published Course",
            content="Content of reading material for published course"
        )
        CourseMaterial.objects.create(
            session=self.session,
            material_id=self.reading_material.id,
            material_type='reading',
            title=self.reading_material.title,
            order=1
        )

    def test_course_list_as_superuser(self):
        self.client.login(username='superuser', password='superpassword')
        response = self.client.get(reverse('course:course_list'))
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, "Published Course")
        self.assertContains(response, "Unpublished Course")
        self.assertContains(response, "Instructor Course")

    def test_course_list_as_instructor(self):
        self.client.login(username='instructor', password='instructorpassword')
        response = self.client.get(reverse('course:course_list'))
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, "Published Course")
        self.assertContains(response, "Instructor Course")
        self.assertNotContains(response, "Unpublished Course")  # Assuming instructors see only published courses

    def test_course_list_as_student(self):
        self.client.login(username='student', password='studentpassword')
        response = self.client.get(reverse('course:course_list'))

        # Debugging output
        print("Response status code:", response.status_code)
        print("Response content:", response.content.decode())

        self.assertEqual(response.status_code, 200)
        self.assertContains(response, "Published Course")
        self.assertNotContains(response, "Unpublished Course")

    def test_course_list_pagination(self):
        # Create more courses for pagination testing
        for i in range(15):
            course = Course.objects.create(
                course_name=f"Course {i + 1}",
                description="This is a test course.",
                course_code=f"COURSE{i + 1}",
                published=True  # Ensure all courses are published
            )
            session = Session.objects.create(course=course, name=f"Session for Course {i + 1}", order=1)
            reading_material = ReadingMaterial.objects.create(
                title=f"Reading Material for Course {i + 1}",
                content="Content of reading material for this course"
            )
            CourseMaterial.objects.create(
                session=session,
                material_id=reading_material.id,
                material_type='reading',
                title=reading_material.title,
                order=1
            )

        self.client.login(username='student', password='studentpassword')
        response = self.client.get(reverse('course:course_list') + '?page=2')  # Assuming 9 courses per page
        self.assertEqual(response.status_code, 200)

        # Debugging output
        print("Response content:", response.content.decode())

        # Check that the second page contains "Course 10" and "Course 11"
        self.assertContains(response, "Course 10")
        self.assertContains(response, "Course 11")

    def test_recommended_courses_logic(self):
        # Log in the student
        self.client.login(username='student', password='studentpassword')

        # Create topics
        topic_python = Topic.objects.create(name="Python")
        topic_data_science = Topic.objects.create(name="Data Science")

        # Create courses with tags
        course1 = Course.objects.create(
            course_name="Python Basics",
            description="Learn Python from scratch",
            course_code="PY101",
            published=True
        )
        course2 = Course.objects.create(
            course_name="Advanced Python",
            description="Deep dive into Python",
            course_code="PY201",
            published=True
        )
        course3 = Course.objects.create(
            course_name="Data Science with Python",
            description="Learn data science using Python",
            course_code="DS101",
            published=True
        )

        # Create tags with topic_id
        tag_python = Tag.objects.create(name="Python", topic=topic_python)
        tag_data_science = Tag.objects.create(name="Data Science", topic=topic_data_science)

        # Assign tags to courses
        course1.tags.add(tag_python)  # Course 1 has the Python tag
        course2.tags.add(tag_python)  # Course 2 also has the Python tag
        course3.tags.add(tag_data_science)  # Course 3 has a different tag

        # Create materials for each course
        session1 = Session.objects.create(course=course1, name="Session 1", order=1)
        reading_material1 = ReadingMaterial.objects.create(
            title="Reading Material for Python Basics",
            content="Content for Python Basics"
        )
        CourseMaterial.objects.create(
            session=session1,
            material_id=reading_material1.id,
            material_type='reading',
            title=reading_material1.title,
            order=1
        )

        session2 = Session.objects.create(course=course2, name="Session 2", order=1)
        reading_material2 = ReadingMaterial.objects.create(
            title="Reading Material for Advanced Python",
            content="Content for Advanced Python"
        )
        CourseMaterial.objects.create(
            session=session2,
            material_id=reading_material2.id,
            material_type='reading',
            title=reading_material2.title,
            order=1
        )

        session3 = Session.objects.create(course=course3, name="Session 3", order=1)
        reading_material3 = ReadingMaterial.objects.create(
            title="Reading Material for Data Science with Python",
            content="Content for Data Science with Python"
        )
        CourseMaterial.objects.create(
            session=session3,
            material_id=reading_material3.id,
            material_type='reading',
            title=reading_material3.title,
            order=1
        )

        # Enroll the student in course1
        Enrollment.objects.create(student=self.student, course=course1, is_active=True)

        # Now, when the student views the course list, they should see recommendations
        response = self.client.get(reverse('course:course_list'))

        # Debugging output
        print("Response content:", response.content.decode())

        # Check that the recommended courses include course2 (similar tag)
        self.assertContains(response, "Advanced Python")

