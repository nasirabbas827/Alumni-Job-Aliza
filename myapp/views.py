from django.shortcuts import render, redirect
from django.contrib import messages
from django.contrib.auth.hashers import check_password
from django.core.mail import send_mail
from django.conf import settings
from django.urls import reverse
import random
import string
from django.contrib.auth.hashers import make_password
from .models import RegisteredUsers, Profile
from .forms import RegisterForm, LoginForm, UpdateProfileForm
from .models import Job
from .forms import JobForm , JobApplicationForm
from django.shortcuts import render, redirect, get_object_or_404
from django.contrib import messages
from django.contrib.auth.hashers import check_password
from django.db.models import Q
from .models import Job, JobApplication, Bookmark, RegisteredUsers


# =====================================================
# Landing Page
# =====================================================

def index(request):
    # Fetch some live stats for the landing page
    job_count = Job.objects.filter(status='approved').count()
    alumni_count = RegisteredUsers.objects.filter(role='alumni').count()
    
    # Get the latest 3 jobs to show on the landing page
    recent_jobs = Job.objects.filter(status='approved').order_by('-created_at')[:3]

    # Determine dashboard URL based on role
    user_role = request.session.get('role')
    dashboard_url = 'login' # default
    if user_role == 'student':
        dashboard_url = 'student_dashboard'
    elif user_role == 'alumni':
        dashboard_url = 'alumni_dashboard'
    elif user_role == 'employer':
        dashboard_url = 'employer_dashboard'

    context = {
        'job_count': job_count + 150, 
        'alumni_count': alumni_count + 50,
        'recent_jobs': recent_jobs,
        'dashboard_url': dashboard_url
    }
    return render(request, 'index.html', context)


# =====================================================
# Helper Function
# =====================================================

def get_logged_in_user(request):
    user_id = request.session.get('user_id')
    if not user_id:
        return None
    return RegisteredUsers.objects.filter(user_id=user_id).first()


# =====================================================
# Registration
# =====================================================

def register_view(request):
    if request.method == "POST":
        form = RegisterForm(request.POST)
        if form.is_valid():
            user = form.save()

            # Automatically create profile
            Profile.objects.create(user=user)

            # Email verification link (simple ID based)
            verification_link = request.build_absolute_uri(
                reverse('verify_email', args=[user.user_id])
            )

            send_mail(
                subject="Verify Your Account - Alumni Portal",
                message=f"""
Hello {user.full_name or user.username},

Thank you for registering.

Please click the link below to activate your account:

{verification_link}

Regards,
Alumni Portal Team
                """,
                from_email=settings.DEFAULT_FROM_EMAIL,
                recipient_list=[user.email],
                fail_silently=False,
            )

            messages.success(request, "Registration successful! Please verify your email.")
            return redirect('login')
    else:
        form = RegisterForm()

    return render(request, 'register.html', {'form': form})


# =====================================================
# Email Verification
# =====================================================

def verify_email(request, user_id):
    user = RegisteredUsers.objects.filter(user_id=user_id).first()

    if not user:
        messages.error(request, "Invalid verification link.")
        return redirect('login')

    if user.status == 'active':
        messages.info(request, "Account already verified.")
        return redirect('login')

    user.status = 'active'
    user.save()

    messages.success(request, "Account verified successfully. You can now login.")
    return redirect('login')


# =====================================================
# Login
# =====================================================

def login_view(request):
    if request.method == "POST":
        form = LoginForm(request.POST)
        if form.is_valid():

            # We already attached user inside form.clean()
            user = form.cleaned_data.get("user")

            # Double safety check
            if user.status != 'active':
                messages.error(request, "Account is not verified.")
                return redirect('login')

            # Store session data
            request.session['user_id'] = user.user_id
            request.session['role'] = user.role
            request.session['username'] = user.username

            # Role-based redirect
            if user.role == 'alumni':
                return redirect('alumni_dashboard')
            elif user.role == 'employer':
                return redirect('employer_dashboard')
            else:
                return redirect('student_dashboard')
    else:
        form = LoginForm()

    return render(request, 'login.html', {'form': form})


# =====================================================
# Update Profile
# =====================================================

def update_profile(request):
    user = get_logged_in_user(request)

    if not user:
        return redirect('login')

    profile, created = Profile.objects.get_or_create(user=user)

    if request.method == "POST":
        form = UpdateProfileForm(request.POST, request.FILES, instance=profile)
        if form.is_valid():
            form.save()
            messages.success(request, "Profile updated successfully.")
            return redirect('update_profile')
    else:
        form = UpdateProfileForm(instance=profile)

    return render(request, 'update_profile.html', {
        'form': form,
        'user': user
    })


# =====================================================
# Role-Based Dashboards
# =====================================================

