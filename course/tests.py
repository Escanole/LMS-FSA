<<<<<<< HEAD
from django.test import TestCase, Client
from django.urls import reverse
from django.contrib.auth import get_user_model
from .models import Course, Enrollment, ReadingMaterial, Completion, Session, SessionCompletion, Topic, Tag, CourseMaterial, UserCourseProgress, Transaction
from course.views import duplicate_course
from department.models import Department
from assessments.models import Assessment
from module_group.models import ModuleGroup
from feedback.models import CourseFeedback
from django.contrib.messages import get_messages
from django.utils.timezone import now
from django.utils import timezone
from django.http import JsonResponse


class CourseDetailViewTests(TestCase):
    def setUp(self):
        # Create users
        super().setUp()
        self.client = Client()
        User = get_user_model()

        self.superuser = User.objects.create_superuser(username='admin', password='password')
        self.instructor = User.objects.create_user(username="instructor", password="password", email="instr@example.com", is_staff=True)
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
        
        Enrollment.objects.create(student=self.student, course=self.prerequisite_course, is_active=True, date_enrolled=timezone.now())
        Enrollment.objects.create(student=self.student, course=self.course, is_active=True, date_enrolled=timezone.now())
        
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
    # def test_superuser_can_access(self):
    #     """Superusers should always have access and be able to enroll."""
    #     self.client.login(username='admin', password='password')
    #     url = reverse('course:course_detail', kwargs={'pk': self.course.pk})
    #     response = self.client.get(url)

    #     self.assertEqual(response.status_code, 200)
    #     self.assertContains(response, "Django Basics")
    #     self.assertContains(response, "abc")
    #     self.assertContains(response, "ok")

    # def test_instructor_access(self):
    #     """Instructors should have access to their own courses but cannot enroll."""
    #     self.client.login(username='instructor', password='password')
    #     url = reverse('course:course_detail', kwargs={'pk': self.course.pk})
    #     response = self.client.get(url)

    #     self.assertEqual(response.status_code, 200)
    #     self.assertContains(response, "Django Basics")
    #     self.assertContains(response, "abc")

    # def test_student_in_department_can_access(self):
    #     """Students in the course's department should have access."""
    #     self.client.login(username='student', password='password')
    #     url = reverse('course:course_detail', kwargs={'pk': self.course.pk})
    #     response = self.client.get(url)
        
    #     self.assertEqual(response.status_code, 200)
    #     self.assertContains(response, "Django Basics")
    #     self.assertTrue(response.context['can_enroll'])
    #     self.assertTrue(response.context['is_enrolled'])

    # def test_student_not_in_department_cannot_access(self):
    #     """Students not in the course's department should not have access."""
    #     # Create new student not in department
    #     User = get_user_model()
    #     other_student = User.objects.create_user(
    #         username="other_student", 
    #         password="password"
    #     )
    #     self.client.login(username='other_student', password='password')
        
    #     url = reverse('course:course_detail', kwargs={'pk': self.course.pk})
    #     response = self.client.get(url)
        
    #     self.assertEqual(response.status_code, 200)
    #     self.assertFalse(response.context['can_enroll'])

    # def test_course_without_department_accessible_to_all(self):
    #     """Courses without department should be accessible to all users."""
    #     # Create course without department
    #     course_no_dept = Course.objects.create(
    #         course_name="Open Course",
    #         course_code="OC101",
    #         creator=self.instructor,
    #         instructor=self.instructor,
    #         published=True
    #     )
        
    #     # Test with a new student
    #     User = get_user_model()
    #     new_student = User.objects.create_user(
    #         username="new_student", 
    #         password="password"
    #     )
    #     self.client.login(username='new_student', password='password')
        
    #     url = reverse('course:course_detail', kwargs={'pk': course_no_dept.pk})
    #     response = self.client.get(url)
        
    #     self.assertEqual(response.status_code, 200)
    #     self.assertTrue(response.context['can_enroll'])

    # def test_course_details_context(self):
    #     """Test that all required context data is present."""
    #     self.client.login(username='student', password='password')
    #     url = reverse('course:course_detail', kwargs={'pk': self.course.pk})
    #     response = self.client.get(url)
        
    #     self.assertEqual(response.status_code, 200)
    #     context = response.context
        
    #     # Check all required context variables
    #     self.assertIn('course', context)
    #     self.assertIn('prerequisites', context)
    #     self.assertIn('is_enrolled', context)
    #     self.assertIn('users_enrolled_count', context)
    #     self.assertIn('course_average_rating', context)
    #     self.assertIn('course_average_rating_star', context)
    #     self.assertIn('feedbacks', context)
    #     self.assertIn('sessions', context)
    #     self.assertIn('session_count', context)
    #     self.assertIn('latest_feedbacks', context)
    #     self.assertIn('tags', context)
    #     self.assertIn('instructor', context)
    #     self.assertIn('user_type', context)
    #     self.assertIn('user_progress', context)
    #     self.assertIn('random_tags', context)
    #     self.assertIn('can_enroll', context)

    # def test_course_statistics(self):
    #     """Test that course statistics are calculated correctly."""
    #     self.client.login(username='student', password='password')
    #     url = reverse('course:course_detail', kwargs={'pk': self.course.pk})
    #     response = self.client.get(url)
        
    #     self.assertEqual(response.status_code, 200)
    #     context = response.context
        
    #     # Test enrollment count
    #     self.assertEqual(context['users_enrolled_count'], 1)
        
    #     # Test average rating calculation
    #     self.assertIsNotNone(context['course_average_rating'])
    #     expected_rating = 4  # (4+4+2+5+5)/5 = 4
    #     self.assertEqual(context['course_average_rating'], expected_rating)
        
    #     # Test rating star percentage
    #     expected_star_percentage = (expected_rating * 100) / 5
    #     self.assertEqual(context['course_average_rating_star'], expected_star_percentage)

    # def test_user_type_identification(self):
    #     """Test that user types are correctly identified."""
    #     # Test for instructor
    #     self.client.login(username='instructor', password='password')
    #     url = reverse('course:course_detail', kwargs={'pk': self.course.pk})
    #     response = self.client.get(url)
    #     self.assertEqual(response.context['user_type'], 'instructor')
        
    #     # Test for student
    #     self.client.login(username='student', password='password')
    #     response = self.client.get(url)
    #     self.assertEqual(response.context['user_type'], 'student')
    
    # def test_random_tags_displayed_correctly(self):
    #     self.client.login(username="student", password="password")
    #     url=reverse('course:course_detail', kwargs={'pk': self.course.pk})
    #     response=self.client.get(url)
    #     random_tags=response.context['random_tags']
    #     self.assertLessEqual(len(random_tags), 4)
    #     self.assertTrue(all(tag in self.course.tags.all() for tag in random_tags))

    # def test_session_count(self):
    #     self.client.login(username="student", password="password")
    #     url=reverse('course:course_detail', kwargs={'pk': self.course.pk})
    #     response=self.client.get(url)
    #     self.assertEqual(response.context['session_count'],1)

    # def test_latest_feedbacks(self):
    #     self.client.login(username="student", password="password")
    #     url=reverse('course:course_detail', kwargs={'pk': self.course.pk})
    #     response=self.client.get(url)
    #     self.assertEqual(response.status_code, 200)
    #     # Access the latest feedbacks from the context
    #     latest_feedbacks = response.context['latest_feedbacks']
    #     # Check that the feedbacks are ordered by `created_at` in descending order
    #     feedback_dates = [feedback.created_at for feedback in latest_feedbacks]
    #     self.assertEqual(feedback_dates, sorted(feedback_dates, reverse=True))

    #     # Check that the number of feedbacks is at most 5
    #     self.assertLessEqual(len(latest_feedbacks), 5)

    # def test_user_progress(self):
    #     self.client.login(username="student", password="password")
    #     url=reverse('course:course_detail', kwargs={'pk': self.course.pk})
    #     response=self.client.get(url)
    #     user_progress=response.context['user_progress']
    #     self.assertEqual(len(user_progress),1)
    #     self.assertEqual(user_progress[0]['user'], self.student)
    #     self.assertEqual(user_progress[0]['progress'], 100)

    # TEST DEF COURSE_ENROLL
    # def test_successfull_enrollment_without_payment(self):
    #     self.course.price = 0
    #     self.course.save()
    #     self.client.login(username="student", password="password")
    #     url=reverse('course:course_enroll', kwargs={'pk': self.course.pk})
    #     response = self.client.get(url)
    #     enrollment=Enrollment.objects.filter(student=self.student, course=self.course, is_active=True).exists()
    #     self.assertTrue(enrollment)
    #     messages = list(get_messages(response.wsgi_request))
    #     self.assertIn('You have been enrolled in Django Basics.', str(messages[0]))

    #     # Check redirect to course detail
    #     self.assertRedirects(response, reverse('course:course_detail', kwargs={'pk': self.course.pk}))

    # def test_successfull_enrollment_with_payment(self):
    #     """Test enrollment process when course requires payment"""
    #     # Delete any existing enrollments/transactions
    #     Enrollment.objects.filter(student=self.student, course=self.course).delete()
    #     Transaction.objects.filter(user=self.student, course=self.course).delete()
        
    #     self.course.price = 100
    #     self.course.save()
        
    #     self.client.login(username="student", password="password")
    #     url = reverse('course:course_enroll', kwargs={'pk': self.course.pk})
    #     response = self.client.post(url)  # Changed to POST request since form submission is required
        
    #     # Check if transaction was created with is_successful=False
    #     transaction = Transaction.objects.filter(
    #         user=self.student, 
    #         course=self.course, 
    #         is_successful=False
    #     ).exists()
    #     self.assertTrue(transaction)
        
    #     # Verify the message
    #     messages = list(get_messages(response.wsgi_request))
    #     self.assertIn('Transaction required. Please complete the payment to activate enrollment.', str(messages[0]))

    #     # Check no enrollment created
    #     enrollment = Enrollment.objects.filter(student=self.student, course=self.course, is_active=True).exists()
    #     self.assertFalse(enrollment)
        
    #     # Verify redirect
    #     self.assertRedirects(response, reverse('course:course_detail', kwargs={'pk': self.course.pk}))

    # def test_unsuccessfull_enrollment_due_to_missing_prerequisites(self):
    #     """Test enrollment fails when prerequisites are not met"""
    #     # Delete any existing enrollments
    #     Enrollment.objects.filter(student=self.student, course=self.course).delete()
    #     Enrollment.objects.filter(student=self.student, course=self.prerequisite_course).delete()
    #     Transaction.objects.filter(user=self.student, course=self.course).delete()
        
    #     self.client.login(username="student", password="password")
    #     url = reverse('course:course_enroll', kwargs={'pk': self.course.pk})
    #     response = self.client.post(url)  # Changed to POST request
        
    #     # Verify no enrollment was created
    #     enrollment = Enrollment.objects.filter(student=self.student, course=self.course).exists()
    #     self.assertFalse(enrollment)
        
    #     # Check error message
    #     messages = list(get_messages(response.wsgi_request))
    #     self.assertIn('You do not meet the prerequisites for this course.', str(messages[0]))
        
    #     # Verify redirect
    #     self.assertRedirects(response, reverse('course:course_detail', kwargs={'pk': self.course.pk}))

    # def test_reactive_existing_enrollment(self):
    #     """Test reactivating an inactive enrollment"""
    #     # First delete any existing enrollments
    #     Enrollment.objects.filter(student=self.student, course=self.course).delete()
    #     Transaction.objects.filter(user=self.student, course=self.course).delete()
        
    #     # Create an inactive enrollment
    #     enrollment = Enrollment.objects.create(
    #         student=self.student, 
    #         course=self.course, 
    #         is_active=False,
    #         date_enrolled=now()
    #     )
        
    #     # Create a successful transaction (since course has no price)
    #     self.course.price = 0
    #     self.course.save()
        
    #     self.client.login(username="student", password="password")
    #     url = reverse('course:course_enroll', kwargs={'pk': self.course.pk})
    #     response = self.client.post(url)  
    #     # Refresh enrollment from database
    #     enrollment.refresh_from_db()
        
    #     # Check enrollment was reactivated
    #     self.assertTrue(enrollment.is_active)
    #     self.assertEqual(enrollment.date_enrolled.date(), now().date())
        
    #     # Verify success message
    #     messages = list(get_messages(response.wsgi_request))
    #     self.assertIn(f'You have been enrolled in {self.course.course_name}', str(messages[0]))
        
    #     # Verify redirect
    #     self.assertRedirects(response, reverse('course:course_detail', kwargs={'pk': self.course.pk}))

    # TEST DEF COURSE_UNENROLL
    # def test_course_unenroll(self):
    #     """Test the course unenrollment process"""
    #     self.client.login(username="student", password="password")
    #     url = reverse('course:course_unenroll', kwargs={'pk': self.course.pk})
        
    #     # First test GET request (confirmation page)
    #     get_response = self.client.get(url)
    #     self.assertEqual(get_response.status_code, 200)
    #     self.assertTemplateUsed(get_response, 'course/course_unenroll.html')
        
    #     # Test POST request (actual unenrollment)
    #     post_response = self.client.post(url)
        
    #     # Refresh enrollment from database
    #     enrollment = Enrollment.objects.get(student=self.student, course=self.course)
    #     transaction = Transaction.objects.get(user=self.student, course=self.course)
        
    #     # Check if enrollment is marked as inactive
    #     self.assertFalse(enrollment.is_active)
    #     self.assertIsNotNone(enrollment.date_unenrolled)
        
    #     # Check if transaction is marked as unsuccessful
    #     self.assertFalse(transaction.is_successful)
        
    #     # Check if completions are deleted
    #     self.assertFalse(
    #         Completion.objects.filter(
    #             user=self.student, 
    #             session__course=self.course
    #         ).exists()
    #     )
        
    #     # Check if session completions are deleted
    #     self.assertFalse(
    #         SessionCompletion.objects.filter(
    #             user=self.student, 
    #             course=self.course
    #         ).exists()
    #     )
        
    #     # Check if course progress is deleted
    #     self.assertFalse(
    #         UserCourseProgress.objects.filter(
    #             user=self.student, 
    #             course=self.course
    #         ).exists()
    #     )
        
    #     # Verify success message
    #     messages = list(get_messages(post_response.wsgi_request))
    #     self.assertIn(f'You have been unenrolled from {self.course.course_name}', str(messages[0]))
        
    #     # Verify redirect to course list
    #     self.assertRedirects(post_response, reverse('course:course_list'))
    
    # # TEST DEF DUPLICATE_COURSE
    # def test_duplicate_course(self):
    #     """Test the course duplication process"""
    #     # Create a PDF file in the course materials
    #     pdf_content = '<iframe src="/media/course_pdf/DJ101/test.pdf#toolbar=0" style="border: none; width: 100%; height: 590px;"></iframe>'
    #     reading_material = ReadingMaterial.objects.create(
    #         material=self.material,
    #         title='PDF Material',
    #         content=pdf_content
    #     )
        
    #     # Call the duplicate_course function
    #     duplicated_course = duplicate_course(self.course)
        
    #     # Test basic course information
    #     self.assertEqual(duplicated_course.course_name, f"{self.course.course_name} - Copy")
    #     self.assertEqual(duplicated_course.description, self.course.description)
    #     self.assertEqual(duplicated_course.instructor, self.course.instructor)
    #     self.assertFalse(duplicated_course.published)
        
    #     # Test unique course code
    #     self.assertTrue(duplicated_course.course_code.startswith(self.course.course_code))
    #     self.assertNotEqual(duplicated_course.course_code, self.course.course_code)
        
    #     # Test sessions were duplicated
    #     original_sessions = self.course.sessions.count()
    #     duplicated_sessions = duplicated_course.sessions.count()
    #     self.assertEqual(original_sessions, duplicated_sessions)
        
    #     # Test materials were duplicated (except assessments)
    #     for original_session, duplicated_session in zip(
    #         self.course.sessions.all(), 
    #         duplicated_course.sessions.all()
    #     ):
    #         # Check session name and order
    #         self.assertEqual(original_session.name, duplicated_session.name)
    #         self.assertEqual(original_session.order, duplicated_session.order)
            
    #         # Check materials (excluding assessments)
    #         original_materials = original_session.materials.exclude(material_type='assessments')
    #         duplicated_materials = duplicated_session.materials.exclude(material_type='assessments')
            
    #         self.assertEqual(original_materials.count(), duplicated_materials.count())
            
    #         for original_material, duplicated_material in zip(
    #             original_materials.order_by('order'),
    #             duplicated_materials.order_by('order')
    #         ):
    #             self.assertEqual(original_material.material_type, duplicated_material.material_type)
    #             self.assertEqual(original_material.order, duplicated_material.order)
    #             self.assertEqual(original_material.title, duplicated_material.title)
                
    #             # Check associated reading materials
    #             if original_material.material_type != 'assessments':
    #                 original_reading = ReadingMaterial.objects.get(id=original_material.material_id)
    #                 duplicated_reading = ReadingMaterial.objects.get(id=duplicated_material.material_id)
                    
    #                 self.assertEqual(original_reading.title, duplicated_reading.title)
                    
    #                 # Check if PDF content was properly duplicated with new course code
    #                 if 'course_pdf' in original_reading.content:
    #                     self.assertIn(duplicated_course.course_code, duplicated_reading.content)
    #                     self.assertNotIn(self.course.course_code, duplicated_reading.content)
        
    #     # Test prerequisites and tags were copied
    #     self.assertEqual(
    #         set(self.course.prerequisites.all()), 
    #         set(duplicated_course.prerequisites.all())
    #     )
    #     self.assertEqual(
    #         set(self.course.tags.all()), 
    #         set(duplicated_course.tags.all())
    #     )

    # def test_duplicate_course_name_uniqueness(self):
    #     """Test that duplicate courses get unique names"""
    #     # Create first duplicate
    #     first_duplicate = duplicate_course(self.course)
    #     self.assertEqual(first_duplicate.course_name, f"{self.course.course_name} - Copy")
        
    #     # Create second duplicate
    #     second_duplicate = duplicate_course(self.course)
    #     self.assertEqual(second_duplicate.course_name, f"{self.course.course_name} - Copy (2)")
        
    #     # Create third duplicate
    #     third_duplicate = duplicate_course(self.course)
    #     self.assertEqual(third_duplicate.course_name, f"{self.course.course_name} - Copy (3)")

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
=======
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
>>>>>>> 0e2e5c19de0ee56ba22f4ec0dbadc55ec9d571bb
