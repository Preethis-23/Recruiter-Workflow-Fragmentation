from django.urls import path
from . import views

urlpatterns = [
    # Job Descriptions
    path('jds/', views.jds_collection, name='jds_collection'),
    path('jds/<int:jd_id>', views.jd_detail, name='jd_detail'),
    path('jds/<int:jd_id>/', views.jd_detail, name='jd_detail_slash'),

    # Resumes
    path('resumes/', views.resumes_collection, name='resumes_collection'),
    path('resumes/<int:resume_id>', views.resume_detail, name='resume_detail'),
    path('resumes/<int:resume_id>/', views.resume_detail, name='resume_detail_slash'),
    path('resumes/upload', views.resume_upload, name='resume_upload'),
    path('resumes/upload/', views.resume_upload, name='resume_upload_slash'),
    path('resumes/upload-path', views.resume_upload_path, name='resume_upload_path'),
    path('resumes/upload-path/', views.resume_upload_path, name='resume_upload_path_slash'),

    # Candidates
    path('candidates/', views.candidates_collection, name='candidates_collection'),
    path('candidates/<int:candidate_id>', views.candidate_detail, name='candidate_detail'),
    path('candidates/<int:candidate_id>/', views.candidate_detail, name='candidate_detail_slash'),
    path('candidates/<int:candidate_id>/status', views.candidate_status_update, name='candidate_status_update'),
    path('candidates/<int:candidate_id>/notes', views.candidate_notes_update, name='candidate_notes_update'),
    path('candidates/batch-decision', views.candidate_batch_decision, name='candidate_batch_decision'),
    path('candidates/batch-decision/', views.candidate_batch_decision, name='candidate_batch_decision_slash'),
    path('candidates/rank/<int:jd_id>', views.candidate_rank, name='candidate_rank'),
    path('candidates/rank/<int:jd_id>/', views.candidate_rank, name='candidate_rank_slash'),
    path('candidates/<int:candidate_id>/summary', views.candidate_summary, name='candidate_summary'),
    path('candidates/<int:candidate_id>/summary/', views.candidate_summary, name='candidate_summary_slash'),

    # Stages
    path('stages/candidate/<int:candidate_id>', views.stages_by_candidate, name='stages_by_candidate'),
    path('stages/candidate/<int:candidate_id>/', views.stages_by_candidate, name='stages_by_candidate_slash'),
    path('stages/<int:stage_id>', views.stage_detail, name='stage_detail'),
    path('stages/<int:stage_id>/', views.stage_detail, name='stage_detail_slash'),

    # Email
    path('email/generate', views.email_generate, name='email_generate'),
    path('email/generate/', views.email_generate, name='email_generate_slash'),
    path('email/send', views.email_send, name='email_send'),
    path('email/send/', views.email_send, name='email_send_slash'),

    # Interview Questions
    path('interview/questions/<int:candidate_id>', views.interview_questions, name='interview_questions'),
    path('interview/questions/<int:candidate_id>/', views.interview_questions, name='interview_questions_slash'),

    # Meetings
    path('meetings/candidate/<int:candidate_id>', views.meetings_by_candidate, name='meetings_by_candidate'),
    path('meetings/candidate/<int:candidate_id>/', views.meetings_by_candidate, name='meetings_by_candidate_slash'),
    path('meetings/<int:meeting_id>', views.meeting_detail, name='meeting_detail'),
    path('meetings/<int:meeting_id>/', views.meeting_detail, name='meeting_detail_slash'),

    # AI Agent
    path('agent/execute', views.agent_execute_view, name='agent_execute'),
    path('agent/execute/', views.agent_execute_view, name='agent_execute_slash'),
    path('agent/pipeline/<int:jd_id>', views.agent_pipeline_view, name='agent_pipeline'),
    path('agent/pipeline/<int:jd_id>/', views.agent_pipeline_view, name='agent_pipeline_slash'),
    path('agent/tools', views.agent_tools_view, name='agent_tools'),
    path('agent/tools/', views.agent_tools_view, name='agent_tools_slash'),

    # Tasks (Celery Status)
    path('tasks/<str:task_id>', views.celery_task_status, name='celery_task_status'),
    path('tasks/<str:task_id>/', views.celery_task_status, name='celery_task_status_slash'),
]
