import json
import os
from pathlib import Path
from typing import cast

from dotenv import load_dotenv
from flask import Blueprint, jsonify, request
from openai import APIError, OpenAI
from src.models.note import Note, db

note_bp = Blueprint('note', __name__)
load_dotenv()

TRANSLATE_PROMPT = Path(__file__).resolve().parents[2] / 'prompts' / 'translate_prompt.md'

@note_bp.route('/notes/translate', methods=['POST'])
def translate_note():
    data = request.get_json(silent=True)
    content = cast(dict[str, object], data).get('content') if isinstance(data, dict) else None
    if not isinstance(content, str) or not content.strip():
        return jsonify({'error': 'Note content is required'}), 400

    api_key = os.getenv('OPEN_ROUTER_KEY')
    if not api_key:
        return jsonify({'error': 'Translation is not configured'}), 503

    try:
        prompt = TRANSLATE_PROMPT.read_text(encoding='utf-8')
    except OSError:
        return jsonify({'error': 'Translation prompt is unavailable'}), 500

    try:
        response = OpenAI(base_url='https://openrouter.ai/api/v1', api_key=api_key).chat.completions.create(
            model='qwen/qwen3.8-27b:free',
            messages=[
                {'role': 'system', 'content': prompt},
                {'role': 'user', 'content': content},
            ],
            timeout=30,
        )
        result: object = json.loads(response.choices[0].message.content or '')
    except (APIError, ValueError, IndexError, AttributeError, TypeError):
        return jsonify({'error': 'Translation failed. Please try again.'}), 502

    translation = cast(dict[str, object], result).get('translation') if isinstance(result, dict) else None
    if not isinstance(translation, str) or not translation.strip():
        return jsonify({'error': 'Translation failed. Please try again.'}), 502

    return jsonify({'translation': translation})

@note_bp.route('/notes', methods=['GET'])
def get_notes():
    """Get all notes, ordered by most recently updated"""
    notes = Note.query.order_by(Note.updated_at.desc()).all()
    return jsonify([note.to_dict() for note in notes])

@note_bp.route('/notes', methods=['POST'])
def create_note():
    """Create a new note"""
    try:
        data = request.json
        if not data or 'title' not in data or 'content' not in data:
            return jsonify({'error': 'Title and content are required'}), 400
        
        note = Note(title=data['title'], content=data['content'])
        db.session.add(note)
        db.session.commit()
        return jsonify(note.to_dict()), 201
    except Exception as e:
        db.session.rollback()
        return jsonify({'error': str(e)}), 500

@note_bp.route('/notes/<int:note_id>', methods=['GET'])
def get_note(note_id):
    """Get a specific note by ID"""
    note = Note.query.get_or_404(note_id)
    return jsonify(note.to_dict())

@note_bp.route('/notes/<int:note_id>', methods=['PUT'])
def update_note(note_id):
    """Update a specific note"""
    try:
        note = Note.query.get_or_404(note_id)
        data = request.json
        
        if not data:
            return jsonify({'error': 'No data provided'}), 400
        
        note.title = data.get('title', note.title)
        note.content = data.get('content', note.content)
        db.session.commit()
        return jsonify(note.to_dict())
    except Exception as e:
        db.session.rollback()
        return jsonify({'error': str(e)}), 500

@note_bp.route('/notes/<int:note_id>', methods=['DELETE'])
def delete_note(note_id):
    """Delete a specific note"""
    try:
        note = Note.query.get_or_404(note_id)
        db.session.delete(note)
        db.session.commit()
        return '', 204
    except Exception as e:
        db.session.rollback()
        return jsonify({'error': str(e)}), 500

@note_bp.route('/notes/search', methods=['GET'])
def search_notes():
    """Search notes by title or content"""
    query = request.args.get('q', '')
    if not query:
        return jsonify([])
    
    notes = Note.query.filter(
        (Note.title.contains(query)) | (Note.content.contains(query))
    ).order_by(Note.updated_at.desc()).all()
    
    return jsonify([note.to_dict() for note in notes])

