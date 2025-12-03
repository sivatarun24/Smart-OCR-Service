
from datetime import datetime
from . import db, bcrypt
from flask_login import UserMixin

class User(UserMixin, db.Model):
    __tablename__ = 'users'
    id = db.Column(db.Integer, primary_key=True)
    username = db.Column(db.String(64), unique=True, nullable=False)
    email = db.Column(db.String(128), unique=True, nullable=False)
    name = db.Column(db.String(128), nullable=False)
    password_hash = db.Column(db.String(256), nullable=False)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)

    # Relationship to Document
    documents = db.relationship('Document', back_populates='user', lazy='dynamic')

    def to_dict(self):
        return {
            'id': self.id,
            'username': self.username,
            'email': self.email,
            'name': self.name,
            'created_at': self.created_at.isoformat()
        }
    

class Document(db.Model):
    __tablename__ = "documents"

    id = db.Column(db.Integer, primary_key=True, autoincrement=True)
    job_id = db.Column(db.String(64), unique=True, nullable=False)

    filename = db.Column(db.String(512), nullable=True)
    mime = db.Column(db.String(128), default="")
    gcs_uri = db.Column(db.String(1024), nullable=True)
    status = db.Column(db.String(64), default="RECEIVED", nullable=False)

    text = db.Column(db.Text, nullable=True)
    entities_json = db.Column(db.Text, nullable=True)
    tags_json = db.Column(db.Text, nullable=True)

    created_at = db.Column(db.DateTime(timezone=True), server_default=db.func.now(), nullable=False)
    updated_at = db.Column(db.DateTime(timezone=True), server_default=db.func.now(), onupdate=db.func.now())

    # Relationship to User
    user_id = db.Column(db.Integer, db.ForeignKey('users.id'))
    user = db.relationship('User', back_populates='documents')

    def to_dict(self):
        return {
            "id": self.id,
            "job_id": self.job_id,
            "filename": self.filename,
            "mime": self.mime,
            "gcs_uri": self.gcs_uri,
            "status": self.status,
            "text": self.text,
            "entities_json": self.entities_json,
            "tags_json": self.tags_json,
            "user_id": self.user_id,
            "created_at": self.created_at.isoformat() if self.created_at else None,
            "updated_at": self.updated_at.isoformat() if self.updated_at else None
        }

class Job(db.Model):
    __tablename__ = "jobs"

    id = db.Column(db.Integer, primary_key=True, autoincrement=True)
    job_id = db.Column(db.String(64), unique=True, nullable=False)

    filename = db.Column(db.String(256), nullable=False)
    mime = db.Column(db.String(128))
    gcs_uri = db.Column(db.String(512))

    status = db.Column(db.String(64), default="RECEIVED")
    progress = db.Column(db.Integer, default=0)
    stage = db.Column(db.String(128), default="INITIALIZED")

    created_at = db.Column(db.DateTime(timezone=True), default=datetime.utcnow)
    updated_at = db.Column(
        db.DateTime(timezone=True),
        default=datetime.utcnow,
        onupdate=datetime.utcnow
    )

    # optional relationship to Document if needed later
    document_id = db.Column(db.Integer, db.ForeignKey("documents.id"), nullable=True)