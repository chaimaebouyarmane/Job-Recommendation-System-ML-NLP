from flask import Flask, request, jsonify
import os
from PyPDF2 import PdfReader
import string
import re
import spacy
from sklearn.feature_extraction.text import TfidfVectorizer
from sklearn.metrics.pairwise import cosine_similarity
from Models.skills import skills  # Importez vos compétences
from BD.Connexion import client, db
from Models.offres_emploi_train import OffreEmploiTrain
import pandas as pd
from Models.similarityOffre import SimilarityOffre
from sklearn.model_selection import train_test_split


# Charger le modèle linguistique français de spaCy
nlp = spacy.load("fr_core_news_sm")
tfidf_matrixCV = None

app = Flask(__name__)

# Définir une liste de stopwords personnalisée
custom_stopwords = ["le", "la", "de", "des", "du", "et", "en", "pour", "avec", "je", "tu", "il", "elle", "nous", "vous", "ils", "elles"]

def nettoyer_texte(texte):
    # Supprimer la ponctuation
    texte = texte.translate(str.maketrans('', '', string.punctuation))

    # Mettre en minuscules
    texte = texte.lower()

    # Supprimer les numéros de téléphone
    texte = re.sub(r'\d{10,}', '', texte)

    # Supprimer les adresses e-mail
    texte = re.sub(r'\S+@\S+', '', texte)

    # Supprimer les stopwords personnalisés
    mots = texte.split()  # Diviser le texte en mots
    mots = [mot for mot in mots if mot not in custom_stopwords]  # Supprimer les stopwords

    # Utiliser spaCy pour normaliser les mots et supprimer les mots répétés
    doc = nlp(" ".join(mots))
    mots_norm = [token.lemma_ for token in doc if not token.is_stop]

    # Filtrer les mots pertinents pour les compétences
    mots_pertinents = [mot for mot in mots_norm if mot in skills]

    # Réassembler les mots pertinents pour les compétences
    texte_skills = ' '.join(mots_pertinents)

    return texte_skills

def mots_communs(texte, liste):
    mots = texte.split()
    mots_communs = [mot for mot in mots if mot in liste]
    return ' '.join(mots_communs)

def lemmatize(text):
    doc = nlp(text)
    # Convertir le document en une chaîne de caractères
    text_str = ' '.join([token.text for token in doc])
    # Supprimer les chiffres
    text_str = re.sub(r'\d+', '', text_str)
    # Supprimer les caractères isolés (un seul alphabet)
    text_str = re.sub(r'\b\w\b', '', text_str)
    # Supprimer les espaces
    text_str = re.sub(r'\s+', ' ', text_str).strip()
    # Supprimer les caractères spéciaux avec une expression régulière
    cleaned_text = re.sub(r"[,./?\":;+=\[\](){}]", "", text_str)
    cleaned_doc = nlp(cleaned_text)
    cleaned_tokens = [token.lemma_ for token in cleaned_doc if not (token.is_stop or token.is_punct or token.pos_ == "VERB")]
    cleaned_text = ' '.join(cleaned_tokens)
    return cleaned_text

# Créer un objet TfidfVectorizer avec sublinear_tf
tfidf_vectorizer = TfidfVectorizer(sublinear_tf=True, stop_words=custom_stopwords)

