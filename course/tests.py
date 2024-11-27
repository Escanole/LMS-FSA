from django.urls import reverse
from .models import Course, Enrollment, Transaction, Session, SessionCompletion, ReadingMaterial, CourseMaterial, Tag, Topic
from django.contrib.auth import get_user_model
from certification.models import Certification  # Assuming this is where your Certification model is defined
from django.utils import timezone
from django.test import TestCase, Client
from django.contrib.auth import get_user_model
from course.models import Course, Session, ReadingMaterial, CourseMaterial
from io import BytesIO
from django.core.files.uploadedfile import SimpleUploadedFile

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

        self.edit_url = reverse("course:course_content_edit", kwargs={"pk": self.course.pk, "session_id": self.session.pk})

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

        self.edit_url = reverse("course:course_content_edit", kwargs={"pk": self.course.pk, "session_id": self.session.pk})

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
        Course.objects.create(course_name="Introduction ", description="Basic programming concepts", course_code="CS101")

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
        empty_course = Course.objects.create(course_name="Empty Course", description="No sessions", course_code="EMPTY101")

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
        self.assertNotEqual(certification_user.id, certification_another_user.id)  # Ensure they are different certifications

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
                course_name=f"Course {i+1}",
                description="This is a test course.",
                course_code=f"COURSE{i+1}",
                published=True  # Ensure all courses are published
            )
            session = Session.objects.create(course=course, name=f"Session for Course {i+1}", order=1)
            reading_material = ReadingMaterial.objects.create(
                title=f"Reading Material for Course {i+1}",
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
        course2.tags.add(tag_python)   # Course 2 also has the Python tag
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
