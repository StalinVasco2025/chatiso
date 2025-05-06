import os
import faiss
import numpy as np
from flask import Flask, request, jsonify, render_template
from werkzeug.utils import secure_filename
from google import genai
from PyPDF2 import PdfReader

# Configuración de la API de Gemini
client = genai.Client(api_key="AIzaSyCpzD4M30B2Yx6p8XwCBcDYzdoYxB-24p4")

# Configuración del proyecto Flask
app = Flask(__name__)
UPLOAD_FOLDER = 'uploads'
app.config['UPLOAD_FOLDER'] = UPLOAD_FOLDER
if not os.path.exists(UPLOAD_FOLDER):
    os.makedirs(UPLOAD_FOLDER)

def leer_pdf(path):
    # Leer el PDF y extraer texto
    reader = PdfReader(path)
    return [page.extract_text() for page in reader.pages if page.extract_text()]

def agrupar_texto(paginas, tamaño=3):
    # Agrupar el texto en bloques de tamaño específico
    return ["\n".join(paginas[i:i + tamaño]) for i in range(0, len(paginas), tamaño)]

def generar_embedding(texto):
    # Generar embedding usando Gemini
    return np.array(client.models.embed_content(
        model="gemini-embedding-exp-03-07",
        contents=texto
    ).embeddings, dtype='float32')

@app.route('/')
def index():
    return render_template("index.html")

@app.route('/procesar', methods=['POST'])
def procesar():
    # Procesar el archivo PDF y el caso de estudio
    archivo = request.files['archivo']
    caso = request.form['caso']

    if not archivo or not caso:
        return jsonify({'error': 'Archivo o texto faltante'})

    # Guardar el archivo PDF
    filename = secure_filename(archivo.filename)
    filepath = os.path.join(app.config['UPLOAD_FOLDER'], filename)
    archivo.save(filepath)

    # Leer y agrupar el texto del PDF
    texto = leer_pdf(filepath)
    bloques = agrupar_texto(texto, tamaño=2)

    textos = []
    vectores = []

    # Generar embeddings de los bloques
    for bloque in bloques:
        try:
            emb = generar_embedding(bloque)
            vectores.append(emb)
            textos.append(bloque)
        except Exception as e:
            print("Error embedding:", e)

    # Crear índice FAISS
    dim = vectores[0].shape[0]
    index = faiss.IndexFlatL2(dim)
    index.add(np.array(vectores))

    # Embedding del caso de estudio
    caso_vec = generar_embedding(caso).reshape(1, -1)

    # Buscar el bloque más similar
    D, I = index.search(caso_vec, 1)
    bloque_relevante = textos[I[0][0]]

    # Preparar el prompt para Gemini
    prompt = f"Caso de estudio:\n{caso}\n\nContenido del documento relacionado:\n{bloque_relevante}"

    # Obtener la respuesta de Gemini
    respuesta = client.models.generate_content(
        model="gemini-2.0-flash",
        contents=prompt
    )

    return jsonify({'respuesta': respuesta.text})

if __name__ == '__main__':
    app.run(debug=True)
