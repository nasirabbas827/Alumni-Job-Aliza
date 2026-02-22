from django.urls import path
from django.conf import settings
from django.conf.urls.static import static
from . import views

urlpatterns = [
    path('', views.index, name='index'),
    path('register/', views.register_view, name='register'),
    path('verify/<int:user_id>/', views.verify_email, name='verify_email'),
    path('login/', views.login_view, name='login'),
    path('logout/', views.logout_view, name='logout'),
    path('reset-password/', views.reset_password, name='reset_password'),
    path('notifications/fetch/', views.fetch_notifications, name='fetch_notifications'),
    
    
    # Role-Specific Dashboards
    path('dashboard/alumni/', views.alumni_dashboard, name='alumni_dashboard'),
    path('dashboard/student/', views.student_dashboard, name='student_dashboard'),
    path('dashboard/employer/', views.employer_dashboard, name='employer_dashboard'),
    path('profile/update/', views.update_profile, name='update_profile'),
    path('jobs/view/', views.job_list, name='job_list'),
    path('jobs/add/', views.job_create, name='job_create'),
    path('jobs/edit/<int:job_id>/', views.job_update, name='job_update'),
    path('jobs/delete/<int:job_id>/', views.job_delete, name='job_delete'),

    # Job browsing & search (for students/alumni)
    path('jobs/', views.job_list_search, name='job_list_search'),
    path('jobs/<int:job_id>/', views.job_detail, name='job_detail'),

    # User-specific job actions
    path('jobs/bookmarks/', views.bookmarked_jobs, name='bookmarked_jobs'),
    path('jobs/applications/', views.my_applications, name='my_applications'),

    # Employer / Alumni - Manage their jobs & applications
    path('my-jobs/', views.my_posted_jobs, name='my_posted_jobs'),
    path('job/<int:job_id>/applications/', views.job_applications, name='job_applications'),
    path('application/<int:application_id>/update-status/', views.update_application_status, name='update_application_status'),
    path('applicant/<int:applicant_id>/profile/', views.view_applicant_profile, name='view_applicant_profile'),
]

if settings.DEBUG:
    urlpatterns += static(settings.MEDIA_URL, document_root=settings.MEDIA_ROOT)