from django.shortcuts import render, redirect, get_object_or_404
from course.models import Course
from department.models import Department
from django.http import JsonResponse
from django.views.decorators.csrf import csrf_exempt
import json
from assessments.models import Assessment


def department_course_list(request):
    search_query = request.GET.get('search', '')

    # Filter departments based on search query
    if search_query:
        departments = Department.objects.filter(name__icontains=search_query)
    else:
        departments = Department.objects.all()

    # Retrieve only unassigned courses for the available courses list
    courses = Course.objects.filter(department__isnull=True)

    return render(request, 'department_course_list.html', {
        'departments': departments,
        'courses': courses,
        'search_query': search_query
    })


@csrf_exempt
def add_course_to_department(request):
    if request.method == 'POST':
        try:
            data = json.loads(request.body)
            department_id = data.get('department_id')
            course_id = data.get('course_id')

            # Check if both department_id and course_id are provided
            if not department_id or not course_id:
                return JsonResponse({'status': 'error', 'message': 'Department ID and Course ID are required.'})

            # Fetch the department and course objects
            department = get_object_or_404(Department, id=department_id)
            course = get_object_or_404(Course, id=course_id)

            # Use add() to add the course to the department's course set
            department.courses.add(course)

            return JsonResponse({'status': 'success', 'message': 'Course added successfully.'})

        except json.JSONDecodeError:
            return JsonResponse({'status': 'error', 'message': 'Invalid JSON data.'})
        except Exception as e:
            return JsonResponse({'status': 'error', 'message': str(e)})

    return JsonResponse({'status': 'error', 'message': 'Invalid request method.'})


@csrf_exempt
def remove_course_from_department(request):
    if request.method == 'POST':
        data = json.loads(request.body)
        department_id = data.get('department_id')
        course_id = data.get('course_id')

        try:
            course = get_object_or_404(Course, id=course_id)
            department = get_object_or_404(Department, id=department_id)
            if not department.courses.filter(id=course.id).exists():
                return JsonResponse({'status': 'error', 'message': 'Course not found in department'})

            department.courses.remove(course)

            return JsonResponse({'status': 'success', 'course_name': course.course_name})
        except Exception as e:
            return JsonResponse({'status': 'error', 'message': str(e)})

    return JsonResponse({'status': 'error', 'message': 'Invalid request'})


@csrf_exempt
def get_assessments_for_course(request, course_id):
    if request.method == 'GET':
        # Fetch the course object
        course = get_object_or_404(Course, id=course_id)

        # Get all assessments related to this course
        assessments = Assessment.objects.filter(course=course)

        assessments_data = [{'id': assessment.id, 'name': assessment.title} for assessment in assessments]
        return JsonResponse({'status': 'success', 'assessments': assessments_data})

    return JsonResponse({'status': 'error', 'message': 'Invalid request method.'})