def alumni_dashboard(request):
    # Assuming your session-based login helper
    user = get_logged_in_user(request)
    if not user or user.role != 'alumni':
        return redirect('login')

    # 1. Stats for Jobs this Alumni POSTED (as an Employer)
    posted_jobs = Job.objects.filter(employer=user)
    total_posted_count = posted_jobs.count()
    
    # 2. Total applications RECEIVED for the jobs they posted
    total_received_applications = JobApplication.objects.filter(job__employer=user).count()

    # 3. Stats for Jobs this Alumni APPLIED TO (as a Candidate)
    my_applications = JobApplication.objects.filter(applicant=user)
    total_applied_count = my_applications.count()

    # 4. Bookmarks & Latest Jobs
    total_bookmarks = Bookmark.objects.filter(user=user).count()
    latest_jobs = Job.objects.filter(status='approved').order_by('-created_at')[:5]

    context = {
        'user': user,
        'total_posted': total_posted_count,
        'total_received': total_received_applications,
        'total_applied': total_applied_count,
        'total_bookmarks': total_bookmarks,
        'latest_jobs': latest_jobs,
        'my_applications_list': my_applications.order_by('-applied_at')[:5],
    }

    return render(request, 'alumni.html', context)


def student_dashboard(request):
    user = get_logged_in_user(request)
    if not user or user.role != 'student':
        return redirect('login')

    # 1. Personal Stats
    applied_count = JobApplication.objects.filter(applicant=user).count()
    saved_count = Bookmark.objects.filter(user=user).count()
    
    # 2. Application Status Breakdown
    hired_count = JobApplication.objects.filter(applicant=user, status='hired').count()

    # 3. Recent Applications (Latest 5)
    recent_applications = JobApplication.objects.filter(applicant=user).order_by('-applied_at')[:5]

    # 4. Recommended Jobs (Latest 3 approved jobs they haven't applied to yet)
    applied_job_ids = JobApplication.objects.filter(applicant=user).values_list('job_id', flat=True)
    recommended_jobs = Job.objects.filter(status='approved').exclude(id__in=applied_job_ids).order_by('-created_at')[:3]

    context = {
        'user': user,
        'applied_count': applied_count,
        'saved_count': saved_count,
        'hired_count': hired_count,
        'recent_applications': recent_applications,
        'recommended_jobs': recommended_jobs,
    }

    return render(request, 'student.html', context)


def employer_dashboard(request):
    user = get_logged_in_user(request)
    if not user or user.role != 'employer':
        return redirect('login')

    # 1. Stats for Jobs this Employer POSTED
    my_jobs = Job.objects.filter(employer=user)
    active_postings_count = my_jobs.filter(status='approved').count()
    
    # 2. Total applications RECEIVED for their jobs
    all_applications = JobApplication.objects.filter(job__employer=user)
    total_apps_count = all_applications.count()

    # 3. "Interviews Set" (Calculated as 'Shortlisted' candidates)
    interviews_count = all_applications.filter(status='shortlisted').count()

    # 4. Recent Applications for the table (limit to 5)
    recent_applications = all_applications.order_by('-applied_at')[:5]

    context = {
        'user': user,
        'active_postings': active_postings_count,
        'total_applications': total_apps_count,
        'interviews_set': interviews_count,
        'recent_applications': recent_applications,
    }

    return render(request, 'employer.html', context)


# =====================================================
# Logout
# =====================================================

def logout_view(request):
    request.session.flush()
    return redirect('login')


def job_create(request):
    user = get_logged_in_user(request)

    if not user or user.role not in ['employer', 'alumni']:
        return redirect('login')

    if request.method == "POST":
        form = JobForm(request.POST)
        if form.is_valid():
            job = form.save(commit=False)
            job.employer = user
            job.save()
            messages.success(request, "Job posted successfully (Pending Approval).")
            return redirect('job_list')
    else:
        form = JobForm()

    return render(request, 'job_form.html', {'form': form})


def job_list(request):
    user = get_logged_in_user(request)

    if not user:
        return redirect('login')

    if user.role in ['employer', 'alumni']:
        jobs = Job.objects.filter(employer=user)
    else:
        jobs = Job.objects.filter(status='approved')

    return render(request, 'job_list.html', {'jobs': jobs})

def job_update(request, job_id):
    user = get_logged_in_user(request)
    job = Job.objects.filter(id=job_id, employer=user).first()

    if not job:
        return redirect('job_list')

    if request.method == "POST":
        form = JobForm(request.POST, instance=job)
        if form.is_valid():
            form.save()
            messages.success(request, "Job updated successfully.")
            return redirect('job_list')
    else:
        form = JobForm(instance=job)

    return render(request, 'job_form.html', {'form': form})


def job_delete(request, job_id):
    user = get_logged_in_user(request)
    job = Job.objects.filter(id=job_id, employer=user).first()

    if job:
        job.delete()
        messages.success(request, "Job deleted successfully.")

    return redirect('job_list')




