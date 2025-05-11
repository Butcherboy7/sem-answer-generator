import os
import logging
import uuid
import time
from datetime import datetime
from flask import Flask, render_template, request, jsonify, send_from_directory, session
from werkzeug.utils import secure_filename
from werkzeug.middleware.proxy_fix import ProxyFix
import threading

from utils.ocr_utils import extract_text_from_pdf, extract_questions
from utils.llm_utils import process_questions_batch
from utils.document_formatter import create_docx, create_pdf
from models import db, ProcessingTask

# Configure logging
logging.basicConfig(level=logging.DEBUG)
logger = logging.getLogger(__name__)

# Initialize Flask app
app = Flask(__name__)
app.secret_key = os.environ.get("SESSION_SECRET", "default-secret-key-for-development")
app.wsgi_app = ProxyFix(app.wsgi_app, x_proto=1, x_host=1)

# Configure database
app.config['SQLALCHEMY_DATABASE_URI'] = os.environ.get("DATABASE_URL")
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False
app.config["SQLALCHEMY_ENGINE_OPTIONS"] = {
    "pool_recycle": 300,
    "pool_pre_ping": True,
}

# Initialize database
db.init_app(app)
with app.app_context():
    db.create_all()

# Create necessary directories
UPLOAD_FOLDER = 'uploads'
OUTPUT_FOLDER = 'output'
TEMP_FOLDER = 'temp'

for folder in [UPLOAD_FOLDER, OUTPUT_FOLDER, TEMP_FOLDER]:
    os.makedirs(folder, exist_ok=True)

app.config['UPLOAD_FOLDER'] = UPLOAD_FOLDER
app.config['OUTPUT_FOLDER'] = OUTPUT_FOLDER
app.config['TEMP_FOLDER'] = TEMP_FOLDER
app.config['MAX_CONTENT_LENGTH'] = 100 * 1024 * 1024  # 100MB limit

# Global dictionary to store processing status
processing_tasks = {}

@app.route('/')
def index():
    """Render the upload form page."""
    return render_template('index.html')

@app.route('/history_page')
def history_page():
    """Render the history page."""
    return render_template('history.html')

@app.route('/upload', methods=['POST'])
def upload_file():
    if 'question_file' not in request.files:
        return jsonify({'error': 'No question file provided'}), 400
    
    question_file = request.files['question_file']
    
    if question_file.filename == '':
        return jsonify({'error': 'No selected question file'}), 400
    
    if not (question_file.filename and question_file.filename.lower().endswith('.pdf')):
        return jsonify({'error': 'Only PDF files are allowed for questions'}), 400
    
    # Check if notes files were provided (optional, multiple allowed)
    notes_files = request.files.getlist('notes_files')
    notes_file_paths = []
    notes_filenames = []
    
    if notes_files and len(notes_files) > 0:
        for notes_file in notes_files:
            if notes_file and notes_file.filename and notes_file.filename != '':
                if not notes_file.filename.lower().endswith('.pdf'):
                    return jsonify({'error': f'Only PDF files are allowed for notes. File "{notes_file.filename}" is not a PDF'}), 400
    
    try:
        # Generate a unique ID for this process
        process_id = str(uuid.uuid4())
        
        # Create a secure filename and save question file
        question_filename = secure_filename(question_file.filename) if question_file.filename else f"question_{process_id}.pdf"
        question_file_path = os.path.join(app.config['UPLOAD_FOLDER'], f"{process_id}_question_{question_filename}")
        question_file.save(question_file_path)
        
        # Save multiple notes files if provided
        if notes_files and len(notes_files) > 0:
            for i, notes_file in enumerate(notes_files):
                if notes_file and notes_file.filename and notes_file.filename != '':
                    notes_filename = secure_filename(notes_file.filename)
                    notes_file_path = os.path.join(app.config['UPLOAD_FOLDER'], f"{process_id}_notes_{i}_{notes_filename}")
                    notes_file.save(notes_file_path)
                    notes_file_paths.append(notes_file_path)
                    notes_filenames.append(notes_filename)
        
        # Get form data
        subject_name = request.form.get('subject_name', '')
        mark_type = request.form.get('mark_type', '5')
        study_mode = request.form.get('study_mode', 'understand')
        
        # Store process info in memory
        processing_tasks[process_id] = {
            'status': 'uploaded',
            'question_file_path': question_file_path,
            'notes_file_paths': notes_file_paths,
            'original_question_filename': question_filename,
            'original_notes_filenames': notes_filenames,
            'has_notes': len(notes_file_paths) > 0,
            'subject_name': subject_name,
            'mark_type': mark_type,
            'study_mode': study_mode,
            'progress': 0,
            'message': 'Files uploaded successfully'
        }
        
        # Store in database
        task_db = ProcessingTask()
        task_db.id = process_id
        task_db.status = 'uploaded'
        task_db.progress = 0
        task_db.message = 'Files uploaded successfully'
        task_db.subject_name = subject_name
        task_db.mark_type = mark_type
        task_db.study_mode = study_mode
        task_db.has_notes = len(notes_file_paths) > 0
        task_db.created_at = datetime.utcnow()
        db.session.add(task_db)
        db.session.commit()
        
        # Start processing in background
        thread = threading.Thread(
            target=process_document, 
            args=(process_id, question_file_path, notes_file_paths, subject_name, mark_type, study_mode)
        )
        thread.start()
        
        return jsonify({
            'process_id': process_id,
            'status': 'uploaded',
            'message': 'Files uploaded successfully'
        })
        
    except Exception as e:
        logger.error(f"Error in upload: {str(e)}")
        return jsonify({'error': str(e)}), 500

