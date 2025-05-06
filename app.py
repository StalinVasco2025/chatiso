from flask import Flask, request, jsonify, render_template
from dotenv import load_dotenv
import os
from google import genai
import fitz  # PyMuPDF
from werkzeug.utils import secure_filename
import json
import re

app = Flask(__name__, static_folder='static', template_folder='templates')
app.config['UPLOAD_FOLDER'] = 'uploads'
app.config['MAX_CONTENT_LENGTH'] = 16 * 1024 * 1024  # 16MB max upload

# Crear carpeta de uploads si no existe
os.makedirs(app.config['UPLOAD_FOLDER'], exist_ok=True)

load_dotenv()
GEMINI_API_KEY = os.getenv("GEMINI_API_KEY")

# Inicializar cliente Gemini
client = genai.Client(api_key=GEMINI_API_KEY)
model = client.models

# Ruta principal
@app.route('/')
def index():
    return render_template('index3.html')

# Función para extraer texto del PDF
def extract_text_from_pdf(pdf_path):
    text = ""
    try:
        doc = fitz.open(pdf_path)
        for page in doc:
            text += page.get_text()
        return text
    except Exception as e:
        print(f"Error al extraer texto del PDF: {e}")
        return ""

# Subida del PDF de la norma ISO
@app.route('/upload-iso', methods=['POST'])
def upload_iso():
    if 'file' not in request.files:
        return jsonify({'error': 'No file part'}), 400

    file = request.files['file']

    if file.filename == '':
        return jsonify({'error': 'No selected file'}), 400

    if file and file.filename.endswith('.pdf'):
        filename = secure_filename(file.filename)
        filepath = os.path.join(app.config['UPLOAD_FOLDER'], filename)
        file.save(filepath)

        pdf_text = extract_text_from_pdf(filepath)

        if not pdf_text:
            return jsonify({'error': 'No se pudo extraer texto del PDF'}), 400

        session_id = request.form.get('session_id', 'default')
        text_filepath = os.path.join(app.config['UPLOAD_FOLDER'], f"{session_id}_iso.txt")

        with open(text_filepath, 'w', encoding='utf-8') as f:
            f.write(pdf_text)

        return jsonify({
            'success': True,
            'message': f'PDF procesado correctamente. Se extrajeron {len(pdf_text)} caracteres.',
            'pages': len(fitz.open(filepath))
        })

    return jsonify({'error': 'Tipo de archivo no permitido'}), 400

# Análisis del caso de estudio
@app.route('/analyze-case', methods=['POST'])
def analyze_case():
    data = request.json
    caso_estudio = data.get('caso', '')
    session_id = data.get('session_id', 'default')

    if not caso_estudio:
        return jsonify({'error': 'El caso de estudio está vacío'}), 400

    text_filepath = os.path.join(app.config['UPLOAD_FOLDER'], f"{session_id}_iso.txt")

    try:
        with open(text_filepath, 'r', encoding='utf-8') as f:
            iso_text = f.read()
    except FileNotFoundError:
        return jsonify({'error': 'No se ha subido ningún archivo de norma ISO'}), 400

    prompt = f"""
    ## Instrucciones
    Eres un experto en la norma ISO 37001 sobre Sistemas de Gestión Antisoborno. Analiza el siguiente caso de estudio 
    en relación con la norma ISO 37001 que se proporciona después. Debes identificar los aspectos clave del caso, 
    relacionarlos con secciones específicas de la norma y proporcionar recomendaciones detalladas.

    ## Contenido de la Norma ISO 37001 (extracto)
    {iso_text[:50000]}

    ## Caso de Estudio
    {caso_estudio}

    ## Formato de Respuesta
    Estructura tu respuesta de la siguiente manera:
    1. Resumen del caso
    2. Términos clave identificados en el caso y su relación con la norma
    3. Secciones relevantes de la norma ISO 37001 aplicables al caso
    4. Recomendaciones específicas para implementar un sistema de gestión antisoborno según la norma
    5. Conclusión
    """

    try:
        response = model.generate_content(
            model="gemini-2.0-flash",
            contents=prompt
        )
        analysis = response.text

        analysis_filepath = os.path.join(app.config['UPLOAD_FOLDER'], f"{session_id}_analysis.txt")
        with open(analysis_filepath, 'w', encoding='utf-8') as f:
            f.write(analysis)

        return jsonify({'analysis': analysis})

    except Exception as e:
        return jsonify({'error': f'Error al generar análisis: {str(e)}'}), 500

# Evaluación de la respuesta del usuario
@app.route('/evaluate-response', methods=['POST'])
def evaluate_response():
    data = request.json
    user_response = data.get('userResponse', '')
    session_id = data.get('session_id', 'default')

    if not user_response:
        return jsonify({'error': 'La respuesta del usuario está vacía'}), 400

    analysis_filepath = os.path.join(app.config['UPLOAD_FOLDER'], f"{session_id}_analysis.txt")

    try:
        with open(analysis_filepath, 'r', encoding='utf-8') as f:
            gemini_analysis = f.read()
    except FileNotFoundError:
        return jsonify({'error': 'No se ha generado un análisis previo'}), 400

    prompt = f"""
    ## Instrucciones
    Eres un experto evaluador en sistemas de gestión antisoborno según la norma ISO 37001. Tu tarea es comparar dos análisis de un caso de estudio:
    1. El análisis generado por IA (modelo Gemini)
    2. El análisis proporcionado por un usuario

    Debes evaluar ambos análisis con base en los siguientes criterios:
    - Precisión y exactitud en relación con la norma ISO 37001
    - Comprensión del caso de estudio
    - Calidad de las recomendaciones
    - Estructura y claridad
    - Aplicabilidad práctica

    ## Análisis generado por IA
    {gemini_analysis}

    ## Análisis del usuario
    {user_response}

    ## Formato de Respuesta
    Tu evaluación debe seguir este formato JSON:
    {{
        "calificacionIA": X,
        "calificacionUsuario": Y,
        "confianzaIA": Z,
        "confianzaUsuario": W,
        "comentarioGeneral": "Comentario",
        "fortalezasIA": ["..."],
        "debilidadesIA": ["..."],
        "fortalezasUsuario": ["..."],
        "debilidadesUsuario": ["..."],
        "recomendacionMejora": "..."
    }}
    """

    try:
        response = model.generate_content(
            model="gemini-2.0-flash",
            contents=prompt
        )
        evaluation_text = response.text

        json_match = re.search(r'```json\s*(.*?)\s*```', evaluation_text, re.DOTALL)
        if json_match:
            json_str = json_match.group(1)
        else:
            json_match = re.search(r'({.*})', evaluation_text, re.DOTALL)
            json_str = json_match.group(1) if json_match else evaluation_text

        try:
            evaluation = json.loads(json_str)
        except json.JSONDecodeError:
            evaluation = {
                "calificacionIA": 7.0,
                "calificacionUsuario": 6.0,
                "confianzaIA": 85,
                "confianzaUsuario": 70,
                "comentarioGeneral": "No se pudo extraer una evaluación estructurada.",
                "fortalezasIA": ["Análisis estructurado"],
                "debilidadesIA": ["No especificado"],
                "fortalezasUsuario": ["Perspectiva personal"],
                "debilidadesUsuario": ["No especificado"],
                "recomendacionMejora": "Revisa la estructura y contenido de tu análisis para mejorar la calificación."
            }

        return jsonify(evaluation)

    except Exception as e:
        return jsonify({'error': f'Error al evaluar respuesta: {str(e)}'}), 500

if __name__ == '__main__':
    app.run(debug=True)
