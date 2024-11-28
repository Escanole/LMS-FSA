from django.shortcuts import render, get_object_or_404
from course.models import Course, Enrollment, Session, Completion, Tag, CourseMaterial, MaterialViewingDuration
from django.db.models import Count, F, Q, Sum, Avg
from module_group.models import ModuleGroup
from user.models import User, Student, Profile
from department.models import Department
from collections import Counter
from django.http import JsonResponse
from activity.models import UserActivityLog
from django.db.models.functions import TruncDate
from datetime import datetime, timedelta
from django.utils.dateparse import parse_date
from django.contrib.auth.decorators import login_required
from django.utils import timezone
from django.shortcuts import render
from django.http import Http404
from collections import defaultdict
import calendar
import json


@login_required
def user_duration_login(request):
    user = request.user
    activity_logs = UserActivityLog.objects.filter(user=user).order_by('activity_timestamp')

    login_times = []
    logout_times = []

    # Lấy thời gian đăng nhập và đăng xuất
    for log in activity_logs:
        if log.activity_type == 'login':
            login_times.append(log.activity_timestamp)
        elif log.activity_type == 'logout':
            logout_times.append(log.activity_timestamp)

    # Tính toán thời gian phiên làm việc
    session_durations = []
    for login_time in login_times:
        # Tìm lần đăng xuất gần nhất sau thời gian đăng nhập
        logout_time = next((lt for lt in logout_times if lt > login_time), None)
        if logout_time:
            # Tính toán thời gian phiên
            duration = logout_time - login_time

            # Định dạng lại thời gian phiên thành chuỗi "X days, Y hours, Z minutes"
            days, seconds = duration.days, duration.seconds
            hours = seconds // 3600
            minutes = (seconds // 60) % 60

            formatted_duration = f"{days} days, {hours} hours, {minutes} minutes"
            total_minutes = duration.total_seconds() // 60  # Tính tổng phút

            session_durations.append({
                'login_time': login_time,
                'logout_time': logout_time,
                'duration': formatted_duration,  # Lưu trữ dưới dạng chuỗi
                'total_minutes': total_minutes,  # Lưu trữ tổng phút
            })
    session_durations = session_durations[-10:]
    return render(request, 'reports/user/user_duration_login.html', {
        'session_durations': session_durations,
    })


@login_required
def login_frequency_report(request):
    from_date = request.GET.get('from_date', '')
    to_date = request.GET.get('to_date', '')

    today = timezone.now()
    start_date = today - timedelta(days=30)

    if from_date:
        from_date_parsed = parse_date(from_date)
        if from_date_parsed:
            start_date = from_date_parsed

    if to_date:
        to_date_parsed = parse_date(to_date)
        if to_date_parsed:
            end_date = to_date_parsed
        else:
            end_date = today
    else:
        end_date = today

    # Tổng hợp dữ liệu đăng nhập theo ngày trong khoảng thời gian đã chọn
    login_data = (
        UserActivityLog.objects.filter(
            user=request.user,
            activity_type='login',
            activity_timestamp__range=[start_date, end_date]
        )
        .annotate(day=TruncDate('activity_timestamp'))
        .values('day')
        .annotate(login_count=Count('log_id'))
        .order_by('day')
    )

    times = [entry['day'].strftime('%Y-%m-%d') for entry in login_data]
    counts = [entry['login_count'] for entry in login_data]

    title = "Login frequency in the last 30 days"
    back_to_month = False

    return render(request, 'reports/user/login_frequency_report.html', {
        'times': times,
        'counts': counts,
        'title': title,
        'login_frequency': login_data,
        'from_date': from_date,
        'to_date': to_date,
        'back_to_month': back_to_month,
    })


@login_required
def user_statistics_report(request):
    module_groups = ModuleGroup.objects.all()
    today = timezone.localtime().date()
    start_of_month = today.replace(day=1)
    current_month = today.strftime("%B %Y")

    # Lấy tham số ngày đăng nhập từ URL nếu có
    login_date_str = request.GET.get('login_date')
    selected_users = []

    # Kiểm tra và chuyển đổi login_date_str thành ngày
    if login_date_str:
        try:
            login_date = datetime.strptime(login_date_str, '%Y-%m-%d').date()
            # Lọc người dùng đã đăng nhập vào ngày được chọn
            selected_users = UserActivityLog.objects.filter(
                activity_type='login',
                activity_timestamp__date=login_date,
                user__is_superuser=False
            ).values('user__username', 'user__email', 'user__date_joined').distinct()
        except ValueError:
            login_date = None  # Ngày không hợp lệ, bỏ qua

    # Tổng hợp số lần đăng nhập hàng ngày cho tháng hiện tại
    daily_login_counts = (
        UserActivityLog.objects.filter(
            activity_type='login',
            activity_timestamp__gte=start_of_month,
            activity_timestamp__lt=today + timezone.timedelta(days=1),
            user__is_superuser=False
        )
        .annotate(login_date=TruncDate('activity_timestamp'))
        .values('login_date')
        .annotate(user_count=Count('user', distinct=True))
        .order_by('login_date')
    )

    # Chuyển đổi dữ liệu cho biểu đồ
    login_dates = [entry['login_date'].strftime('%Y-%m-%d') for entry in daily_login_counts]
    user_counts = [entry['user_count'] for entry in daily_login_counts]

    # Truy vấn tất cả người dùng đăng nhập trong tháng hiện tại
    users = User.objects.filter(date_joined__gte=start_of_month, is_superuser=False)

    return render(request, 'reports/user/user_statistics_report.html',
                  {
                      'module_groups': module_groups,
                      'login_dates': login_dates,
                      'user_counts': user_counts,
                      'current_month': current_month,
                      'users': users,
                      'selected_users': selected_users,
                      'selected_date': login_date_str  # Truyền ngày đã chọn
                  })


def student_id_report(request):
    students = Student.objects.all()
    student_cohorts = {}
    total_students = 0  # Tổng số sinh viên

    for student in students:
        if student.student_code and student.student_code.startswith("SE"):
            cohort = student.student_code[2:4]
            student_cohorts.setdefault(cohort, []).append(student)

    labels = [f"SE{cohort}" for cohort in student_cohorts.keys()]  # Thêm 'SE' vào nhãn
    data = [len(students) for students in student_cohorts.values()]
    total_students = sum(data)

    # Tạo bảng tổng kết
    cohort_summary = [
        {
            'label': label,
            'count': count,
            'percentage': (count / total_students) * 100 if total_students > 0 else 0
        }
        for label, count in zip(labels, data)
    ]

    context = {
        'labels': labels,
        'data': data,
        'cohort_summary': cohort_summary,
    }

    return render(request, 'reports/user/student_id_report.html', context)


def get_students_by_cohort(request, cohort):
    """Lấy danh sách sinh viên theo cohort cho yêu cầu AJAX"""
    students = Student.objects.filter(student_code__startswith=f"SE{cohort}")
    student_data = [{"name": student.user.username, "student_code": student.student_code} for student in students]
    return JsonResponse(student_data, safe=False)


def role_report(request):
    # Lấy số lượng người dùng theo vai trò
    role_counts = Profile.objects.values('role__role_name').annotate(user_count=Count('user')).order_by(
        'role__role_name')

    context = {
        'role_counts': role_counts,
    }

    return render(request, 'reports/user/role_report.html', context)


@login_required
def user_overview_report(request):
    # Lấy tất cả người dùng (trừ superusers)
    users = User.objects.exclude(is_superuser=True)

    return render(request, 'reports/user/user_overview_report.html', {'users': users})


@login_required
def report_dashboard(request):
    module_groups = ModuleGroup.objects.all()
    return render(request, 'reports/dashboard_report.html',
                  {
                      'module_groups': module_groups,
                  })


@login_required
def course_overview_report(request):
    module_groups = ModuleGroup.objects.all()
    courses = Course.objects.all()
    return render(request, 'reports/course_overview_report.html',
                  {'courses': courses, 'module_groups': module_groups,
                   })


@login_required
def student_enrollment_report(request):
    enrollments = Enrollment.objects.select_related('student', 'course').all()
    return render(request, 'reports/student_enrollment_report.html', {'enrollments': enrollments})


@login_required
def course_completion_report(request):
    user = request.user
    course_progress = {course: course.get_completion_percent(user) for course in Course.objects.all()}
    return render(request, 'reports/course_completion_report.html', {'course_progress': course_progress})


@login_required
def session_overview_report(request):
    sessions = Session.objects.select_related('course').all()
    return render(request, 'reports/session_overview_report.html', {'sessions': sessions})


@login_required
def material_usage_report(request):
    completions = Completion.objects.select_related('session', 'material', 'user').all()
    return render(request, 'reports/material_usage_report.html', {'completions': completions})


def get_quarter(month):
    if 1 <= month <= 3:
        return 1
    elif 4 <= month <= 6:
        return 2
    elif 7 <= month <= 9:
        return 3
    else:
        return 4


@login_required
def enrollment_trends_report(request):
    all_courses = Course.objects.all()

    # Get current year and month if not specified
    current_date = timezone.now()
    year = int(request.GET.get('year', current_date.year))
    month = request.GET.get('month')  # Optional month filter

    # Get course_id from request, default to first course if none selected
    course_id = request.GET.get('course_id')
    if not course_id and all_courses.exists():
        course_id = all_courses.first().id
    elif not all_courses.exists():
        raise Http404("No courses available.")

    course = get_object_or_404(Course, pk=course_id)

    # Initialize data dictionaries
    enrollment_data = {month: 0 for month in range(1, 13)}
    unenrollment_data = {month: 0 for month in range(1, 13)}
    weekly_enrollment_data = defaultdict(int)
    weekly_unenrollment_data = defaultdict(int)

    # Base query for enrollments
    enrollments_query = Enrollment.objects.filter(
        course_id=course_id,
        date_enrolled__year=year,
        is_active=True
    )

    unenrollments_query = Enrollment.objects.filter(
        course_id=course_id,
        date_enrolled__year=year,
        is_active=False
    )

    if month:
        # If month is selected, show weekly data for that month
        month = int(month)
        enrollments_query = enrollments_query.filter(date_enrolled__month=month)
        unenrollments_query = unenrollments_query.filter(date_enrolled__month=month)

        _, num_days = calendar.monthrange(year, month)
        week_ranges = []
        weekly_enrollment_data = {}
        weekly_unenrollment_data = {}

        current_start = 1
        while current_start <= num_days:
            current_end = min(current_start + 6, num_days)  # 7-day week
            week_label = f"Day {current_start}-{current_end}"
            week_ranges.append((current_start, current_end))
            weekly_enrollment_data[week_label] = 0
            weekly_unenrollment_data[week_label] = 0
            current_start += 7

        # Group enrollments by weekly ranges
        for enrollment in enrollments_query:
            day_of_month = enrollment.date_enrolled.day
            for start, end in week_ranges:
                if start <= day_of_month <= end:
                    week_label = f"Day {start}-{end}"
                    weekly_enrollment_data[week_label] += 1
                    break

        for unenrollment in unenrollments_query:
            day_of_month = unenrollment.date_enrolled.day
            for start, end in week_ranges:
                if start <= day_of_month <= end:
                    week_label = f"Day {start}-{end}"
                    weekly_unenrollment_data[week_label] += 1
                    break

        # Prepare chart data
        chart_labels = list(weekly_enrollment_data.keys())
        chart_enrollment_data = list(weekly_enrollment_data.values())
        chart_unenrollment_data = list(weekly_unenrollment_data.values())
    else:
        # Show monthly data when no month is selected
        for enrollment in enrollments_query:
            enrollment_data[enrollment.date_enrolled.month] += 1

        for unenrollment in unenrollments_query:
            unenrollment_data[unenrollment.date_enrolled.month] += 1

        chart_labels = ['Jan', 'Feb', 'Mar', 'Apr', 'May', 'Jun', 'Jul', 'Aug', 'Sep', 'Oct', 'Nov', 'Dec']
        chart_enrollment_data = list(enrollment_data.values())
        chart_unenrollment_data = list(unenrollment_data.values())

    context = {
        'course': course,
        'course_id': int(course_id),
        'year': year,
        'selected_month': month,
        'enrollment_data': enrollment_data,
        'unenrollment_data': unenrollment_data,
        'all_courses': all_courses,
        'chart_labels': json.dumps(chart_labels),  # Convert to JSON
        'chart_enrollment_data': json.dumps(chart_enrollment_data),  # Convert to JSON
        'chart_unenrollment_data': json.dumps(chart_unenrollment_data),  # Convert to JSON
        'months': [
            {'number': i, 'name': calendar.month_name[i]}
            for i in range(1, 13)
        ],
        # Add data for table
        'table_data': zip(chart_labels, chart_enrollment_data, chart_unenrollment_data)
    }

    return render(request, 'reports/enrollment_trends_report.html', context)

@login_required
def material_type_distribution_report(request):
    materials = CourseMaterial.objects.values('material_type').annotate(count=Count('id'))
    return render(request, 'reports/material_type_distribution_report.html', {'materials': materials})


@login_required
def tag_report(request):
    tags = Tag.objects.annotate(course_count=Count('courses'))
    return render(request, 'reports/tag_report.html', {'tags': tags})


@login_required
def user_progress_report(request):
    user = request.user
    progress = Completion.objects.filter(user=user).select_related('session', 'material')
    return render(request, 'reports/user_progress_report.html', {'progress': progress})


@login_required
def instructor_performance_report(request):
    instructors = Course.objects.values('instructor__username', 'course_name').annotate(
        enrollment_count=Count('enrollments')
    ).order_by('instructor__username', '-enrollment_count')

    return render(request, 'reports/instructor_performance_report.html', {'instructors': instructors})


def round_to_nearest_half(hour):
    return round(hour * 2) / 2

def course_duration_report(request):
    # Get the selected course from the GET parameters
    selected_course_id = request.GET.get('course', None)

    # Query to group durations by user and course
    user_course_durations = (
        MaterialViewingDuration.objects
        .values('material__session__course', 'user')  # Group by course and user
        .annotate(total_time=Sum(F('time_spent')))  # Sum the duration for each group
    )

    # Filter by selected course if provided
    if selected_course_id:
        user_course_durations = user_course_durations.filter(
            material__session__course=selected_course_id
        )

    # Prepare data for rendering
    course_durations = {}
    for entry in user_course_durations:
        course_id = entry['material__session__course']
        user_id = entry['user']
        total_time = entry['total_time']

        # Convert time_spent (which is timedelta) to hours (float)
        total_hours = total_time.total_seconds() / 3600 if total_time else 0

        # Round to the nearest 0.5 hour
        rounded_hours = round_to_nearest_half(total_hours)

        if course_id not in course_durations:
            course_durations[course_id] = {}

        # Store rounded duration by user for the course in hours
        course_durations[course_id][user_id] = rounded_hours

    # Group users by the same time spent on the course
    grouped_durations = {}
    for course_id, user_data in course_durations.items():
        for user_id, total_time in user_data.items():
            if total_time not in grouped_durations:
                grouped_durations[total_time] = 0
            grouped_durations[total_time] += 1  # Count how many users spent this amount of time

    # Prepare data for the chart
    chart_labels = [f'{time} hours' for time in grouped_durations.keys()]
    chart_data = list(grouped_durations.values())

    # Optionally, retrieve course and user details for display
    all_courses = Course.objects.in_bulk(course_durations.keys())
    all_users = User.objects.in_bulk({user_id for user_data in course_durations.values() for user_id in user_data})

    # Build human-readable data structure for the template
    readable_durations = {}
    for course_id, user_data in course_durations.items():
        course_name = all_courses[course_id].course_name  # Get the course name
        readable_durations[course_name] = {
            all_users[user_id].username: total_time  # Get the username for each user
            for user_id, total_time in user_data.items()
        }

    # Convert the Python dictionary to a JSON-serializable string
    readable_durations_json = json.dumps(readable_durations)

    # Get all courses for the filter dropdown
    all_courses_names = Course.objects.values('id', 'course_name')

    return render(request, 'reports/course_duration_report.html', {
        'readable_durations_json': readable_durations_json,
        'readable_durations': readable_durations,
        'all_courses_names': all_courses_names,
        'selected_course_id': selected_course_id,
        'chart_labels': chart_labels,
        'chart_data': chart_data,
    })

def price_report(request):
    """Generate comprehensive price analysis report for courses"""
    
    # Top 5 courses with highest original price
    top_price_courses = Course.objects.filter(published=True).order_by('-price')[:5]
    price_chart_data = {
        'labels': [course.course_name for course in top_price_courses],
        'prices': [float(course.price) for course in top_price_courses]
    }
    
    # Top 5 courses with highest discount percentage
    top_discount_courses = Course.objects.filter(
        published=True, 
        discount__gt=0
    ).order_by('-discount')[:5]
    discount_chart_data = {
        'labels': [course.course_name for course in top_discount_courses],
        'discounts': [float(course.discount) for course in top_discount_courses]
    }
    
    # Lowest price courses after discount
    lowest_price_courses = Course.objects.filter(published=True).order_by('price')
    lowest_after_discount = []
    
    for course in lowest_price_courses:
        discounted_price = course.price * (1 - course.discount/100)
        lowest_after_discount.append({
            'course': course,
            'original_price': float(course.price),
            'discount': float(course.discount),
            'final_price': float(discounted_price)
        })
    
    # Sort by final price and get top 5 cheapest
    lowest_after_discount.sort(key=lambda x: x['final_price'])
    lowest_after_discount = lowest_after_discount[:5]
    
    # Prepare scatter plot data
    scatter_data = [{
        'x': item['original_price'],
        'y': item['final_price'],
        'label': item['course'].course_name
    } for item in lowest_after_discount]
    
    # Discount rate analysis
    discount_analysis = []
    courses_with_discount = Course.objects.filter(
        published=True,
        discount__gt=0
    ).order_by('-discount')
    
    for course in courses_with_discount:
        original_price = float(course.price)
        discount_amount = original_price * (float(course.discount)/100)
        final_price = original_price - discount_amount
        
        discount_analysis.append({
            'course': course.course_name,
            'original_price': original_price,
            'final_price': final_price,
            'savings': discount_amount
        })
    
    # Prepare grouped column chart data, So sánh giá gc và giá sau chiết khấu cho từng khóa học.
    group_chart_data = {
        'labels': [item['course'] for item in discount_analysis],
        'original_prices': [item['original_price'] for item in discount_analysis],
        'final_prices': [item['final_price'] for item in discount_analysis],
        'savings': [item['savings'] for item in discount_analysis]
    }

    context = {
        'price_chart_data': json.dumps(price_chart_data),
        'discount_chart_data': json.dumps(discount_chart_data),
        'scatter_data': json.dumps(scatter_data),
        'group_chart_data': json.dumps(group_chart_data),
        'lowest_after_discount': lowest_after_discount,
        'discount_analysis': discount_analysis
    }
    
    return render(request, 'reports/price_report.html', context)

def department_report(request):
    """Generate comprehensive department analysis report"""
    
    # 1. Average number of courses per department
    departments = Department.objects.all()
    dept_course_data = {
        'labels': [],
        'course_counts': []
    }
    
    for dept in departments:
        dept_course_data['labels'].append(dept.name)
        dept_course_data['course_counts'].append(dept.courses.count())

    # Calculate average
    total_courses = sum(dept_course_data['course_counts'])
    avg_courses = total_courses / len(departments) if departments else 0
    
    # 2. Topic distribution across departments
    topic_distribution = {}
    for dept in departments:
        dept_topics = set()  # Use set to avoid duplicate topics
        for course in dept.courses.all():
            for tag in course.tags.all():
                dept_topics.add(tag.topic.name)
        
        topic_distribution[dept.name] = list(dept_topics)
    
    # Convert to chart data
    topic_chart_data = {
        'labels': list(topic_distribution.keys()),  # Department names
        'datasets': []
    }
    
    # Get unique topics
    all_topics = set()
    for topics in topic_distribution.values():
        all_topics.update(topics)
    
    # Create dataset for each topic
    for topic in all_topics:
        dataset = {
            'label': topic,
            'data': []
        }
        for dept in topic_distribution:
            dataset['data'].append(1 if topic in topic_distribution[dept] else 0)
        topic_chart_data['datasets'].append(dataset)

    # 3. Enrollment percentage by department
    enrollment_data = {
        'labels': [],
        'percentages': []
    }
    
    for dept in departments:
        total_users = dept.users.count()
        if total_users > 0:
            enrolled_users = 0
            for course in dept.courses.all():
                enrolled_users += course.enrollments.filter(
                    student__in=dept.users.all()
                ).distinct().count()
            
            enrollment_percentage = (enrolled_users / total_users) * 100
            
            enrollment_data['labels'].append(dept.name)
            enrollment_data['percentages'].append(round(enrollment_percentage, 2))
    
    location_course_data = {
        'labels': [],  # Department names
        'datasets': {}  # Will hold data for each location
    }
    
    # Get all unique locations
    locations = set()
    for dept in departments:
        if dept.location:  # Make sure location exists
            # Convert Location object to string using its string representation
            location_str = str(dept.location)
            locations.add(location_str)
            location_course_data['labels'].append(dept.name)
    
    # Initialize datasets for each location
    for location in locations:
        location_course_data['datasets'][location] = []
    
    # Fill in the data
    for dept in departments:
        # Convert location to string for comparison
        dept_location = str(dept.location) if dept.location else None
        for location in locations:
            if dept_location == location:
                location_course_data['datasets'][location].append(dept.courses.count())
            else:
                location_course_data['datasets'][location].append(0)
    
    # Convert to format expected by Chart.js
    location_datasets = []
    for location, data in location_course_data['datasets'].items():
        location_datasets.append({
            'label': location,
            'data': data
        })

    context = {
        'dept_course_data': json.dumps(dept_course_data),
        'topic_chart_data': json.dumps(topic_chart_data),
        'enrollment_data': json.dumps(enrollment_data),
        'avg_courses': round(avg_courses, 2),
        'location_course_data': json.dumps({
            'labels': location_course_data['labels'],
            'datasets': location_datasets
        })
    }
    
    return render(request, 'reports/department_report.html', context)
