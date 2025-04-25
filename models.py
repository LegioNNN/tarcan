from datetime import datetime
from app import db, login_manager
from flask_login import UserMixin
from werkzeug.security import generate_password_hash, check_password_hash

@login_manager.user_loader
def load_user(user_id):
    return User.query.get(int(user_id))

class User(UserMixin, db.Model):
    id = db.Column(db.Integer, primary_key=True)
    username = db.Column(db.String(64), unique=True, nullable=False)
    email = db.Column(db.String(120), unique=True, nullable=False)
    password_hash = db.Column(db.String(256), nullable=False)
    name = db.Column(db.String(100))
    phone = db.Column(db.String(20))
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    fields = db.relationship('Field', backref='owner', lazy='dynamic')
    activities = db.relationship('Activity', backref='user', lazy='dynamic')
    
    def set_password(self, password):
        self.password_hash = generate_password_hash(password)
    
    def check_password(self, password):
        return check_password_hash(self.password_hash, password)
    
    def __repr__(self):
        return f'<User {self.username}>'

class Field(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(100), nullable=False)
    location = db.Column(db.String(200))
    size = db.Column(db.Float)  # Size in hectares or acres
    size_unit = db.Column(db.String(10), default='hectare')  # hectare or acre
    description = db.Column(db.Text)
    # Map coordinates
    center_lat = db.Column(db.Float)  # Center latitude
    center_lng = db.Column(db.Float)  # Center longitude
    zoom_level = db.Column(db.Integer, default=15)  # Map zoom level
    map_bounds = db.Column(db.Text)  # JSON string of field boundary coordinates
    user_id = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=False)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    updated_at = db.Column(db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    products = db.relationship('FieldProduct', backref='field', lazy='dynamic')
    activities = db.relationship('Activity', backref='field', lazy='dynamic')
    
    def __repr__(self):
        return f'<Field {self.name}>'

class Product(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(100), nullable=False)
    description = db.Column(db.Text)
    growing_period = db.Column(db.Integer)  # Growing period in days
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    field_products = db.relationship('FieldProduct', backref='product', lazy='dynamic')
    
    def __repr__(self):
        return f'<Product {self.name}>'

class FieldProduct(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    field_id = db.Column(db.Integer, db.ForeignKey('field.id'), nullable=False)
    product_id = db.Column(db.Integer, db.ForeignKey('product.id'), nullable=False)
    planting_date = db.Column(db.Date)
    expected_harvest_date = db.Column(db.Date)
    status = db.Column(db.String(20), default='active')  # active, harvested, failed
    notes = db.Column(db.Text)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    
    def __repr__(self):
        return f'<FieldProduct {self.field_id}:{self.product_id}>'

class ActivityType(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(50), nullable=False, unique=True)
    description = db.Column(db.Text)
    
    def __repr__(self):
        return f'<ActivityType {self.name}>'

class Activity(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    field_id = db.Column(db.Integer, db.ForeignKey('field.id'), nullable=False)
    user_id = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=False)
    activity_type_id = db.Column(db.Integer, db.ForeignKey('activity_type.id'), nullable=False)
    activity_type = db.relationship('ActivityType')
    date = db.Column(db.Date, nullable=False)
    time = db.Column(db.Time)
    notes = db.Column(db.Text)
    completed = db.Column(db.Boolean, default=False)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    
    def __repr__(self):
        return f'<Activity {self.id} {self.activity_type.name}>'

# Add some predefined activity types
def create_default_activity_types():
    default_types = [
        ('Planting', 'Planting seeds or seedlings'),
        ('Fertilizing', 'Applying fertilizer to crops'),
        ('Watering', 'Irrigation or watering plants'),
        ('Pesticide', 'Applying pesticides or herbicides'),
        ('Harvesting', 'Harvesting crops'),
        ('Soil preparation', 'Preparing soil for planting'),
        ('Maintenance', 'General field maintenance tasks'),
        ('Inspection', 'Field or crop inspection'),
    ]
    
    for name, description in default_types:
        activity_type = ActivityType.query.filter_by(name=name).first()
        if activity_type is None:
            activity_type = ActivityType(name=name, description=description)
            db.session.add(activity_type)
    
    db.session.commit()
