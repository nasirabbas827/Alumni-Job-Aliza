from django.contrib import admin
from django.utils.html import format_html
from django.urls import reverse
from django.http import HttpResponse, FileResponse
import csv
import io
from reportlab.pdfgen import canvas
from .models import RegisteredUsers, Profile, Job, JobApplication, Bookmark

# =====================================================
# Generic Export Actions
# =====================================================
def export_as_csv(modeladmin, request, queryset):
    meta = modeladmin.model._meta
    field_names = [field.name for field in meta.fields]

    response = HttpResponse(content_type='text/csv')
    response['Content-Disposition'] = f'attachment; filename={meta.model_name}.csv'
    writer = csv.writer(response)

    writer.writerow(field_names)
    for obj in queryset:
        writer.writerow([getattr(obj, field) for field in field_names])
    return response
export_as_csv.short_description = "Export selected as CSV"

def export_as_pdf(modeladmin, request, queryset):
    buffer = io.BytesIO()
    p = canvas.Canvas(buffer)
    y = 800
    for obj in queryset:
        p.drawString(50, y, str(obj))
        y -= 20
        if y < 50:
            p.showPage()
            y = 800
    p.save()
    buffer.seek(0)
    return FileResponse(buffer, as_attachment=True, filename='export.pdf')
export_as_pdf.short_description = "Export selected as PDF"

# =====================================================
# RegisteredUsers Admin
# =====================================================
@admin.register(RegisteredUsers)
class RegisteredUsersAdmin(admin.ModelAdmin):
    list_display = ('username', 'email', 'role', 'status', 'created_at', 'updated_at')
    list_filter = ('role', 'status', 'created_at')
    search_fields = ('username', 'email', 'full_name')
    actions = ['activate_users', 'deactivate_users', export_as_csv, export_as_pdf]

    def activate_users(self, request, queryset):
        updated = queryset.update(status='active')
        self.message_user(request, f"{updated} user(s) activated.")
    activate_users.short_description = "Activate selected users"

    def deactivate_users(self, request, queryset):
        updated = queryset.update(status='inactive')
        self.message_user(request, f"{updated} user(s) deactivated.")
    deactivate_users.short_description = "Deactivate selected users"

# =====================================================
# Profile Admin
# =====================================================
@admin.register(Profile)
class ProfileAdmin(admin.ModelAdmin):
    list_display = ('user', 'linkedin_url', 'education_summary', 'experience_summary', 'skills_summary', 'is_public')
    search_fields = ('user__username', 'skills', 'education', 'experience')
    list_filter = ('is_public',)
    actions = [export_as_csv, export_as_pdf]

    def education_summary(self, obj):
        return (obj.education[:50] + '...') if obj.education else '-'
    education_summary.short_description = 'Education'

    def experience_summary(self, obj):
        return (obj.experience[:50] + '...') if obj.experience else '-'
    experience_summary.short_description = 'Experience'

    def skills_summary(self, obj):
        return (obj.skills[:50] + '...') if obj.skills else '-'
    skills_summary.short_description = 'Skills'

# =====================================================
# Job Admin
# =====================================================
@admin.register(Job)
class JobAdmin(admin.ModelAdmin):
    list_display = ('title', 'employer_link', 'location', 'job_type', 'status', 'created_at', 'applications_count')
    list_filter = ('status', 'job_type', 'created_at')
    search_fields = ('title', 'employer__username', 'skills_required', 'category')
    actions = ['approve_jobs', 'reject_jobs', export_as_csv, export_as_pdf]

    def employer_link(self, obj):
        url = reverse("admin:myapp_registeredusers_change", args=[obj.employer.user_id])
        return format_html('<a href="{}">{}</a>', url, obj.employer.username)
    employer_link.short_description = 'Employer'

    def applications_count(self, obj):
        return obj.applications.count()
    applications_count.short_description = 'Applications'

    def approve_jobs(self, request, queryset):
        updated = queryset.update(status='approved')
        self.message_user(request, f"{updated} job(s) approved.")
    approve_jobs.short_description = "Approve selected jobs"

    def reject_jobs(self, request, queryset):
        updated = queryset.update(status='rejected')
        self.message_user(request, f"{updated} job(s) rejected.")
    reject_jobs.short_description = "Reject selected jobs"

# =====================================================
# JobApplication Admin
# =====================================================
@admin.register(JobApplication)
class JobApplicationAdmin(admin.ModelAdmin):
    list_display = ('job', 'applicant', 'status', 'applied_at')
    list_filter = ('status', 'applied_at')
    search_fields = ('job__title', 'applicant__username')
    actions = ['mark_shortlisted', 'mark_hired', 'mark_rejected', export_as_csv, export_as_pdf]

    def mark_shortlisted(self, request, queryset):
        updated = queryset.update(status='shortlisted')
        self.message_user(request, f"{updated} application(s) shortlisted.")
    mark_shortlisted.short_description = "Mark selected as Shortlisted"

    def mark_hired(self, request, queryset):
        updated = queryset.update(status='hired')
        self.message_user(request, f"{updated} application(s) marked as Hired.")
    mark_hired.short_description = "Mark selected as Hired"

    def mark_rejected(self, request, queryset):
        updated = queryset.update(status='rejected')
        self.message_user(request, f"{updated} application(s) rejected.")
    mark_rejected.short_description = "Mark selected as Rejected"

# =====================================================
# Bookmark Admin
# =====================================================
@admin.register(Bookmark)
class BookmarkAdmin(admin.ModelAdmin):
    list_display = ('user', 'job', 'created_at')
    list_filter = ('created_at',)
    search_fields = ('user__username', 'job__title')
    actions = [export_as_csv, export_as_pdf]

# =====================================================
# Admin site customization
# =====================================================
admin.site.site_header = "Alumni Job Portal Admin"
admin.site.site_title = "Alumni Job Portal"
admin.site.index_title = "Dashboard"