# ────────────────────────────────────────────────
#  Job List + Search + Filters (main page)
# ────────────────────────────────────────────────
def job_list_search(request):
    user = get_logged_in_user(request)
    if not user or user.role not in ['student', 'alumni']:
        return redirect('login')

    jobs = Job.objects.filter(status='approved') \
              .select_related('employer') \
              .order_by('-created_at')

    keyword   = request.GET.get('keyword', '').strip()
    location  = request.GET.get('location', '').strip()
    job_type  = request.GET.get('job_type', '').strip()

    if keyword:
        jobs = jobs.filter(
            Q(title__icontains=keyword) |
            Q(description__icontains=keyword) |
            Q(skills_required__icontains=keyword)
        )
    if location:
        jobs = jobs.filter(location__icontains=location)
    if job_type:
        jobs = jobs.filter(job_type=job_type)

    # Skill match score
    user_profile = getattr(user, 'profile', None)
    user_skills = set()
    if user_profile and user_profile.skills:
        user_skills = {s.strip().lower() for s in user_profile.skills.split(',') if s.strip()}

    for job in jobs:
        job_skills = {s.strip().lower() for s in job.skills_required.split(',') if s.strip()}
        common = user_skills & job_skills
        job.match_score = len(common)
        job.match_percentage = round((len(common) / max(len(job_skills), 1)) * 100, 1) if job_skills else 0

    bookmarked_ids = set(Bookmark.objects.filter(user=user).values_list('job_id', flat=True))

    context = {
        'user': user,
        'jobs': jobs,
        'bookmarked_ids': bookmarked_ids,
        'filters': {'keyword': keyword, 'location': location, 'job_type': job_type},
        'job_type_choices': Job.JOB_TYPE_CHOICES,
    }
    return render(request, 'jobs/list.html', context)


# ────────────────────────────────────────────────
#  Single Job Detail
# ────────────────────────────────────────────────
def job_detail(request, job_id):
    user = get_logged_in_user(request)
    if not user or user.role not in ['student', 'alumni']:
        return redirect('login')

    job = get_object_or_404(Job, id=job_id, status='approved')

    # Match score
    user_profile = getattr(user, 'profile', None)
    match_score = 0
    match_percentage = 0
    if user_profile and user_profile.skills:
        user_skills = {s.strip().lower() for s in user_profile.skills.split(',') if s.strip()}
        job_skills = {s.strip().lower() for s in job.skills_required.split(',') if s.strip()}
        common = user_skills & job_skills
        match_score = len(common)
        match_percentage = round((len(common) / max(len(job_skills), 1)) * 100, 1) if job_skills else 0

    is_bookmarked = Bookmark.objects.filter(user=user, job=job).exists()
    has_applied   = JobApplication.objects.filter(applicant=user, job=job).exists()

    if request.method == "POST":
        action = request.POST.get('action')

        if action == 'toggle_bookmark':
            if is_bookmarked:
                Bookmark.objects.filter(user=user, job=job).delete()
                messages.info(request, "Removed from bookmarks.")
            else:
                Bookmark.objects.create(user=user, job=job)
                messages.success(request, "Added to bookmarks.")
            return redirect(request.path)

        elif action == 'apply':
            if job.employer == user:
                messages.error(request, "Cannot apply to your own job.")
            elif has_applied:
                messages.info(request, "Already applied.")
            else:
                form = JobApplicationForm(request.POST, request.FILES)
                if form.is_valid():
                    app = form.save(commit=False)
                    app.job = job
                    app.applicant = user
                    app.save()
                    messages.success(request, "Application submitted!")
                else:
                    messages.error(request, "Please check the form.")
            return redirect(request.path)

    context = {
        'user': user,
        'job': job,
        'match_score': match_score,
        'match_percentage': match_percentage,
        'is_bookmarked': is_bookmarked,
        'has_applied': has_applied,
        'application_form': JobApplicationForm(),
    }
    return render(request, 'jobs/detail.html', context)


# ────────────────────────────────────────────────
#  Bookmarked Jobs
# ────────────────────────────────────────────────
def bookmarked_jobs(request):
    user = get_logged_in_user(request)
    if not user or user.role not in ['student', 'alumni']:
        return redirect('login')

    bookmarks = Bookmark.objects.filter(user=user).select_related('job__employer')
    context = {'user': user, 'bookmarks': bookmarks}
    return render(request, 'jobs/bookmarks.html', context)


# ────────────────────────────────────────────────
#  My Applications
# ────────────────────────────────────────────────
def my_applications(request):
    user = get_logged_in_user(request)
    if not user or user.role not in ['student', 'alumni']:
        return redirect('login')

    applications = JobApplication.objects.filter(applicant=user) \
                        .select_related('job__employer') \
                        .order_by('-applied_at')
    context = {'user': user, 'applications': applications}
    return render(request, 'jobs/applications.html', context)


