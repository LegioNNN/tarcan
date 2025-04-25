import calendar
import os
import json
from datetime import datetime, timedelta, date
from flask import render_template, redirect, url_for, flash, request, jsonify
from flask_login import login_user, logout_user, current_user, login_required
from urllib.parse import urlparse
from app import db
from models import User, Field, Product, FieldProduct, Activity, ActivityType, create_default_activity_types

def register_routes(app):
    # Default activity types will be created after all routes are registered
    # and database tables are created (see code at bottom of this file)
        
    # User authentication routes
    @app.route('/login', methods=['GET', 'POST'])
    def login():
        if current_user.is_authenticated:
            return redirect(url_for('index'))
        
        if request.method == 'POST':
            username = request.form['username']
            password = request.form['password']
            user = User.query.filter_by(username=username).first()
            
            if user is None or not user.check_password(password):
                flash('Invalid username or password', 'danger')
                return redirect(url_for('login'))
            
            login_user(user, remember=True)
            next_page = request.args.get('next')
            if not next_page or urlparse(next_page).netloc != '':
                next_page = url_for('index')
            
            return redirect(next_page)
        
        return render_template('login.html', title='Sign In')
    
    @app.route('/logout')
    def logout():
        logout_user()
        return redirect(url_for('index'))
    
    @app.route('/register', methods=['GET', 'POST'])
    def register():
        if current_user.is_authenticated:
            return redirect(url_for('index'))
        
        if request.method == 'POST':
            username = request.form['username']
            email = request.form['email']
            password = request.form['password']
            name = request.form['name']
            phone = request.form['phone']
            
            if User.query.filter_by(username=username).first():
                flash('Username already in use. Please choose a different one.', 'danger')
                return redirect(url_for('register'))
            
            if User.query.filter_by(email=email).first():
                flash('Email already registered. Please use a different one.', 'danger')
                return redirect(url_for('register'))
            
            user = User(username=username, email=email, name=name, phone=phone)
            user.set_password(password)
            db.session.add(user)
            db.session.commit()
            
            flash('Registration successful! You can now log in.', 'success')
            return redirect(url_for('login'))
        
        return render_template('register.html', title='Register')
    
    # Home page
    @app.route('/')
    def index():
        if current_user.is_authenticated:
            # Get fields data for dashboard
            fields = Field.query.filter_by(user_id=current_user.id).all()
            fields_count = len(fields)
            
            # Get upcoming activities
            today = date.today()
            next_week = today + timedelta(days=7)
            upcoming_activities = Activity.query.join(Field).filter(
                Field.user_id == current_user.id,
                Activity.date >= today,
                Activity.date <= next_week,
                Activity.completed == False
            ).order_by(Activity.date).limit(5).all()
            
            return render_template('index.html', title='Dashboard', 
                                fields_count=fields_count,
                                fields=fields,
                                upcoming_activities=upcoming_activities)
        else:
            return render_template('index.html', title='Farm Management System')

    # Fields routes
    @app.route('/fields')
    @login_required
    def fields():
        user_fields = Field.query.filter_by(user_id=current_user.id).order_by(Field.name).all()
        return render_template('fields/index.html', title='Your Fields', fields=user_fields)
    
    @app.route('/fields/add', methods=['GET', 'POST'])
    @login_required
    def add_field():
        if request.method == 'POST':
            name = request.form['name']
            location = request.form['location']
            size = request.form['size']
            size_unit = request.form['size_unit']
            description = request.form['description']
            
            # Get map coordinates
            center_lat = request.form.get('center_lat', None)
            center_lng = request.form.get('center_lng', None)
            zoom_level = request.form.get('zoom_level', None)
            map_bounds = request.form.get('map_bounds', None)
            
            field = Field(
                name=name,
                location=location,
                size=float(size) if size else None,
                size_unit=size_unit,
                description=description,
                center_lat=float(center_lat) if center_lat else None,
                center_lng=float(center_lng) if center_lng else None,
                zoom_level=int(zoom_level) if zoom_level else 15,
                map_bounds=map_bounds,
                user_id=current_user.id
            )
            
            db.session.add(field)
            db.session.commit()
            
            flash('Tarla başarıyla eklendi!', 'success')
            return redirect(url_for('fields'))
        
        return render_template('fields/add.html', title='Tarla Ekle', os=os)
    
    @app.route('/fields/edit/<int:id>', methods=['GET', 'POST'])
    @login_required
    def edit_field(id):
        field = Field.query.get_or_404(id)
        
        # Ensure the field belongs to the current user
        if field.user_id != current_user.id:
            flash('You do not have permission to edit this field.', 'danger')
            return redirect(url_for('fields'))
        
        if request.method == 'POST':
            field.name = request.form['name']
            field.location = request.form['location']
            field.size = float(request.form['size']) if request.form['size'] else None
            field.size_unit = request.form['size_unit']
            field.description = request.form['description']
            
            db.session.commit()
            
            flash('Field updated successfully!', 'success')
            return redirect(url_for('fields'))
        
        return render_template('fields/edit.html', title='Edit Field', field=field)
    
    @app.route('/fields/delete/<int:id>')
    @login_required
    def delete_field(id):
        field = Field.query.get_or_404(id)
        
        # Ensure the field belongs to the current user
        if field.user_id != current_user.id:
            flash('You do not have permission to delete this field.', 'danger')
            return redirect(url_for('fields'))
        
        # Delete associated products
        FieldProduct.query.filter_by(field_id=field.id).delete()
        
        # Delete associated activities
        Activity.query.filter_by(field_id=field.id).delete()
        
        db.session.delete(field)
        db.session.commit()
        
        flash('Field deleted successfully!', 'success')
        return redirect(url_for('fields'))
    
    @app.route('/fields/view/<int:id>')
    @login_required
    def view_field(id):
        field = Field.query.get_or_404(id)
        
        # Ensure the field belongs to the current user
        if field.user_id != current_user.id:
            flash('Bu tarlayı görüntüleme izniniz yok.', 'danger')
            return redirect(url_for('fields'))
        
        # Get field products
        field_products = FieldProduct.query.filter_by(field_id=field.id).all()
        
        # Get all products for the add product modal
        products = Product.query.order_by(Product.name).all()
        
        # Get field activities
        activities = Activity.query.filter_by(field_id=field.id).order_by(Activity.date.desc()).all()
        
        return render_template('fields/view.html', title=field.name, 
                              field=field, 
                              field_products=field_products,
                              products=products,
                              activities=activities,
                              os=os)
    
    # Products routes
    @app.route('/products')
    @login_required
    def products():
        # Get all products and user's field products
        all_products = Product.query.order_by(Product.name).all()
        user_fields = Field.query.filter_by(user_id=current_user.id).all()
        
        return render_template('products/index.html', title='Products', 
                              products=all_products,
                              fields=user_fields)
    
    @app.route('/products/add', methods=['GET', 'POST'])
    @login_required
    def add_product():
        if request.method == 'POST':
            name = request.form['name']
            description = request.form['description']
            growing_period = request.form['growing_period']
            
            # Check if product already exists
            existing_product = Product.query.filter_by(name=name).first()
            if existing_product:
                flash('Product already exists!', 'warning')
                return redirect(url_for('products'))
            
            product = Product(
                name=name,
                description=description,
                growing_period=int(growing_period) if growing_period else None
            )
            
            db.session.add(product)
            db.session.commit()
            
            flash('Product added successfully!', 'success')
            return redirect(url_for('products'))
        
        return render_template('products/add.html', title='Add Product')
    
    @app.route('/products/edit/<int:id>', methods=['GET', 'POST'])
    @login_required
    def edit_product(id):
        product = Product.query.get_or_404(id)
        
        if request.method == 'POST':
            product.name = request.form['name']
            product.description = request.form['description']
            product.growing_period = int(request.form['growing_period']) if request.form['growing_period'] else None
            
            db.session.commit()
            
            flash('Product updated successfully!', 'success')
            return redirect(url_for('products'))
        
        return render_template('products/edit.html', title='Edit Product', product=product)
    
    @app.route('/field_products/add', methods=['POST'])
    @login_required
    def add_field_product():
        field_id = request.form['field_id']
        product_id = request.form['product_id']
        planting_date_str = request.form['planting_date']
        notes = request.form['notes']
        
        # Validate field ownership
        field = Field.query.get_or_404(field_id)
        if field.user_id != current_user.id:
            flash('You do not have permission to add products to this field.', 'danger')
            return redirect(url_for('products'))
        
        # Convert planting date
        planting_date = datetime.strptime(planting_date_str, '%Y-%m-%d').date() if planting_date_str else None
        
        # Calculate expected harvest date if growing period is available
        product = Product.query.get_or_404(product_id)
        expected_harvest_date = None
        if planting_date and product.growing_period:
            expected_harvest_date = planting_date + timedelta(days=product.growing_period)
        
        field_product = FieldProduct(
            field_id=field_id,
            product_id=product_id,
            planting_date=planting_date,
            expected_harvest_date=expected_harvest_date,
            notes=notes
        )
        
        db.session.add(field_product)
        db.session.commit()
        
        # Add planting activity
        planting_activity_type = ActivityType.query.filter_by(name='Planting').first()
        if planting_activity_type and planting_date:
            activity = Activity(
                field_id=field_id,
                user_id=current_user.id,
                activity_type_id=planting_activity_type.id,
                date=planting_date,
                notes=f"Planted {product.name}. {notes}",
                completed=True
            )
            db.session.add(activity)
            db.session.commit()
        
        flash('Product added to field successfully!', 'success')
        return redirect(url_for('view_field', id=field_id))
    
    # Activities routes
    @app.route('/activities/add', methods=['GET', 'POST'])
    @login_required
    def add_activity():
        if request.method == 'POST':
            field_id = request.form['field_id']
            activity_type_id = request.form['activity_type_id']
            date_str = request.form['date']
            time_str = request.form.get('time', '')
            notes = request.form['notes']
            completed = 'completed' in request.form
            
            # Validate field ownership
            field = Field.query.get_or_404(field_id)
            if field.user_id != current_user.id:
                flash('You do not have permission to add activities to this field.', 'danger')
                return redirect(url_for('fields'))
            
            # Parse date and time
            activity_date = datetime.strptime(date_str, '%Y-%m-%d').date()
            activity_time = datetime.strptime(time_str, '%H:%M').time() if time_str else None
            
            activity = Activity(
                field_id=field_id,
                user_id=current_user.id,
                activity_type_id=activity_type_id,
                date=activity_date,
                time=activity_time,
                notes=notes,
                completed=completed
            )
            
            db.session.add(activity)
            db.session.commit()
            
            flash('Activity added successfully!', 'success')
            
            # Redirect back to field view or calendar depending on where we came from
            next_page = request.form.get('next', url_for('view_field', id=field_id))
            return redirect(next_page)
        
        # Get field id from query parameter if present
        field_id = request.args.get('field_id')
        field = None
        if field_id:
            field = Field.query.get_or_404(field_id)
            # Validate field ownership
            if field.user_id != current_user.id:
                flash('You do not have permission to add activities to this field.', 'danger')
                return redirect(url_for('fields'))
        
        # Get all fields owned by user
        fields = Field.query.filter_by(user_id=current_user.id).all()
        activity_types = ActivityType.query.order_by(ActivityType.name).all()
        
        # Get next page for redirect
        next_page = request.args.get('next', '')
        
        return render_template('activities/add.html', title='Add Activity',
                              field=field,
                              fields=fields,
                              activity_types=activity_types,
                              next=next_page)
    
    @app.route('/activities/complete/<int:id>')
    @login_required
    def complete_activity(id):
        activity = Activity.query.get_or_404(id)
        
        # Ensure the activity belongs to the current user
        if activity.field.user_id != current_user.id:
            flash('You do not have permission to update this activity.', 'danger')
            return redirect(url_for('calendar'))
        
        activity.completed = True
        db.session.commit()
        
        flash('Activity marked as completed!', 'success')
        
        # Redirect back to the referring page
        return redirect(request.referrer or url_for('calendar'))
    
    @app.route('/activities/delete/<int:id>')
    @login_required
    def delete_activity(id):
        activity = Activity.query.get_or_404(id)
        
        # Ensure the activity belongs to the current user
        if activity.field.user_id != current_user.id:
            flash('You do not have permission to delete this activity.', 'danger')
            return redirect(url_for('calendar'))
        
        db.session.delete(activity)
        db.session.commit()
        
        flash('Activity deleted successfully!', 'success')
        
        # Redirect back to the referring page
        return redirect(request.referrer or url_for('calendar'))
    
    # Calendar routes
    @app.route('/calendar')
    @login_required
    def calendar_view():
        # Get the month and year from query parameters, default to current month
        today = date.today()
        month = int(request.args.get('month', today.month))
        year = int(request.args.get('year', today.year))
        
        # Get calendar data for the selected month
        cal = calendar.monthcalendar(year, month)
        month_name = calendar.month_name[month]
        
        # Get activities for the selected month
        start_date = date(year, month, 1)
        if month == 12:
            end_date = date(year + 1, 1, 1) - timedelta(days=1)
        else:
            end_date = date(year, month + 1, 1) - timedelta(days=1)
        
        activities = Activity.query.join(Field).filter(
            Field.user_id == current_user.id,
            Activity.date >= start_date,
            Activity.date <= end_date
        ).order_by(Activity.date, Activity.time).all()
        
        # Organize activities by date
        activity_dates = {}
        for activity in activities:
            day = activity.date.day
            if day not in activity_dates:
                activity_dates[day] = []
            activity_dates[day].append(activity)
        
        # Get all fields for the add activity form
        fields = Field.query.filter_by(user_id=current_user.id).all()
        activity_types = ActivityType.query.order_by(ActivityType.name).all()
        
        return render_template('calendar/index.html', title='Calendar',
                              cal=cal,
                              month=month,
                              year=year,
                              month_name=month_name,
                              activity_dates=activity_dates,
                              fields=fields,
                              activity_types=activity_types,
                              today=today)
    
    # Profile routes
    @app.route('/profile', methods=['GET', 'POST'])
    @login_required
    def profile():
        if request.method == 'POST':
            # Update user profile
            current_user.name = request.form['name']
            current_user.phone = request.form['phone']
            current_user.email = request.form['email']
            
            # Check if password change was requested
            current_password = request.form.get('current_password')
            new_password = request.form.get('new_password')
            confirm_password = request.form.get('confirm_password')
            
            if current_password and new_password:
                if not current_user.check_password(current_password):
                    flash('Current password is incorrect.', 'danger')
                    return redirect(url_for('profile'))
                
                if new_password != confirm_password:
                    flash('New passwords do not match.', 'danger')
                    return redirect(url_for('profile'))
                
                current_user.set_password(new_password)
                flash('Password changed successfully!', 'success')
            
            db.session.commit()
            flash('Profile updated successfully!', 'success')
            return redirect(url_for('profile'))
        
        return render_template('profile/index.html', title='Your Profile')
