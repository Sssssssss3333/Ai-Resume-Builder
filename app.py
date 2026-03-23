import os
from flask import Flask, render_template, request, redirect, url_for, flash, session
from flask_sqlalchemy import SQLAlchemy
from flask_login import UserMixin, login_user, LoginManager, login_required, logout_user, current_user
from flask_bcrypt import Bcrypt
from analyzer_logic import analyze_resume

app = Flask(__name__)
app.config['SECRET_KEY'] = 'A_VERY_SECRET_KEY_12345'
app.config['SQLALCHEMY_DATABASE_URI'] = 'sqlite:///site.db'
db = SQLAlchemy(app)
bcrypt = Bcrypt(app)
login_manager = LoginManager(app)
login_manager.login_view = 'login'

# Models
class User(UserMixin, db.Model):
    id = db.Column(db.Integer, primary_key=True)
    username = db.Column(db.String(20), unique=True, nullable=False)
    email = db.Column(db.String(120), unique=True, nullable=False)
    password = db.Column(db.String(60), nullable=False)
    resumes = db.relationship('Resume', backref='author', lazy=True)

class Resume(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    title = db.Column(db.String(100), nullable=False)
    content = db.Column(db.Text, nullable=False) # JSON or simple text
    score = db.Column(db.Integer, default=0)
    feedback = db.Column(db.Text, default='')
    user_id = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=False)

@login_manager.user_loader
def load_user(user_id):
    return User.query.get(int(user_id))

# Routes
@app.route('/')
def index():
    if current_user.is_authenticated:
        return redirect(url_for('dashboard'))
    return render_template('index.html')

@app.route('/signup', methods=['GET', 'POST'])
def signup():
    if request.method == 'POST':
        username = request.form.get('username')
        email = request.form.get('email')
        password = request.form.get('password')
        
        user_exists = User.query.filter_by(email=email).first()
        if user_exists:
            flash('Email address already exists', 'danger')
            return redirect(url_for('signup'))
            
        hashed_password = bcrypt.generate_password_hash(password).decode('utf-8')
        new_user = User(username=username, email=email, password=hashed_password)
        db.session.add(new_user)
        db.session.commit()
        flash('Account created! You can now log in.', 'success')
        return redirect(url_for('login'))
        
    return render_template('signup.html')

@app.route('/login', methods=['GET', 'POST'])
def login():
    if request.method == 'POST':
        email = request.form.get('email')
        password = request.form.get('password')
        user = User.query.filter_by(email=email).first()
        
        if user and bcrypt.check_password_hash(user.password, password):
            login_user(user)
            return redirect(url_for('dashboard'))
        else:
            flash('Login Unsuccessful. Please check email and password', 'danger')
    return render_template('login.html')

@app.route('/logout')
@login_required
def logout():
    logout_user()
    return redirect(url_for('index'))

@app.route('/dashboard')
@login_required
def dashboard():
    user_resumes = Resume.query.filter_by(user_id=current_user.id).order_by(Resume.id.desc()).all()
    
    last_resume = user_resumes[0] if user_resumes else None
    
    score = 0
    suggestions = ["Build a resume first to receive AI-driven suggestions!"]
    
    if last_resume:
        import json
        try:
            data = json.loads(last_resume.content)
            parsed_text = " ".join([str(v) for v in data.values()])
        except:
            parsed_text = last_resume.content
            
        score, missing, tips = analyze_resume(parsed_text)
        suggestions = tips[:3] # Top 3 actionable suggestions
        
    return render_template('dashboard.html', 
                           resumes=user_resumes, 
                           last_resume=last_resume,
                           avg_score=score,
                           suggestions=suggestions)

@app.route('/builder', methods=['GET', 'POST'])
@login_required
def builder():
    if request.method == 'POST':
        resume_id = request.form.get('resume_id')
        title = request.form.get('title')
        content = request.form.get('content')
        
        if resume_id:
            resume = Resume.query.get(resume_id)
            if resume and resume.author == current_user:
                resume.title = title if title else 'Untitled Resume'
                resume.content = content
                db.session.commit()
                flash("Resume updated gracefully!", "success")
                return redirect(url_for('dashboard'))
        
        new_resume = Resume(
            title=title if title else 'Untitled Resume',
            content=content,
            user_id=current_user.id
        )
        db.session.add(new_resume)
        db.session.commit()
        
        flash("Resume successfully generated and bound to your Vault!", "success")
        return redirect(url_for('dashboard'))
        
    return render_template('builder.html', resume=None, resume_data={})

@app.route('/edit/<int:resume_id>')
@login_required
def edit_resume(resume_id):
    resume = Resume.query.get_or_404(resume_id)
    if resume.author != current_user:
        return "Unauthorized", 403
    import json
    try:
        resume_data = json.loads(resume.content)
    except:
        resume_data = {}
    return render_template('builder.html', resume=resume, resume_data=resume_data)

