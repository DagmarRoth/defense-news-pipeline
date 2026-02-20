"""
Flask web interface for DVIDS Topic Manager

Allows users to create, edit, and manage custom monitoring topics.
Each topic gets its own Google Sheet and optional Slack notifications.
"""

import os
from flask import Flask, render_template, request, redirect, url_for, flash, jsonify
from datetime import datetime
from dotenv import load_dotenv

# Load environment variables
load_dotenv()

# Import our modules
from topic_manager import (
    load_topics, create_topic, get_topic_by_id,
    update_topic, delete_topic, list_active_topics,
    get_topic_sheet_url
)
from notifiers.sheets_logger import init_sheets_client, create_topic_sheet_on_add

# ============================================================================
# Flask Application Setup
# ============================================================================

app = Flask(__name__)
app.config['SECRET_KEY'] = os.getenv('FLASK_SECRET_KEY', 'dev-key-please-change')

# Initialize Google Sheets client
try:
    SHEETS_CLIENT = init_sheets_client(
        os.getenv('GOOGLE_CREDENTIALS_PATH', 'credentials/google_service_account.json')
    )
    MASTER_SHEET_ID = os.getenv('GOOGLE_SHEETS_SPREADSHEET_ID')
except Exception as e:
    print(f"⚠ Warning: Could not initialize Google Sheets client: {e}")
    print("  The web UI will still work, but topic sheet creation will fail.")
    SHEETS_CLIENT = None
    MASTER_SHEET_ID = None


# ============================================================================
# Routes
# ============================================================================

@app.route('/')
def index():
    """Display all topics with statistics."""
    topics = list_active_topics()

    # Add stats to each topic
    for topic in topics:
        topic['sheet_url'] = get_topic_sheet_url(topic)
        topic['has_slack'] = bool(topic.get('slack_webhook'))

    return render_template('index.html', topics=topics)


@app.route('/topic/add', methods=['GET', 'POST'])
def add_topic_route():
    """Add new topic form and processing."""
    if request.method == 'POST':
        try:
            # Get form data
            name = request.form.get('name', '').strip()
            keywords_str = request.form.get('keywords', '').strip()
            score_threshold_str = request.form.get('score_threshold', '5')
            slack_webhook = request.form.get('slack_webhook', '').strip() or None

            # Validate inputs
            if not name:
                flash('Topic name is required', 'error')
                return redirect(url_for('add_topic_route'))

            if not keywords_str:
                flash('At least one keyword is required', 'error')
                return redirect(url_for('add_topic_route'))

            try:
                score_threshold = int(score_threshold_str)
                if score_threshold < 1 or score_threshold > 10:
                    raise ValueError()
            except ValueError:
                flash('Score threshold must be between 1 and 10', 'error')
                return redirect(url_for('add_topic_route'))

            # Parse keywords (comma-separated)
            keywords = [k.strip() for k in keywords_str.split(',') if k.strip()]

            if not keywords:
                flash('At least one valid keyword is required', 'error')
                return redirect(url_for('add_topic_route'))

            # Sanitize sheet name (max 100 chars)
            sheet_name = name[:100]

            # Check Google Sheets is configured
            if not MASTER_SHEET_ID or not SHEETS_CLIENT:
                flash('Google Sheets not configured. Cannot create topic.', 'error')
                return redirect(url_for('add_topic_route'))

            # Create topic in database
            topic = create_topic(
                name=name,
                keywords=keywords,
                sheet_id=MASTER_SHEET_ID,
                sheet_name=sheet_name,
                slack_webhook=slack_webhook,
                score_threshold=score_threshold
            )

            # Create worksheet immediately
            try:
                create_topic_sheet_on_add(SHEETS_CLIENT, topic)
                flash(
                    f"✓ Topic '{name}' created successfully! "
                    f"<a href='{get_topic_sheet_url(topic)}' target='_blank'>View Google Sheet</a>",
                    'success'
                )
            except Exception as e:
                flash(
                    f"⚠ Topic created but worksheet creation failed: {e}",
                    'warning'
                )

            return redirect(url_for('index'))

        except ValueError as e:
            flash(f'Invalid topic data: {e}', 'error')
            return redirect(url_for('add_topic_route'))
        except Exception as e:
            flash(f'Error creating topic: {e}', 'error')
            return redirect(url_for('add_topic_route'))

    return render_template('add_topic.html')


