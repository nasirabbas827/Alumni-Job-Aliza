from django.db import models
from django.conf import settings
from django.utils import timezone


class RegisteredUsers(models.Model):
    STATUS_CHOICES = (
        ('active', 'Active'),
        ('inactive', 'Inactive'),
    )

    # Adding Role Choices
    ROLE_CHOICES = (
        ('alumni', 'Alumni'),
        ('student', 'Student'),
        ('employer', 'Employer'),
    )

    user_id = models.AutoField(primary_key=True)
    username = models.CharField(max_length=150, unique=True)
    email = models.EmailField(unique=True)
    password = models.CharField(max_length=255) 
    full_name = models.CharField(max_length=150, blank=True, null=True)
    
    # New Role Field
    role = models.CharField(
        max_length=10, 
        choices=ROLE_CHOICES, 
        default='student'
    )

    gender = models.CharField(
        max_length=10,
        choices=[('Male', 'Male'), ('Female', 'Female'), ('Other', 'Other')],
        blank=True,
        null=True
    )
    status = models.CharField(max_length=10, choices=STATUS_CHOICES, default='inactive')
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    def __str__(self):
        return f"{self.username} ({self.role})"
    

# =====================================================
# Profile Model 
# =====================================================

class Profile(models.Model):
    user = models.OneToOneField(
        RegisteredUsers,
        on_delete=models.CASCADE,
        related_name='profile'
    )

    linkedin_url = models.URLField(blank=True, null=True)
    education = models.TextField(blank=True, null=True)
    experience = models.TextField(blank=True, null=True)
    skills = models.TextField(help_text="Comma separated skills")
    resume = models.FileField(upload_to='resumes/', blank=True, null=True)
    profile_picture = models.ImageField(upload_to='profiles/', blank=True, null=True)
    is_public = models.BooleanField(default=True)

    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    def __str__(self):
        return f"{self.user.username} Profile"



# =====================================================
# 4. Job Posting Model
# =====================================================

class Job(models.Model):

    JOB_TYPE_CHOICES = (
        ('full_time', 'Full Time'),
        ('part_time', 'Part Time'),
        ('internship', 'Internship'),
        ('contract', 'Contract'),
    )

    STATUS_CHOICES = (
        ('pending', 'Pending'),
        ('approved', 'Approved'),
        ('rejected', 'Rejected'),
    )

    employer = models.ForeignKey(
        RegisteredUsers,
        on_delete=models.CASCADE,
        limit_choices_to={'role__in': ['employer', 'alumni']},
        related_name='jobs'
    )

    title = models.CharField(max_length=255)
    description = models.TextField()
    location = models.CharField(max_length=255)

    salary_min = models.DecimalField(max_digits=10, decimal_places=2, blank=True, null=True)
    salary_max = models.DecimalField(max_digits=10, decimal_places=2, blank=True, null=True)

    job_type = models.CharField(max_length=20, choices=JOB_TYPE_CHOICES)
    category = models.CharField(max_length=255)
    skills_required = models.TextField(help_text="Comma separated skills")

    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default='pending')

    created_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return f"{self.title} - {self.employer.username}"




# JobApplication model
class JobApplication(models.Model):
    STATUS_CHOICES = (
        ('applied', 'Applied'),
        ('shortlisted', 'Shortlisted'),
        ('rejected', 'Rejected'),
        ('hired', 'Hired'),
    )

    job = models.ForeignKey(Job, on_delete=models.CASCADE, related_name='applications')
    applicant = models.ForeignKey(
        RegisteredUsers,  # <- use RegisteredUsers instead of settings.AUTH_USER_MODEL
        on_delete=models.CASCADE,
        limit_choices_to={'role__in': ['student', 'alumni']}
    )
    resume = models.FileField(upload_to='applications/')
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default='applied')
    applied_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        unique_together = ('job', 'applicant')

    def __str__(self):
        return f"{self.applicant.username} -> {self.job.title}"
    
class Bookmark(models.Model):
    user = models.ForeignKey(RegisteredUsers, on_delete=models.CASCADE)
    job = models.ForeignKey(Job, on_delete=models.CASCADE)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        unique_together = ('user', 'job')

    def __str__(self):
        return f"{self.user.username} bookmarked {self.job.title}"


# ================================
# Notification Model
# ================================
class Notification(models.Model):
    NOTIFICATION_TYPE_CHOICES = (
        ('job_posted', 'New Job Posted'),
        ('application_update', 'Application Status Update'),
        ('system_alert', 'System Alert'),
    )

    user = models.ForeignKey(
        RegisteredUsers,
        on_delete=models.CASCADE,
        related_name='notifications'
    )
    message = models.TextField()
    notification_type = models.CharField(
        max_length=50,
        choices=NOTIFICATION_TYPE_CHOICES,
        default='system_alert'
    )
    job = models.ForeignKey(Job, on_delete=models.CASCADE, blank=True, null=True)
    application = models.ForeignKey(JobApplication, on_delete=models.CASCADE, blank=True, null=True)
    is_read = models.BooleanField(default=False)
    created_at = models.DateTimeField(default=timezone.now)

    class Meta:
        ordering = ['-created_at']

    def __str__(self):
        return f"Notification for {self.user.username}: {self.message[:30]}..."


# ================================
# Signals for auto-notifications
# ================================
from django.db.models.signals import post_save
from django.dispatch import receiver

# Notify all students/alumni when a new job is approved
@receiver(post_save, sender=Job)
def notify_users_new_job(sender, instance, created, **kwargs):
    if created and instance.status == 'approved':
        users_to_notify = RegisteredUsers.objects.filter(role__in=['student', 'alumni'])
        notifications = [
            Notification(
                user=user,
                message=f"New job posted: {instance.title} at {instance.location}",
                notification_type='job_posted',
                job=instance
            )
            for user in users_to_notify
        ]
        Notification.objects.bulk_create(notifications)


# Notify applicant when application status changes
@receiver(post_save, sender=JobApplication)
def notify_application_status(sender, instance, created, **kwargs):
    if not created:
        Notification.objects.create(
            user=instance.applicant,
            message=f"Your application for '{instance.job.title}' is now {instance.status}.",
            notification_type='application_update',
            application=instance
        )


# Optional helper for system-wide notifications
def create_system_alert(message):
    users = RegisteredUsers.objects.all()
    notifications = [
        Notification(user=user, message=message, notification_type='system_alert')
        for user in users
    ]
    Notification.objects.bulk_create(notifications)