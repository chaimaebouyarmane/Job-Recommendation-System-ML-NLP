from flask import Flask, request,render_template,redirect, url_for
from PyPDF2 import PdfReader 
import string
import re
from sklearn.metrics.pairwise import cosine_similarity
from Models.skills import skills  # Importez vos compétences
from BD.Connexion import db
from Models.offres_emploi_test import OffreEmploiTest
from Models.offres_emploi_train import OffreEmploiTrain
from Models.OffreEmploi import OffreEmploi
from Models.similarityOffre import SimilarityOffre
from Models.User import User
import bcrypt
from sklearn.metrics import f1_score
import matplotlib.pyplot as plt 
from processing import tfidf_vectorizer

#######
plt.ion()
app = Flask(__name__,template_folder='../templates')
app.config['STATIC_FOLDER'] = 'static'

########HOME###################
@app.route('/')
def home():
    return render_template('index.html')

###########COLLECTION############
collection = db['user']
######LOGIN############################
@app.route('/login', methods=['GET', 'POST'])
def login():
    error_message = None
    if request.method == 'POST' or request.method == 'GET':
        email = request.form.get('email')
        password = request.form.get('password')

        user = collection.find_one({'email': email})

        if user and bcrypt.checkpw(password.encode('utf-8'), user['password']):
            return redirect('index_cv')
        else :
             error_message = "Email ou mot de passe incorrect"

    return render_template('index.html',error_message=error_message)



########SIGNUP#########################
@app.route('/signup', methods=['GET', 'POST'])
def signup():
    error_message = None
    if request.method == 'POST':
        nom = request.form.get('nom')
        prenom = request.form.get('prenom')
        email = request.form.get('email')
        password = request.form.get('password')

        existing_user = collection.find_one({'email': email})

        if existing_user:
            error_message = "Cet email existe deja"
        else:

            # Créez un nouvel utilisateur en fournissant tous les arguments nécessaires
            new_user = User(nom, prenom, email, password)

            # Hachez le mot de passe avant de le stocker
            hashed_password = bcrypt.hashpw(password.encode('utf-8'), bcrypt.gensalt())

            # Enregistrez l'utilisateur dans la base de données
            collection.insert_one({'nom': new_user.nom, 'prenom': new_user.prenom, 'email': new_user.email, 'password': hashed_password})

            return redirect(url_for('index_cv'))
    return render_template('index_inscrire.html', error_message=error_message)
##############
@app.route('/logout')
def logout():
    return render_template('index.html')
###############MAIN#################
@app.route('/index_cv')
def index_cv():
    return render_template('index_cv.html')

##############MODELE#########################
def clean_and_preprocess(text):
    # Supprimer la ponctuation
    text = text.translate(str.maketrans('', '', string.punctuation))

    # Mettre en minuscules
    text = text.lower()

    # Supprimer les numéros de téléphone (10 chiffres ou plus)
    text = re.sub(r'\d{10,}', '', text)

    # Supprimer les adresses e-mail
    text = re.sub(r'\S+@\S+', '', text)

    # Supprimer les stopwords personnalisés
    custom_stopwords = ["le", "la", "de", "des", "du", "et", "en", "pour", "avec", "je", "tu", "il", "elle", "nous", "vous", "ils", "elles"]
    words = text.split()
    words = [word for word in words if word not in custom_stopwords]

    # Réassembler les mots nettoyés en une seule chaîne
    cleaned_text = ' '.join(words)

    return cleaned_text
################
@app.route('/process_uploaded_cv', methods=['GET', 'POST'])
def process_uploaded_cv():
    if 'pdfFile' not in request.files:
        return "Aucun fichier CV n'a été téléchargé."

    uploaded_cv = request.files['pdfFile']

    if uploaded_cv.filename == '':
        return "Le nom du fichier est vide."

    cv_text = ""

    if uploaded_cv:
        pdf_reader = PdfReader(uploaded_cv)
        if pdf_reader:
            for page in pdf_reader.pages:
                cv_text += page.extract_text()

    # Clean and preprocess the CV text
    cleaned_cv = clean_and_preprocess(cv_text)

    # Fit the TF-IDF vectorizer to the skills
    tfidf_vectorizer.fit(skills)

    # Transform the user's CV with the fitted vectorizer
    tfidf_vector_for_user_cv = tfidf_vectorizer.transform([cleaned_cv])

    data = []
    collection = db["offres_emploi"]
    cursor = collection.find({})

    similarities = []  # Liste pour stocker les similarités
    offre_names = []  # Liste pour stocker les noms des offres
    for document in cursor:
        name = document['name']
        combined_text = document['combined_text']
        lien = document['lien']
        offre = OffreEmploi(name, combined_text, lien)

        # Clean and preprocess the combined text of the job offer
        cleaned_offer_text = clean_and_preprocess(offre.combined_text)

        # Transform the offer text with the fitted vectorizer
        tfidf_vector_for_offer = tfidf_vectorizer.transform([cleaned_offer_text])
         #Calculate the similarity between the user's CV and the job offer
        similarity_score = cosine_similarity(tfidf_vector_for_user_cv, tfidf_vector_for_offer)

        #similarity_offre = SimilarityOffre(lien, similarity_score[0][0])
        #similarities.append(similarity_score)
        #offre_names.append(name)

        #data.append(similarity_offre)

        # # Check if similarity_score is not None before attempting to convert
        if similarity_score is not None:
            similarity_score = similarity_score[0][0]
            similarity_offre = SimilarityOffre(lien, similarity_score)
            data.append(similarity_offre)
            similarities.append(similarity_score)
            offre_names.append(name)
        else:
            pass  # You can choose to skip this offer or assign a default similarity score

    # Filter recommendations with similarity > 0
    filtered_recommendations = []
    for offre in data:
        if offre.similarity > 0.2:
            filtered_recommendations.append({
                'lienOffre': offre.lien,
                'similarity': offre.similarity
            })

    filtered_recommendations.sort(key=lambda x: x['similarity'], reverse=True)
    # Create a bar plot with offre names on the x-axis and similarities on the y-axis
    plt.figure(figsize=(10, 6))
    plt.bar(offre_names, similarities, color='blue')  # Lignes bleues
    plt.axhline(y=0.9, color='red', linestyle='--', label='CV Similarité ')
    plt.title('Similarité entre le CV de l\'utilisateur et les offres')
    plt.xlabel('Offre')
    plt.ylabel('Similarité')
    plt.xticks(rotation=45)  # Rotation des noms des offres pour une meilleure lisibilité
    plt.legend()
    # Before plt.savefig
    print("Saving the plot")

    plt.savefig('/Users/habibaezzagrani/Desktop/RecommandationSystem/Backend/static/similarite.png')

    # After plt.savefig
    print("Plot saved")


    # Fermez le graphique pour libérer les ressources
    plt.close()
    #return redirect(url_for('offre', similarity_image='similarite.png', recommendations=filtered_recommendations))
    return render_template('offre.html',similarity_image='similarite.png', recommendations=filtered_recommendations)


if __name__ == '__main__':
    app.run(debug=True,port=5002)