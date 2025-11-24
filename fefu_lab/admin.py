from django.contrib import admin
from .models import Student, Instructor, Course, Enrollment, UserProfile

@admin.register(Student)
class StudentAdmin(admin.ModelAdmin):
    list_display = ['get_last_name', 'get_first_name', 'get_email', 'faculty', 'created_at']
    list_filter = ['faculty', 'created_at']
    search_fields = ['user__first_name', 'user__last_name', 'user__email']
    readonly_fields = ['created_at']
    
    def get_first_name(self, obj):
        return obj.user.first_name
    get_first_name.short_description = 'Имя'
    
    def get_last_name(self, obj):
        return obj.user.last_name
    get_last_name.short_description = 'Фамилия'
    
    def get_email(self, obj):
        return obj.user.email
    get_email.short_description = 'Email'

@admin.register(Instructor)
class InstructorAdmin(admin.ModelAdmin):
    list_display = ['get_last_name', 'get_first_name', 'get_email', 'specialization', 'is_active']
    list_filter = ['is_active', 'specialization']
    search_fields = ['user__first_name', 'user__last_name', 'user__email', 'specialization']
    list_editable = ['is_active']
    
    def get_first_name(self, obj):
        return obj.user.first_name
    get_first_name.short_description = 'Имя'
    
    def get_last_name(self, obj):
        return obj.user.last_name
    get_last_name.short_description = 'Фамилия'
    
    def get_email(self, obj):
        return obj.user.email
    get_email.short_description = 'Email'

@admin.register(Course)
class CourseAdmin(admin.ModelAdmin):
    list_display = ['title', 'get_instructor_name', 'level', 'duration', 'is_active', 'created_at']
    list_filter = ['is_active', 'level', 'instructor', 'created_at']
    search_fields = ['title', 'description']
    list_editable = ['is_active']
    prepopulated_fields = {'slug': ('title',)}
    readonly_fields = ['created_at', 'updated_at']
    
    def get_queryset(self, request):
        return super().get_queryset(request).select_related('instructor')
    
    def get_instructor_name(self, obj):
        return obj.instructor.user.get_full_name() if obj.instructor else "Не назначен"
    get_instructor_name.short_description = 'Преподаватель'

@admin.register(Enrollment)
class EnrollmentAdmin(admin.ModelAdmin):
    list_display = ['get_student_name', 'get_course_title', 'status', 'enrolled_at']
    list_filter = ['status', 'enrolled_at', 'course']
    search_fields = ['student__user__first_name', 'student__user__last_name', 'course__title']
    list_editable = ['status']
    readonly_fields = ['enrolled_at']
    
    def get_queryset(self, request):
        return super().get_queryset(request).select_related('student', 'course')
    
    def get_student_name(self, obj):
        return obj.student.user.get_full_name()
    get_student_name.short_description = 'Студент'
    
    def get_course_title(self, obj):
        return obj.course.title
    get_course_title.short_description = 'Курс'

@admin.register(UserProfile)
class UserProfileAdmin(admin.ModelAdmin):
    list_display = ['get_username', 'get_email', 'role', 'created_at']
    list_filter = ['role', 'created_at']
    search_fields = ['user__username', 'user__email']
    readonly_fields = ['created_at', 'updated_at']
    
    def get_username(self, obj):
        return obj.user.username
    get_username.short_description = 'Имя пользователя'
    
    def get_email(self, obj):
        return obj.user.email
    get_email.short_description = 'Email'