@app.route('/db_check', methods=['GET'])
def db_check():
    """Check if database connection is working properly."""
    try:
        # Query one record to check connection
        task_count = ProcessingTask.query.count()
        
        # Also create a test record and immediately delete it to verify write permissions
        test_task = ProcessingTask()
        test_task.id = str(uuid.uuid4())  # Just use a plain UUID to stay within 36 chars
        test_task.status = "test"
        test_task.progress = 0
        test_task.message = "Database connection test"
        test_task.created_at = datetime.utcnow()
        
        db.session.add(test_task)
        db.session.commit()
        
        # Now delete the test task
        db.session.delete(test_task)
        db.session.commit()
        
        return jsonify({
            'success': True,
            'message': f'Database connection successful. Current task count: {task_count}',
            'database_url': os.environ.get('DATABASE_URL', 'Not set').split('@')[0][:10] + '...' if os.environ.get('DATABASE_URL') else 'Not set'
        })
    except Exception as e:
        logger.error(f"Database check failed: {str(e)}")
        return jsonify({
            'success': False,
            'error': str(e)
        }), 500

@app.route('/history', methods=['GET'])
def get_history():
    """Get the list of completed tasks from the database."""
    try:
        # Query the database for completed tasks, order by most recent first
        completed_tasks = ProcessingTask.query.filter(
            ProcessingTask.status == 'completed'
        ).order_by(ProcessingTask.created_at.desc()).limit(20).all()
        
        # Convert tasks to dictionaries for JSON response
        tasks_list = [task.to_dict() for task in completed_tasks]
        
        return jsonify({
            'success': True,
            'tasks': tasks_list
        })
    except Exception as e:
        logger.error(f"Error retrieving task history: {str(e)}")
        return jsonify({'error': f'Failed to retrieve history: {str(e)}'}), 500

@app.route('/status/<process_id>', methods=['GET'])
def get_status(process_id):
    """Check status of a processing task."""
    # First check in-memory cache
    if process_id in processing_tasks:
        return jsonify(processing_tasks[process_id])
    
    # If not in memory, try to get from database
    try:
        task = ProcessingTask.query.get(process_id)
        if task:
            # Convert database task to dict format
            return jsonify(task.to_dict())
        else:
            return jsonify({'error': 'Invalid process ID'}), 404
    except Exception as e:
        logger.error(f"Error retrieving task status: {str(e)}")
        return jsonify({'error': f'Error retrieving status: {str(e)}'}), 500

@app.route('/download/<process_id>/<format_type>', methods=['GET'])
def download_file(process_id, format_type):
    """Download the generated document."""
    filename = None
    
    # First check in-memory cache
    if process_id in processing_tasks:
        task = processing_tasks[process_id]
        
        if task['status'] != 'completed':
            return jsonify({'error': 'Processing not completed yet'}), 400
        
        if format_type == 'pdf':
            filename = task.get('pdf_filename')
        else:
            filename = task.get('docx_filename')
    else:
        # If not in memory, try to get from database
        try:
            task = ProcessingTask.query.get(process_id)
            if not task or task.status != 'completed':
                return jsonify({'error': 'Process not found or not completed'}), 404
            
            if format_type == 'pdf':
                filename = task.pdf_filename
            else:
                filename = task.docx_filename
        except Exception as e:
            logger.error(f"Error retrieving task for download: {str(e)}")
            return jsonify({'error': f'Error retrieving file: {str(e)}'}), 500
    
    if not filename:
        return jsonify({'error': 'Output file not found'}), 404
    
    return send_from_directory(
        app.config['OUTPUT_FOLDER'],
        filename,
        as_attachment=True
    )

