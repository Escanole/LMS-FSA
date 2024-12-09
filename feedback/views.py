from django.shortcuts import render, redirect, get_object_or_404
from .forms import InstructorFeedbackForm, CourseFeedbackForm, TrainingProgramFeedbackForm
from .models import InstructorFeedback, CourseFeedback, TrainingProgramFeedback
from course.models import Course
from training_program.models import TrainingProgram
from django.contrib.auth import get_user_model
from module_group.models import ModuleGroup, Module
from django.contrib import messages
from django.core.paginator import Paginator
from django.db.models import F, FloatField, ExpressionWrapper, Count, Q, Avg
from django.http import Http404, JsonResponse


User = get_user_model()


def feedback_list(request):
    # Fetch all courses and instructors
    courses = Course.objects.all()
    course_instructors = courses.values_list('instructor', flat=True).distinct()
    instructors = User.objects.filter(id__in=course_instructors)

    # Get the query parameters for filtering and searching
    search_term = request.GET.get('search', '').strip().lower()
    course_filter = request.GET.get('course', '').strip().lower()
    instructor_search = request.GET.get('instructor_search', '').strip().lower()
    instructor_filter = request.GET.get('instructor', '').strip().lower()
    course_instructor_filter = request.GET.get('course_instructor', '').strip().lower()

    # Sorting parameters for course feedback
    course_sort_order = request.GET.get('course_sort', 'asc')  # Default to ascending
    instructor_sort_order = request.GET.get('instructor_sort', 'asc')  # Default to ascending

    # Filter course feedback
    course_feedbacks_all = CourseFeedback.objects.all()

    if search_term:
        course_feedbacks_all = course_feedbacks_all.filter(
            Q(course__course_name__icontains=search_term) |
            Q(course_comment__icontains=search_term) |
            Q(material_comment__icontains=search_term)
        )

    if course_filter:
        course_feedbacks_all = course_feedbacks_all.filter(course__course_name__icontains=course_filter)

    # Annotate each course feedback with the average rating
    course_feedbacks_all = course_feedbacks_all.annotate(
        average_rating=(
            (F('course_material') + F('clarity_of_explanation') +
            F('course_structure') + F('practical_applications') +
            F('support_materials')) / 5.0
        )
    )

    # Sorting course feedback by average rating
    if course_sort_order == 'desc':
        course_feedbacks_all = course_feedbacks_all.order_by('-average_rating')
    else:
        course_feedbacks_all = course_feedbacks_all.order_by('average_rating')

    # Pagination for Course Feedback Tab
    course_page_number = request.GET.get('course_page', 1)
    course_paginator = Paginator(course_feedbacks_all, 8)
    try:
        course_page_obj = course_paginator.page(course_page_number)
    except:
        course_page_obj = course_paginator.page(1)

    # Filter instructor feedback
    instructor_feedbacks_all = InstructorFeedback.objects.all()

    if instructor_search:
        instructor_feedbacks_all = instructor_feedbacks_all.filter(
            Q(instructor__username__icontains=instructor_search) |
            Q(comments__icontains=instructor_search)
        )

    if instructor_filter:
        instructor_feedbacks_all = instructor_feedbacks_all.filter(instructor__username__icontains=instructor_filter)

    if course_instructor_filter:
        instructor_feedbacks_all = instructor_feedbacks_all.filter(course__course_name__icontains=course_instructor_filter)

    # Annotate each instructor feedback with the average rating
    instructor_feedbacks_all = instructor_feedbacks_all.annotate(
        average_rating=(
            (F('course_knowledge') + F('communication_skills') +
            F('approachability') + F('engagement') + F('professionalism')) / 5.0
        )
    )

    # Sorting instructor feedback by average rating
    if instructor_sort_order == 'desc':
        instructor_feedbacks_all = instructor_feedbacks_all.order_by('-average_rating')
    else:
        instructor_feedbacks_all = instructor_feedbacks_all.order_by('average_rating')

    # Pagination for Instructor Feedback Tab
    instructor_page_number = request.GET.get('instructor_page', 1)
    instructor_paginator = Paginator(instructor_feedbacks_all, 8)
    try:
        instructor_page_obj = instructor_paginator.page(instructor_page_number)
    except:
        instructor_page_obj = instructor_paginator.page(1)

    # Render data for all tabs
    return render(request, 'feedback_list.html', {
        'courses': courses,
        'instructors': instructors,
        'course_page_obj': course_page_obj,
        'instructor_page_obj': instructor_page_obj,
        'course_feedbacks_all': course_page_obj.object_list,
        'instructor_feedbacks_all': instructor_page_obj.object_list,
    })