# ────────────────────────────────────────────────
#  My Posted Jobs + Applications Overview
# ────────────────────────────────────────────────
def my_posted_jobs(request):
    user = get_logged_in_user(request)
    if not user or user.role not in ['employer', 'alumni']:
        return redirect('login')

    jobs = Job.objects.filter(employer=user).order_by('-created_at')

    context = {
        'user': user,
        'jobs': jobs,
    }
    return render(request, 'employer/my_posted_jobs.html', context)


# ────────────────────────────────────────────────
#  Applications for a specific job
# ────────────────────────────────────────────────
def job_applications(request, job_id):
    user = get_logged_in_user(request)
    if not user or user.role not in ['employer', 'alumni']:
        return redirect('login')

    job = get_object_or_404(Job, id=job_id, employer=user)

    applications = JobApplication.objects.filter(job=job)\
        .select_related('applicant', 'applicant__profile')\
        .order_by('-applied_at')

    context = {
        'user': user,
        'job': job,
        'applications': applications,
    }
    return render(request, 'employer/job_applications.html', context)


# ────────────────────────────────────────────────
#  Update application status (AJAX-friendly or form POST)
# ────────────────────────────────────────────────
def update_application_status(request, application_id):
    user = get_logged_in_user(request)
    if not user or user.role not in ['employer', 'alumni']:
        return redirect('login')

    application = get_object_or_404(JobApplication, id=application_id)

    # Security: only the job poster can update
    if application.job.employer != user:
        messages.error(request, "You do not have permission to update this application.")
        return redirect('job_applications', job_id=application.job.id)

    if request.method == "POST":
        new_status = request.POST.get('status')
        if new_status in dict(JobApplication.STATUS_CHOICES):
            application.status = new_status
            application.save()
            messages.success(request, f"Application status updated to: {application.get_status_display()}")
        else:
            messages.error(request, "Invalid status selected.")

        return redirect('job_applications', job_id=application.job.id)

    return redirect('job_applications', job_id=application.job.id)


# ────────────────────────────────────────────────
#  View Applicant Profile (if public)
# ────────────────────────────────────────────────
def view_applicant_profile(request, applicant_id):
    user = get_logged_in_user(request)
    if not user or user.role not in ['employer', 'alumni']:
        return redirect('login')

    applicant = get_object_or_404(RegisteredUsers, user_id=applicant_id)

    # Only allow viewing if profile is public
    if not hasattr(applicant, 'profile') or not applicant.profile.is_public:
        messages.error(request, "This profile is not publicly visible.")
        return redirect(request.META.get('HTTP_REFERER', 'job_list_search'))

    profile = applicant.profile

    context = {
        'applicant': applicant,
        'profile': profile,
        'viewer': user,   
    }
    return render(request, 'employer/applicant_profile.html', context)


def reset_password(request):
    if request.method == "POST":
        email = request.POST.get("email").strip()
        user = RegisteredUsers.objects.filter(email=email).first()

        if not user:
            messages.error(request, "No account found with this email.")
            return redirect('reset_password')

        # Generate temporary password
        temp_password = ''.join(random.choices(string.ascii_letters + string.digits, k=8))

        # Save hashed password
        user.password = make_password(temp_password)
        user.save()

        # Send email with temporary password
        try:
            send_mail(
                subject="Temporary Password - Alumni Job Portal",
                message=f"""
Hello {user.full_name or user.username},

Your password has been reset. Use the temporary password below to login:

Temporary Password: {temp_password}

Please login and update your password immediately.

Regards,
Alumni Job Portal Team
                """,
                from_email=settings.DEFAULT_FROM_EMAIL,
                recipient_list=[user.email],
                fail_silently=False,
            )
            messages.success(request, "Temporary password sent to your email.")
        except Exception as e:
            messages.error(request, "Failed to send email. Try again later.")

        return redirect('login')

    return render(request, 'reset_password.html')


from django.http import JsonResponse
from django.utils.timesince import timesince
from .models import Notification

def fetch_notifications(request):
    user_id = request.session.get('user_id')
    if not user_id:
        return JsonResponse({"unread_count": 0, "notifications": []})

    # First filter by user
    notifications_qs = Notification.objects.filter(user_id=user_id).order_by('-created_at')
    
    # Count unread notifications
    unread_count = notifications_qs.filter(is_read=False).count()

    # Then slice for latest 10 notifications
    notifications = notifications_qs[:10]

    data = {
        "unread_count": unread_count,
        "notifications": [
            {
                "message": n.message,
                "is_read": n.is_read,
                "time_ago": timesince(n.created_at) + " ago",
                "link": "#"  # optional: add relevant link to job or application
            } for n in notifications
        ]
    }
    return JsonResponse(data)