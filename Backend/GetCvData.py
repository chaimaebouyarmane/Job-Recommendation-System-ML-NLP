from flask import Flask, request, jsonify
import os
from BD.Connexion import db
from PyPDF2 import PdfReader
from Models.CV import CV  # Importez la classe CV depuis votre fichier CV.py

app = Flask(__name__)

# Route pour l'extraction de données depuis les fichiers PDF et l'enregistrement dans MongoDB
@app.route('/upload_cv', methods=['POST'])
def upload_cv():
    # Spécifiez le chemin du répertoire contenant les CV
    dossier_cv = "CV"

    # Utilisez os.listdir pour récupérer la liste des fichiers dans le répertoire
    fichiers_dossier = os.listdir(dossier_cv)

    cv_collection = db["cvs"]
    # Créez une liste vide pour stocker le contenu des CV
    contenu_cv = []

    # Parcourez la liste des fichiers
    for fichier in fichiers_dossier:
        if fichier.endswith(".pdf"):
            chemin_pdf = os.path.join(dossier_cv, fichier)
            pdf_reader = PdfReader(chemin_pdf)

            cv_texte = ""
            # Parcourez chaque page du PDF et extrayez le texte
            for page in pdf_reader.pages:
                cv_texte += page.extract_text()
            # Ajoutez le texte du CV à la liste
            contenu_cv.append(cv_texte)

            # Créez une instance de la classe CV
            cv_instance = CV(file=fichier)

            # Insérez l'instance dans la collection MongoDB
            cv_collection.insert_one(cv_instance.__dict__)

    return jsonify({"message": "Les données des CV ont été importées dans MongoDB."})

if __name__ == '__main__':
    app.run(debug=True)