def feedback_chart_data(request):
    selected_course_id = request.GET.get('course', 'all')
    selected_instructor_id = request.GET.get('instructor', 'all')

    # Prepare data for Course Criteria (Stacked Bar Chart)
    course_criteria = ['course_material', 'practical_applications', 'clarity_of_explanation',
                       'course_structure', 'support_materials']
    course_feedbacks = CourseFeedback.objects.filter(
        course_id=selected_course_id) if selected_course_id != 'all' else CourseFeedback.objects.all()
    course_criteria_counts = {criterion: {star: 0 for star in range(1, 6)} for criterion in course_criteria}
    course_avg_rating_counts = {star: 0 for star in range(1, 6)}

    for feedback in course_feedbacks:
        for criterion in course_criteria:
            rating = getattr(feedback, criterion, 0)
            if 1 <= rating <= 5:
                course_criteria_counts[criterion][rating] += 1
        avg_rating = feedback.average_rating()
        if 1 <= avg_rating <= 5:
            course_avg_rating_counts[int(avg_rating)] += 1

    # Prepare data for Instructor Criteria (Stacked Bar Chart)
    instructor_criteria = ['course_knowledge', 'communication_skills', 'approachability',
                           'engagement', 'professionalism']
    instructor_feedbacks = InstructorFeedback.objects.filter(
        instructor=selected_instructor_id) if selected_instructor_id != 'all' else InstructorFeedback.objects.all()
    instructor_criteria_counts = {criterion: {star: 0 for star in range(1, 6)} for criterion in instructor_criteria}
    instructor_avg_rating_counts = {star: 0 for star in range(1, 6)}

    for feedback in instructor_feedbacks:
        for criterion in instructor_criteria:
            rating = getattr(feedback, criterion, 0)
            if 1 <= rating <= 5:
                instructor_criteria_counts[criterion][rating] += 1
        avg_rating = feedback.average_rating()
        if 1 <= avg_rating <= 5:
            instructor_avg_rating_counts[int(avg_rating)] += 1

    return JsonResponse({
        'course': {
            'criteria_counts': course_criteria_counts,
            'avg_rating_counts': course_avg_rating_counts,
        },
        'instructor': {
            'criteria_counts': instructor_criteria_counts,
            'avg_rating_counts': instructor_avg_rating_counts,
        }
    })


def give_instructor_feedback(request, instructor_id, course_id):
    # Retrieve the instructor and course based on the provided IDs
    try:
        instructor = User.objects.get(pk=instructor_id)
        course = Course.objects.get(pk=course_id)
    except (User.DoesNotExist, Course.DoesNotExist):
        raise Http404("Instructor or Course not found")

    if request.method == 'POST':
        form = InstructorFeedbackForm(request.POST)
        if form.is_valid():
            # Save feedback but do not commit yet
            feedback = form.save(commit=False)
            feedback.student = request.user  # Set the current logged-in user as the student
            feedback.instructor = instructor  # Associate the feedback with the instructor
            feedback.course = course  # Associate the feedback with the specific course
            feedback.save()  # Save the feedback to the database
            return redirect('feedback:feedback_success')  # Redirect to a success page
    else:
        # If GET request, create an empty form
        form = InstructorFeedbackForm()

    return render(request, 'feedback_Instructor.html', {'form': form, 'instructor': instructor, 'course': course})