@app.route('/choose_template')
@login_required
def choose_template():
    if 'resume_data' not in session:
        flash("Please provide your details first.", "warning")
        return redirect(url_for('builder'))
    return render_template('choose_template.html')

# 3. Separate routes for each template
@app.route('/template/minimal')
@login_required
def template_minimal():
    if 'resume_data' not in session: return redirect(url_for('builder'))
    return render_template('resume_templates/minimal.html', resume_data=session['resume_data'], theme='minimal')

@app.route('/template/modern')
@login_required
def template_modern():
    if 'resume_data' not in session: return redirect(url_for('builder'))
    return render_template('resume_templates/modern.html', resume_data=session['resume_data'], theme='modern')

@app.route('/template/professional')
@login_required
def template_professional():
    if 'resume_data' not in session: return redirect(url_for('builder'))
    return render_template('resume_templates/professional.html', resume_data=session['resume_data'], theme='professional')

@app.route('/template/creative')
@login_required
def template_creative():
    if 'resume_data' not in session: return redirect(url_for('builder'))
    return render_template('resume_templates/creative.html', resume_data=session['resume_data'], theme='creative')

@app.route('/save_resume/<theme_name>', methods=['POST'])
@login_required
def save_resume(theme_name):
    if 'resume_data' not in session:
        return redirect(url_for('builder'))
        
    resume_data = session['resume_data'].copy()
    resume_data['theme'] = theme_name
    
    import json
    content = json.dumps(resume_data)
    
    new_resume = Resume(
        title=resume_data.get('title', 'Untitled Document'),
        content=content,
        user_id=current_user.id
    )
    db.session.add(new_resume)
    db.session.commit()
    
    session.pop('resume_data', None)
    flash("Resume perfectly rendered and saved to your database!", "success")
    return redirect(url_for('dashboard'))

@app.route('/analyzer', methods=['GET', 'POST'])
@login_required
def analyzer():
    if request.method == 'POST':
        resume_text = request.form.get('resume_text', '')
        job_description = request.form.get('job_description', '')
        
        if 'resume_pdf' in request.files:
            file = request.files['resume_pdf']
            if file and file.filename.endswith('.pdf'):
                from PyPDF2 import PdfReader
                try:
                    reader = PdfReader(file)
                    pdf_text = ""
                    for page in reader.pages:
                        parsed = page.extract_text()
                        if parsed:
                            pdf_text += parsed + "\n"
                    resume_text = pdf_text + "\n" + resume_text
                except:
                    pass

        import json
        try:
            data = json.loads(resume_text)
            parsed_text = " ".join([str(v) for v in data.values()])
        except:
            parsed_text = resume_text
        
        # Analyze resume using our mock AI function
        score, missing_skills, improvement_tips = analyze_resume(parsed_text, job_description)
        
        return render_template('result.html', score=score, missing_skills=missing_skills, improvement_tips=improvement_tips, resume_text=parsed_text)
        
    return render_template('analyzer.html')

@app.route('/result/<int:resume_id>')
@login_required
def view_result(resume_id):
    resume = Resume.query.get_or_404(resume_id)
    if resume.author != current_user:
        return "Unauthorized", 403
    import json
    try:
        resume_data = json.loads(resume.content)
        is_json = True
    except:
        resume_data = resume.content
        is_json = False
    return render_template('resume_view.html', resume=resume, resume_data=resume_data, is_json=is_json)

@app.route('/download_pdf/<theme_name>')
@login_required
def download_pdf(theme_name):
    if 'resume_data' not in session: return redirect(url_for('builder'))
    resume_data = session['resume_data']
    
    # Render pure standalone HTML
    rendered_html = render_template('pdf_layout.html', resume_data=resume_data, theme=theme_name)
    
    import pdfkit
    import tempfile
    from flask import make_response
    
    try:
        # Check standard Windows paths for wkhtmltopdf
        path_wkhtmltopdf = r'C:\Program Files\wkhtmltopdf\bin\wkhtmltopdf.exe'
        config = pdfkit.configuration(wkhtmltopdf=path_wkhtmltopdf) if os.path.exists(path_wkhtmltopdf) else None
        
        pdf = pdfkit.from_string(rendered_html, False, configuration=config, options={'margin-top': '0', 'margin-bottom': '0', 'margin-left': '0', 'margin-right': '0'})
        
        response = make_response(pdf)
        response.headers['Content-Type'] = 'application/pdf'
        response.headers['Content-Disposition'] = f'attachment; filename={resume_data.get("name", "Resume")}_{theme_name}.pdf'
        return response
    except Exception as e:
        flash(f"Error generating PDF (Install wkhtmltopdf to system): {str(e)}", "danger")
        return redirect(url_for(f'template_{theme_name}'))

if __name__ == '__main__':
    with app.app_context():
        db.create_all()
    app.run(debug=True, port=5000)