@app.route('/topic/<topic_id>/edit', methods=['GET', 'POST'])
def edit_topic_route(topic_id):
    """Edit existing topic."""
    topic = get_topic_by_id(topic_id)

    if not topic:
        flash('Topic not found', 'error')
        return redirect(url_for('index'))

    if request.method == 'POST':
        try:
            # Get form data
            name = request.form.get('name', '').strip()
            keywords_str = request.form.get('keywords', '').strip()
            score_threshold_str = request.form.get('score_threshold', str(topic.get('score_threshold', 5)))
            slack_webhook = request.form.get('slack_webhook', '').strip() or None

            # Validate
            if not name:
                flash('Topic name is required', 'error')
                return redirect(url_for('edit_topic_route', topic_id=topic_id))

            if not keywords_str:
                flash('At least one keyword is required', 'error')
                return redirect(url_for('edit_topic_route', topic_id=topic_id))

            try:
                score_threshold = int(score_threshold_str)
                if score_threshold < 1 or score_threshold > 10:
                    raise ValueError()
            except ValueError:
                flash('Score threshold must be between 1 and 10', 'error')
                return redirect(url_for('edit_topic_route', topic_id=topic_id))

            keywords = [k.strip() for k in keywords_str.split(',') if k.strip()]

            if not keywords:
                flash('At least one valid keyword is required', 'error')
                return redirect(url_for('edit_topic_route', topic_id=topic_id))

            # Update topic
            updated = update_topic(
                topic_id,
                name=name,
                keywords=keywords,
                slack_webhook=slack_webhook,
                score_threshold=score_threshold
            )

            if updated:
                flash(f"✓ Topic '{name}' updated successfully!", 'success')
            else:
                flash('Topic not found', 'error')

            return redirect(url_for('index'))

        except Exception as e:
            flash(f'Error updating topic: {e}', 'error')
            return redirect(url_for('edit_topic_route', topic_id=topic_id))

    # GET request - show form with current values
    topic['sheet_url'] = get_topic_sheet_url(topic)
    return render_template('edit_topic.html', topic=topic)


@app.route('/topic/<topic_id>/delete', methods=['POST'])
def delete_topic_route(topic_id):
    """Delete (deactivate) a topic."""
    topic = get_topic_by_id(topic_id)

    if not topic:
        flash('Topic not found', 'error')
        return redirect(url_for('index'))

    try:
        delete_topic(topic_id)
        flash(f"✓ Topic '{topic['name']}' deleted", 'info')
    except Exception as e:
        flash(f'Error deleting topic: {e}', 'error')

    return redirect(url_for('index'))


@app.route('/health')
def health():
    """Health check endpoint for Railway."""
    return jsonify({
        'status': 'ok',
        'timestamp': datetime.now().isoformat(),
        'topics': len(list_active_topics())
    })


# ============================================================================
# Error Handlers
# ============================================================================

@app.errorhandler(404)
def not_found(error):
    """Handle 404 errors."""
    return render_template('error.html', error='Page not found'), 404


@app.errorhandler(500)
def internal_error(error):
    """Handle 500 errors."""
    return render_template('error.html', error='Internal server error'), 500


# ============================================================================
# Main
# ============================================================================

if __name__ == '__main__':
    port = int(os.getenv('PORT', 5000))
    debug = os.getenv('FLASK_ENV', 'production') == 'development'

    print("\n" + "="*70)
    print("DVIDS Topic Manager - Starting Flask Application")
    print("="*70)
    print(f"Port: {port}")
    print(f"Debug: {debug}")
    if SHEETS_CLIENT and MASTER_SHEET_ID:
        print(f"✓ Google Sheets configured")
    else:
        print(f"⚠ Google Sheets NOT configured - topic creation may fail")
    print("="*70 + "\n")

    app.run(host='0.0.0.0', port=port, debug=debug)