def give_course_feedback(request, course_id):
    course = get_object_or_404(Course, id=course_id)

    if request.method == 'POST':
        form = CourseFeedbackForm(request.POST)
        if form.is_valid():
            # Create a new CourseFeedback object
            feedback = form.save(commit=False)
            feedback.student = request.user
            feedback.course = course

            # Save both comments: course_comment and material_comment
            feedback.course_comment = form.cleaned_data.get('course_comment')
            feedback.material_comment = form.cleaned_data.get('material_comment')

            feedback.save()

            messages.success(request, 'Your feedback has been submitted successfully.')
            return redirect('course:course_detail', pk=course.id)
        else:
            messages.error(request, 'There was an error with your submission. Please check the form and try again.')
    else:
        form = CourseFeedbackForm()

    # Fetch the 5 newest feedback entries for this course
    latest_feedbacks = CourseFeedback.objects.filter(course=course).order_by('-created_at')[:5]

    return render(request, 'feedback_Course.html', {
        'form': form,
        'course': course,
        'latest_feedbacks': latest_feedbacks
    })


def give_training_program_feedback(request, training_program_id):
    training_program = TrainingProgram.objects.get(pk=training_program_id)
    if request.method == 'POST':
        form = TrainingProgramFeedbackForm(request.POST)
        if form.is_valid():
            feedback = form.save(commit=False)
            feedback.student = request.user
            feedback.training_program = training_program
            feedback.save()
            return redirect('feedback:feedback_success')
    else:
        form = TrainingProgramFeedbackForm()
    return render(request, 'feedback_Program.html', {'form': form, 'training_program': training_program})


def feedback_success(request):
    return render(request, 'feedback_success.html')


def instructor_feedback_detail(request, feedback_id):
    feedback = InstructorFeedback.objects.get(pk=feedback_id)
    return render(request, 'feedback_detail.html', {'feedback': feedback, 'type': 'Instructor'})


def course_feedback_detail(request, feedback_id):
    feedback = CourseFeedback.objects.get(pk=feedback_id)
    return render(request, 'feedback_detail.html', {'feedback': feedback, 'type': 'Course'})


def program_feedback_detail(request, feedback_id):
    try:
        feedback = TrainingProgramFeedback.objects.get(pk=feedback_id)
    except TrainingProgramFeedback.DoesNotExist:
        raise Http404("Feedback does not exist")
    return render(request, 'feedback_detail.html', {'feedback': feedback, 'type': 'Training Program'})


def course_all_feedback(request, course_id):
    course = get_object_or_404(Course, id=course_id)
    all_feedbacks = CourseFeedback.objects.filter(course=course)

    # Calculate rating distribution
    total_feedbacks = all_feedbacks.count()
    rating_distribution = []

    if total_feedbacks > 0:  # 31/10
        for rating in range(5, 0, -1):  # 5 to 1 in reverse order
            count = len(
                [f for f in all_feedbacks if (f.average_rating() - rating) < 1 and (f.average_rating() - rating) >= 0])
            percentage = (count / total_feedbacks) * 100
            rating_distribution.append({
                'rating': rating,
                'count': count,
                'percentage': percentage
            })

        # Calculate overall average rating
        total_rating = sum(feedback.average_rating() for feedback in all_feedbacks)
        course_average_rating = total_rating / total_feedbacks
        course_average_rating_star = course_average_rating * 20  # Convert to percentage (0-100)
    else:
        course_average_rating = None
        course_average_rating_star = 0
        rating_distribution = [{'rating': i, 'count': 0, 'percentage': 0} for i in range(5, 0, -1)]

    sort_by = request.GET.get('sort', 'recent')
    all_feedbacks = all_feedbacks.annotate(helpful_count=Count('helpful_rate'))

    if sort_by == 'helpful':
        all_feedbacks = all_feedbacks.order_by('-helpful_count', '-created_at')
    else:
        all_feedbacks = all_feedbacks.order_by('-created_at')

    selected_rating = request.GET.get('rating', None)

    all_feedbacks = all_feedbacks.annotate(
        average_rating=ExpressionWrapper(
            (F('course_material') + F('clarity_of_explanation') +
             F('course_structure') + F('practical_applications') +
             F('support_materials')) / 5.0,
            output_field=FloatField()
        )
    )

    if selected_rating:
        try:
            selected_rating = int(selected_rating)
            all_feedbacks = all_feedbacks.filter(average_rating__gte=selected_rating,
                                                 average_rating__lt=selected_rating + 1).order_by('-created_at')
        except ValueError:
            pass

    paginator = Paginator(all_feedbacks, 3)
    page_number = request.GET.get('page')
    page_obj = paginator.get_page(page_number)

    return render(request, 'feedback_course_list.html', {
        'course': course,
        'page_obj': page_obj,
        'course_average_rating': course_average_rating,
        'course_average_rating_star': course_average_rating_star,
        'range': {1, 2, 3, 4, 5},
        'selected_rating': selected_rating,
        'sort_by': sort_by,
        'total_feedbacks': total_feedbacks,
        'rating_distribution': rating_distribution,  # Added this to the context
    })


