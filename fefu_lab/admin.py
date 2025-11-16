from django.contrib import admin

from .models import Student, Instructor, Course, Enrollment, UserProfile

@admin.register(Student)
class StudentAdmin(admin.ModelAdmin):
    list_display = ['last_name', 'first_name', 'email', 'faculty', 'created_at']
    list_filter = ['faculty', 'created_at']
    search_fields = ['first_name', 'last_name', 'email']
    readonly_fields = ['created_at']
    fieldsets = [
        ('Основная информация', {
            'fields': ['first_name', 'last_name', 'email']
        }),
        ('Дополнительная информация', {
            'fields': ['birth_date', 'faculty', 'created_at']
        }),
    ]

@admin.register(Instructor)
class InstructorAdmin(admin.ModelAdmin):
    list_display = ['last_name', 'first_name', 'email', 'specialization', 'is_active']
    list_filter = ['is_active', 'specialization']
    search_fields = ['first_name', 'last_name', 'email', 'specialization']
    list_editable = ['is_active']

@admin.register(Course)
class CourseAdmin(admin.ModelAdmin):
    list_display = ['title', 'instructor', 'level', 'duration', 'is_active', 'created_at']
    list_filter = ['is_active', 'level', 'instructor', 'created_at']
    search_fields = ['title', 'description']
    list_editable = ['is_active']
    prepopulated_fields = {'slug': ('title',)}
    readonly_fields = ['created_at', 'updated_at']
    
    def get_queryset(self, request):
        return super().get_queryset(request).select_related('instructor')

@admin.register(Enrollment)
class EnrollmentAdmin(admin.ModelAdmin):
    list_display = ['student', 'course', 'status', 'enrolled_at']
    list_filter = ['status', 'enrolled_at', 'course']
    search_fields = ['student__first_name', 'student__last_name', 'course__title']
    list_editable = ['status']
    readonly_fields = ['enrolled_at']
    
    def get_queryset(self, request):
        return super().get_queryset(request).select_related('student', 'course')

@admin.register(UserProfile)
class UserProfileAdmin(admin.ModelAdmin):
    list_display = ['username', 'email', 'created_at']
    list_filter = ['created_at']
    search_fields = ['username', 'email']
    readonly_fields = ['created_at']
