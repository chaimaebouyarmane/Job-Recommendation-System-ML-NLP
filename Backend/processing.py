import string
import re
import spacy
from sklearn.feature_extraction.text import TfidfVectorizer
from Models.skills import skills  # Importez vos compétences

nlp = spacy.load("fr_core_news_sm")
tfidf_matrixCV = None

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
#######
tfidf_vectorizer = TfidfVectorizer(sublinear_tf=True, stop_words=custom_stopwords)