def helpful_rate(request, pk):
    feedback = get_object_or_404(CourseFeedback, pk=pk)
    print(feedback.id)
    if request.user in feedback.helpful_rate.all():
        feedback.helpful_rate.remove(request.user)
    else:
        feedback.helpful_rate.add(request.user)
    return redirect('feedback:course_all_feedback', course_id=feedback.course.id)



def combined_feedback(request, course_id):
    course = get_object_or_404(Course, id=course_id)
    instructor = course.instructor
    if request.method == 'POST':
        course_form = CourseFeedbackForm(request.POST)
        instructor_form = InstructorFeedbackForm(request.POST)

        # Check if both forms are valid
        if course_form.is_valid() and instructor_form.is_valid():
            print("Get IN")
            # Save course feedback
            course_feedback = course_form.save(commit=False)
            course_feedback.student = request.user
            course_feedback.course = course
            course_feedback.course_comment = course_form.cleaned_data.get('course_comment')
            course_feedback.material_comment = course_form.cleaned_data.get('material_comment')
            course_feedback.save()

            # Save instructor feedback
            instructor_feedback = instructor_form.save(commit=False)
            instructor_feedback.student = request.user
            instructor_feedback.instructor = instructor
            instructor_feedback.course = course
            instructor_feedback.save()

            messages.success(request, 'Both course and instructor feedback submitted successfully.')
            return redirect('student_portal:course_detail', pk=course.id)
        else:
            messages.error(request, 'Please check your feedback forms and try again.')
    else:
        course_form = CourseFeedbackForm()
        instructor_form = InstructorFeedbackForm()
    context = {
        'course': course,
        'instructor': instructor,
        'course_form': course_form,
        'instructor_form': instructor_form,
    }

    return render(request, 'feedback_course_instructor.html', context)


def all_feedback(request):
    course_feedbacks = CourseFeedback.objects.select_related('course', 'student').annotate(
        average_rating=(
            (F('course_material') + F('clarity_of_explanation') +
             F('course_structure') + F('practical_applications') +
             F('support_materials')) / 5.0
        )
    ).order_by('-created_at')

    instructor_feedbacks = InstructorFeedback.objects.select_related('instructor', 'course', 'student').annotate(
        average_rating=(
            (F('course_knowledge') + F('communication_skills') +
             F('approachability') + F('engagement') + F('professionalism')) / 5.0
        )
    ).order_by('-created_at')

    return JsonResponse({
        'course_feedbacks': [{
            'id': f.id,
            'course_name': f.course.course_name,
            'average_rating': float(f.average_rating),
            'material_comment': f.material_comment,
            'course_comment': f.course_comment,
            'created_at': f.created_at.strftime('%Y-%m-%d %H:%M:%S')
        } for f in course_feedbacks],
        'instructor_feedbacks': [{
            'id': f.id,
            'instructor_name': f.instructor.username,
            'course_name': f.course.course_name,
            'average_rating': float(f.average_rating),
            'comments': f.comments,
            'created_at': f.created_at.strftime('%Y-%m-%d %H:%M:%S')
        } for f in instructor_feedbacks]
    })