from flask_sqlalchemy import SQLAlchemy
from datetime import datetime

db = SQLAlchemy()

class ProcessingTask(db.Model):
    """
    Model for storing processing task information.
    This allows users to look back at previously processed tasks and re-download documents.
    """
    id = db.Column(db.String(36), primary_key=True)  # UUID as string
    status = db.Column(db.String(50), nullable=False, default='pending')
    progress = db.Column(db.Integer, default=0)
    message = db.Column(db.String(255))
    subject_name = db.Column(db.String(100))
    mark_type = db.Column(db.String(10))
    study_mode = db.Column(db.String(20))
    has_notes = db.Column(db.Boolean, default=False)
    question_count = db.Column(db.Integer, default=0)
    docx_filename = db.Column(db.String(255))
    pdf_filename = db.Column(db.String(255))
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    completed_at = db.Column(db.DateTime)

    def to_dict(self):
        """Convert the model to a dictionary for JSON response"""
        return {
            'id': self.id,
            'status': self.status,
            'progress': self.progress,
            'message': self.message,
            'subject_name': self.subject_name,
            'mark_type': self.mark_type,
            'study_mode': self.study_mode,
            'has_notes': self.has_notes,
            'question_count': self.question_count,
            'docx_filename': self.docx_filename,
            'pdf_filename': self.pdf_filename,
            'created_at': self.created_at.isoformat() if self.created_at else None,
            'completed_at': self.completed_at.isoformat() if self.completed_at else None
        }