# Route pour l'extraction de données depuis les fichiers PDF, nettoyage et extraction de compétences
@app.route('/extract_clean_and_extract_skills', methods=['GET'])
def extract_clean_and_extract_skills():
    global tfidf_matrixCV
    # Spécifiez le chemin du répertoire contenant les CV
    dossier_cv = "CV"

    # Utilisez os.listdir pour récupérer la liste des fichiers dans le répertoire
    fichiers_dossier = os.listdir(dossier_cv)

    # Créez une liste vide pour stocker les compétences extraites des CV
    extracted_skills_list = []

    # Parcourez la liste des fichiers
    for fichier in fichiers_dossier:
        if fichier.endswith(".pdf"):
            chemin_pdf = os.path.join(dossier_cv, fichier)
            pdf_reader = PdfReader(chemin_pdf)

            cv_texte = ""
            # Parcourez chaque page du PDF et extrayez le texte
            for page in pdf_reader.pages:
                cv_texte += page.extract_text()

            # Appliquez la fonction de nettoyage et d'extraction de compétences
            cleaned_cv = nettoyer_texte(cv_texte)
            extracted_skills_list.append({"file": fichier, "skills": cleaned_cv})

    # Extraire uniquement les compétences des CV pour la vectorisation TF-IDF
    skills_text = [cv["skills"] for cv in extracted_skills_list]

    # Effectuer la vectorisation TF-IDF sur les compétences des CV
    tfidf_matrixCV = tfidf_vectorizer.fit_transform(skills_text)

    # Récupérer les noms de fonction
    feature_names = tfidf_vectorizer.get_feature_names_out()

    # Boucler sur tous les CV
    for cv_index, cv in enumerate(extracted_skills_list):
        tfidf_vector_for_cv = tfidf_matrixCV[cv_index]

        # Récupérer les scores TF-IDF sous forme de tableau
        tfidf_scores_for_cv = tfidf_vector_for_cv.toarray()[0]

        print(f"CV {cv_index + 1} - Valeurs TF-IDF :")
        for word, tfidf_score in zip(feature_names, tfidf_scores_for_cv):
            print(f"Mot : {word}, TF-IDF : {tfidf_score}")
        print("\n")

    return jsonify(extracted_skills_list)

# Route pour la récupération et la vectorisation des offres d'emploi
collection2 = db['similarity_offres']
@app.route('/vectorize_offres', methods=['GET'])
def vectorize_offres():
    global tfidf_matrixCV
    data = []  # Créez une liste pour stocker les données
    

    collection = db["offres_emploi_train"]

    # Récupération de toutes les offres
    cursor = collection.find({})

    # Création d'objets OffreEmploi à partir des données de MongoDB
    for document in cursor:
        name = document['name']
        combined_text = document['combined_text']
        lien = document['lien']
        offre = OffreEmploiTrain(name, combined_text, lien)

        # Effectuer la vectorisation TF-IDF sur les compétences des offres
        comp = mots_communs(offre.combined_text, skills)
        tfidf_vector_for_offre = tfidf_vectorizer.transform([comp])

        # Calculer la similarité entre le CV de l'utilisateur et l'offre
        similarity_score = cosine_similarity(tfidf_matrixCV, tfidf_vector_for_offre)

        # Créez un objet SimilarityOffre pour stocker le lien de l'offre et la similarité
        similarity_offre = SimilarityOffre(lien, similarity_score[0][0])
        # Ajoutez l'objet SimilarityOffre à la collection
        collection2.insert_one({
            'lien': similarity_offre.lien,
            'similarity': similarity_offre.similarity
        })

        # Ajoutez l'objet SimilarityOffre à la liste "data"
        data.append(similarity_offre)

    # Fermeture de la connexion à MongoDB
    #client.close()

    # Triez la liste en fonction de la similarité décroissante
    data.sort(key=lambda x: x.similarity, reverse=True)

    # Convertissez la liste en un format JSON
    recommendations = [{
        'lienOffre': offre.lien,
        'similarity': offre.similarity
    } for offre in data]

    # Créez une liste pour stocker les recommandations pour chaque CV
    cv_recommendations = []

    # Boucle sur tous les CV et ajoutez les recommandations
    for cv_index, _ in enumerate(tfidf_matrixCV):
        cv_recommendations.append({
            'cv_index': cv_index,
            'recommendations': [rec for rec in recommendations]
        })

    return jsonify(cv_recommendations)



if __name__ == '__main__':
    app.run(debug=True, port=5009)