def process_document(process_id, question_file_path, notes_file_paths, subject_name, mark_type, study_mode):
    try:
        # Get in-memory and database task objects
        task = processing_tasks[process_id]
        
        # Function to update both in-memory and database state
        def update_task_status(status, progress, message):
            # Update in-memory
            task['status'] = status
            task['progress'] = progress
            task['message'] = message
            
            # Update in database
            with app.app_context():
                db_task = db.session.get(ProcessingTask, process_id)
                if db_task:
                    db_task.status = status
                    db_task.progress = progress
                    db_task.message = message
                    db.session.commit()
        
        # Update status for processing questions
        update_task_status('processing_ocr', 10, 'Extracting questions from PDF')
        
        # Step 1: Extract text from question PDF
        extracted_question_text = extract_text_from_pdf(question_file_path)
        
        update_task_status('extracting_questions', 20, 'Identifying questions from text')
        
        # Step 2: Extract questions from the text
        questions = extract_questions(extracted_question_text)
        total_questions = len(questions)
        
        if total_questions == 0:
            update_task_status('error', 0, 'No questions found in the document')
            return
        
        # Step 3: Process notes if provided
        notes_text = None
        if notes_file_paths and len(notes_file_paths) > 0:
            update_task_status('processing_notes', 30, f'Extracting and processing {len(notes_file_paths)} reference notes')
            
            # Extract text from all notes PDFs and combine
            all_notes_text = []
            for i, notes_path in enumerate(notes_file_paths):
                update_task_status('processing_notes', 30, f'Processing reference note {i+1} of {len(notes_file_paths)}')
                file_text = extract_text_from_pdf(notes_path)
                all_notes_text.append(f"--- NOTES DOCUMENT {i+1} ---\n{file_text}\n")
            
            # Combine all notes into one text
            notes_text = "\n".join(all_notes_text)
        
        update_task_status('processing_questions', 40, f'Processing {total_questions} questions through LLM')
        
        # Update question count in database
        with app.app_context():
            db_task = db.session.get(ProcessingTask, process_id)
            if db_task:
                db_task.question_count = total_questions
                db.session.commit()
        
        # Step 4: Process questions in batches of 3
        all_answers = []
        batch_size = 3
        
        for i in range(0, total_questions, batch_size):
            batch = questions[i:i+batch_size]
            batch_answers = process_questions_batch(batch, subject_name, mark_type, study_mode, notes_text)
            all_answers.extend(batch_answers)
            
            # Update progress
            progress = 40 + int((i + len(batch)) / total_questions * 40)
            progress = min(80, progress)
            update_task_status('processing_questions', progress, 
                              f'Processed {min(i + len(batch), total_questions)} of {total_questions} questions')
        
        # Step 5: Generate documents
        update_task_status('creating_documents', 90, 'Creating output documents')
        
        timestamp = time.strftime("%Y%m%d-%H%M%S")
        safe_subject = ''.join(e for e in subject_name if e.isalnum() or e == ' ').strip().replace(' ', '_')
        if not safe_subject:
            safe_subject = 'subject'
            
        # Create Word document
        docx_filename = f"{safe_subject}_{timestamp}.docx"
        docx_path = os.path.join(app.config['OUTPUT_FOLDER'], docx_filename)
        create_docx(all_answers, questions, docx_path, subject_name, mark_type, study_mode, has_notes=notes_text is not None)
        
        # Create PDF document
        pdf_filename = f"{safe_subject}_{timestamp}.pdf"
        pdf_path = os.path.join(app.config['OUTPUT_FOLDER'], pdf_filename)
        create_pdf(all_answers, questions, pdf_path, subject_name, mark_type, study_mode, has_notes=notes_text is not None)
        
        # Update task with completion info
        update_task_status('completed', 100, 'Processing completed successfully')
        task['docx_filename'] = docx_filename
        task['pdf_filename'] = pdf_filename
        task['output_filename'] = docx_filename  # Default download is docx
        
        # Update database with file information
        with app.app_context():
            db_task = db.session.get(ProcessingTask, process_id)
            if db_task:
                db_task.docx_filename = docx_filename
                db_task.pdf_filename = pdf_filename
                db_task.completed_at = datetime.utcnow()
                db.session.commit()
        
    except Exception as e:
        logger.error(f"Error processing document: {str(e)}")
        if process_id in processing_tasks:
            # Update in-memory task
            processing_tasks[process_id]['status'] = 'error'
            processing_tasks[process_id]['progress'] = 0
            processing_tasks[process_id]['message'] = f'Error: {str(e)}'
            
        # Update database with error
        with app.app_context():
            try:
                db_task = db.session.get(ProcessingTask, process_id)
                if db_task:
                    db_task.status = 'error'
                    db_task.message = f'Error: {str(e)}'
                    db.session.commit()
            except Exception as db_error:
                logger.error(f"Failed to update database with error: {str(db_error)}")

if __name__ == '__main__':
    app.run(host='0.0.0.0', port=5000, debug=True)
